from contextlib import nullcontext

from foe_buildings.ui import tooltip
from foe_buildings.ui.styles import load_tooltip_css
from foe_buildings.ui.tooltip import (
    RandomOutcome,
    RandomProductionGroup,
    TooltipRow,
    TooltipSection,
    _random_group_html,
    _tooltip_row_html,
)
from foe_buildings.ui.tooltip_icons import ResolvedIcon


def random_group(
    key: str,
    amount: int,
    probability: int,
    *,
    duration: int | None = None,
) -> RandomProductionGroup:
    label = "Coins" if key == "money" else "Forge Points"
    row = TooltipRow(
        icon=ResolvedIcon(key, f"https://cdn/{key}.png", label),
        label=label,
        value=str(amount),
    )
    return RandomProductionGroup(
        outcomes=[RandomOutcome(row=row, probability=probability)],
        duration=duration,
    )


def test_quantitative_row_hides_visible_label_but_keeps_accessible_name():
    row = TooltipRow(
        icon=ResolvedIcon("money", "https://cdn/money.png", "Coins"),
        label="Coins",
        value="1,000",
    )

    html = _tooltip_row_html(row, "en")

    assert '<img src="https://cdn/money.png"' in html
    assert ">1,000<" in html
    assert ">Coins:" not in html
    assert 'aria-label="Coins: 1,000"' in html
    assert 'title="Coins: 1,000"' in html


def test_semantic_row_keeps_visible_text():
    row = TooltipRow(
        icon=ResolvedIcon("icon_unique_building", None, "Trait"),
        label="Trait",
        value="Unique building",
        show_label=True,
    )

    html = _tooltip_row_html(row, "en")

    assert "Unique building" in html
    assert ">Trait:" not in html
    assert "tooltip-icon-missing" in html


def test_rendering_escapes_api_derived_accessible_text():
    row = TooltipRow(None, '<script>alert("x")</script>', "1")

    html = _tooltip_row_html(row, "en")

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&quot;x&quot;" in html


def test_row_escapes_icon_suffix_and_marker_metadata():
    row = TooltipRow(
        icon=ResolvedIcon(
            "money", 'https://cdn/money.png?size="large"', "Coins <primary>"
        ),
        label="Coins & currency",
        value="1 < 2",
        suffix='bonus "value"',
        duration=3600,
        markers=[
            ResolvedIcon(
                "when_motivated",
                'https://cdn/marker.png?kind="motivation"',
                "When <motivated>",
            )
        ],
    )

    html = _tooltip_row_html(row, "en")

    assert "money.png?size=&quot;large&quot;" in html
    assert "Coins &lt;primary&gt;" in html
    assert "Coins &amp; currency: 1 &lt; 2" in html
    assert "bonus &quot;value&quot;" in html
    assert ">1h<" in html
    assert "marker.png?kind=&quot;motivation&quot;" in html
    assert "When &lt;motivated&gt;" in html


def test_random_groups_have_separate_styled_containers_and_probabilities():
    first = random_group("money", 10, 25)
    second = random_group("strategy_points", 2, 75)

    html = _random_group_html(first, "en") + _random_group_html(second, "en")

    assert html.count('class="tooltip-random-group"') == 2
    assert ">25%<" in html
    assert ">75%<" in html
    assert html.count('aria-label="Random production') == 2


def test_random_group_renders_its_duration_and_markers_without_visible_label():
    group = random_group("money", 10, 25, duration=86400)
    group.markers.append(
        ResolvedIcon("when_motivated", "https://cdn/motivated.png", "Motivated")
    )

    html = _random_group_html(group, "en")

    assert ">1d<" in html
    assert 'src="https://cdn/motivated.png"' in html
    assert ">Random production<" not in html


def test_renderer_injects_css_once_and_keeps_header_image_and_group_order(
    monkeypatch,
):
    row = TooltipRow(None, "Coins", "10")
    group = random_group("strategy_points", 2, 75)
    section = TooltipSection(
        key="produces",
        title="Produces",
        rows=[row],
        header="Test <Building>",
        image_url="https://cdn/building.png",
        random_groups=[group],
        shared_duration=86400,
    )
    markdown_calls = []
    image_calls = []
    monkeypatch.setattr(tooltip.st, "container", nullcontext)
    monkeypatch.setattr(
        tooltip.st,
        "markdown",
        lambda body, **kwargs: markdown_calls.append((body, kwargs)),
    )
    monkeypatch.setattr(
        tooltip.st,
        "image",
        lambda image, **kwargs: image_calls.append((image, kwargs)),
    )

    tooltip.render_tooltip_sections([section], "en")

    assert markdown_calls[0] == (
        load_tooltip_css(),
        {"unsafe_allow_html": True},
    )
    assert sum(body == load_tooltip_css() for body, _ in markdown_calls) == 1
    assert markdown_calls[1][0] == "### Test &lt;Building&gt;"
    assert image_calls == [("https://cdn/building.png", {"width": "content"})]
    assert markdown_calls[2][0] == "**Produces (1d)**"
    row_index = next(
        index
        for index, (body, _) in enumerate(markdown_calls)
        if 'class="foe-tooltip-row"' in body
    )
    group_index = next(
        index
        for index, (body, _) in enumerate(markdown_calls)
        if 'class="tooltip-random-group"' in body
    )
    assert row_index < group_index
