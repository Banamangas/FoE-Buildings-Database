from types import SimpleNamespace
from typing import Literal
from unittest.mock import Mock

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from foe_buildings import config
from foe_buildings.tabs import building_details


class _Container:
    def __init__(self, *, open_: bool = False) -> None:
        self.open = open_

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> Literal[False]:
        return False


@pytest.fixture
def details_harness(monkeypatch):
    tab_states = [True, False]
    tabs_calls = []

    def tabs(labels, **kwargs):
        tabs_calls.append((labels, kwargs))
        return [_Container(open_=is_open) for is_open in tab_states]

    def columns(widths):
        return [_Container() for _ in widths]

    streamlit_calls = {
        name: Mock() for name in ("header", "info", "markdown", "error", "image")
    }
    for name, call in streamlit_calls.items():
        monkeypatch.setattr(building_details.st, name, call)
    monkeypatch.setattr(building_details.st, "columns", columns)
    monkeypatch.setattr(building_details.st, "tabs", tabs)
    monkeypatch.setattr(building_details.st, "session_state", {})
    monkeypatch.setattr(
        building_details.st,
        "selectbox",
        Mock(return_value="Test Building"),
    )

    monkeypatch.setattr(
        building_details.translations,
        "get_text",
        Mock(side_effect=lambda key, _lang: key),
    )
    monkeypatch.setattr(
        building_details.translations,
        "translate_column",
        Mock(side_effect=lambda column, _lang: column),
    )

    get_icon_base64 = Mock(return_value=None)
    monkeypatch.setattr(
        building_details.ui_components,
        "get_icon_base64",
        get_icon_base64,
    )

    original_is_numeric_dtype = building_details.pd.api.types.is_numeric_dtype
    is_numeric_dtype = Mock(wraps=original_is_numeric_dtype)
    monkeypatch.setattr(
        building_details.pd.api.types,
        "is_numeric_dtype",
        is_numeric_dtype,
    )

    combine_army = Mock(side_effect=lambda dataframe: dataframe.copy())
    monkeypatch.setattr(
        building_details,
        "combine_army_with_ge_gbg",
        combine_army,
    )

    entity = {"components": {"AllAge": {}}}
    load_lookup = Mock(return_value={"B_TEST": entity})
    monkeypatch.setattr(
        building_details.data_loader,
        "load_building_entity_lookup",
        load_lookup,
    )

    sections = [object()]
    render_building_tooltip = Mock(return_value=sections)
    render_tooltip_sections = Mock()
    monkeypatch.setattr(
        building_details.tooltip_renderer,
        "render_building_tooltip",
        render_building_tooltip,
    )
    monkeypatch.setattr(
        building_details.tooltip_renderer,
        "render_tooltip_sections",
        render_tooltip_sections,
    )

    render_stats_table = Mock()
    monkeypatch.setattr(
        building_details,
        "_render_stats_table",
        render_stats_table,
    )

    image_manager = Mock()
    image_manager.has_image.return_value = False
    dataframe = pd.DataFrame(
        [
            {
                config.COL_NAME: "Test Building",
                config.COL_TRANSLATED_ERA: "Test Era",
                config.COL_ERA: "TestEra",
                config.COL_SIZE: 4,
                config.COL_ASSET_ID: "W_Test",
                "id": "B_TEST",
                "coins": 100,
            }
        ]
    )

    def render(
        *,
        show_per_square: bool = False,
        combine_army_stats: bool = False,
    ) -> None:
        building_details.render_building_details(
            df_original=dataframe,
            selected_translated_era="Test Era",
            lang_code="en",
            image_manager=image_manager,
            show_per_square=show_per_square,
            combine_army_stats=combine_army_stats,
        )

    return SimpleNamespace(
        combine_army=combine_army,
        error=streamlit_calls["error"],
        get_icon_base64=get_icon_base64,
        info=streamlit_calls["info"],
        is_numeric_dtype=is_numeric_dtype,
        load_lookup=load_lookup,
        render=render,
        render_building_tooltip=render_building_tooltip,
        render_stats_table=render_stats_table,
        render_tooltip_sections=render_tooltip_sections,
        sections=sections,
        tab_states=tab_states,
        tabs_calls=tabs_calls,
    )


def test_stats_open_skips_entity_lookup(details_harness):
    details_harness.tab_states[:] = [True, False]

    details_harness.render()

    details_harness.load_lookup.assert_not_called()
    details_harness.render_stats_table.assert_called_once()


def test_tooltip_open_loads_lookup_and_renders_tooltip(details_harness):
    details_harness.tab_states[:] = [False, True]

    details_harness.render()

    details_harness.load_lookup.assert_called_once_with()
    details_harness.render_building_tooltip.assert_called_once()
    details_harness.render_tooltip_sections.assert_called_once_with(
        details_harness.sections,
        "en",
    )


def test_building_detail_tabs_track_state_with_a_stable_key(details_harness):
    details_harness.render()
    details_harness.render()

    labels, options = details_harness.tabs_calls[0]
    assert labels == ["complete_stats_table", "in_game_tooltip"]
    assert options["on_change"] == "rerun"

    keys = [call_options.get("key") for _, call_options in details_harness.tabs_calls]
    assert all(keys)
    assert len(set(keys)) == 1


def test_tooltip_open_skips_hidden_stats_work(details_harness):
    details_harness.tab_states[:] = [False, True]
    details_harness.combine_army.side_effect = lambda dataframe: dataframe.assign(
        id="B_COMBINED",
        Era="CombinedEra",
    )

    details_harness.render(show_per_square=True, combine_army_stats=True)

    details_harness.combine_army.assert_not_called()
    details_harness.is_numeric_dtype.assert_not_called()
    details_harness.get_icon_base64.assert_not_called()
    details_harness.render_stats_table.assert_not_called()
    _, tooltip_options = details_harness.render_building_tooltip.call_args
    assert tooltip_options["era_key"] == "TestEra"


def test_stats_open_runs_combination_and_per_square_preparation(details_harness):
    details_harness.tab_states[:] = [True, False]

    details_harness.render(show_per_square=True, combine_army_stats=True)

    details_harness.combine_army.assert_called_once()
    details_harness.is_numeric_dtype.assert_called()
    stats_data = details_harness.render_stats_table.call_args.args[0]
    coins_row = next(row for row in stats_data if row["Statistic"] == "coins")
    assert coins_row["Value"] == "25"


def test_tooltip_error_is_sanitized(details_harness):
    details_harness.tab_states[:] = [False, True]
    details_harness.load_lookup.side_effect = RuntimeError("secret backend detail")

    details_harness.render()

    details_harness.error.assert_called_once_with("tooltip_render_error")
    assert "secret backend detail" not in str(details_harness.error.call_args)
    assert any(
        call.args == ("no_tooltip_data",)
        for call in details_harness.info.call_args_list
    )


def test_streamlit_tracked_tabs_default_to_stats_and_restore_tooltip_selection():
    app = AppTest.from_string(
        """
import streamlit as st

stats, tooltip = st.tabs(
    ["Stats", "Tooltip"],
    key="building_details_tabs",
    on_change="rerun",
)
st.write(f"stats={stats.open};tooltip={tooltip.open}")
"""
    ).run()

    assert app.session_state["building_details_tabs"] == "Stats"
    assert app.markdown[0].value == "stats=True;tooltip=False"

    app.session_state["building_details_tabs"] = "Tooltip"
    app.run()

    assert app.session_state["building_details_tabs"] == "Tooltip"
    assert app.markdown[0].value == "stats=False;tooltip=True"
    assert not app.exception
