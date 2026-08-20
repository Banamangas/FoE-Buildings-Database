from foe_buildings.config import (
    ERAS_DICT,
    ERAS_LEVEL_MAP,
    WEIGHTABLE_COLUMNS,
    ADDITIVE_METRICS,
    RANKING_POINTS_PER_RESOURCE,
    SessionKeys,
    init_session_state,
)


def test_eras_level_map_has_22_entries():
    """There should be exactly 22 era levels."""
    assert len(ERAS_LEVEL_MAP) == 22


def test_eras_level_map_keys_match_eras_dict():
    """Every era key in ERAS_LEVEL_MAP must exist in ERAS_DICT."""
    for level, era_key in ERAS_LEVEL_MAP.items():
        assert era_key in ERAS_DICT, f"Level {level} era '{era_key}' not in ERAS_DICT"


def test_ranking_points_goods_eras_match_eras_dict():
    """Every era in RANKING_POINTS_PER_RESOURCE['goods'] must be a valid era."""
    for era_key in RANKING_POINTS_PER_RESOURCE["goods"]:
        assert era_key in ERAS_DICT, f"Goods era '{era_key}' not in ERAS_DICT"


def test_ranking_points_special_goods_eras_match_eras_dict():
    """Every era in RANKING_POINTS_PER_RESOURCE['special_goods'] must be valid."""
    for era_key in RANKING_POINTS_PER_RESOURCE["special_goods"]:
        assert era_key in ERAS_DICT, f"Special goods era '{era_key}' not in ERAS_DICT"


def test_session_keys_event_tooltip_event_exists():
    """Event tooltip event key should have the expected string value."""
    assert SessionKeys.SELECTED_EVENT_TOOLTIP_EVENT == "selected_event_tooltip_event"


def test_session_keys_event_tooltip_era_exists():
    """Event tooltip era key should have the expected string value."""
    assert SessionKeys.SELECTED_EVENT_TOOLTIP_ERA == "selected_event_tooltip_era"


def test_session_keys_no_duplicate_values():
    """No two SessionKeys should map to the same string value."""
    values = [
        v
        for k, v in vars(SessionKeys).items()
        if not k.startswith("_") and isinstance(v, str)
    ]
    assert len(values) == len(set(values)), f"Duplicate SessionKeys values: {values}"


def test_init_session_state_sets_event_tooltip_defaults(monkeypatch):
    """init_session_state should initialize event tooltip keys to empty strings."""
    import streamlit as st

    monkeypatch.setattr(st, "session_state", {})
    init_session_state()
    assert st.session_state[SessionKeys.SELECTED_EVENT_TOOLTIP_EVENT] == ""
    assert st.session_state[SessionKeys.SELECTED_EVENT_TOOLTIP_ERA] == ""


def test_additive_metrics_subset_of_weightable():
    """Every ADDITIVE_METRICS column must also be in WEIGHTABLE_COLUMNS."""
    for col in ADDITIVE_METRICS:
        assert (
            col in WEIGHTABLE_COLUMNS
        ), f"{col} in ADDITIVE_METRICS but not WEIGHTABLE_COLUMNS"
