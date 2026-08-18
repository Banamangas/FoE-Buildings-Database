import logging

import pandas as pd
import streamlit as st

from foe_buildings import config
from foe_buildings import i18n as translations
from foe_buildings.data import loader as data_loader
from foe_buildings.data.calculations import combine_army_with_ge_gbg
from foe_buildings.ui import grid as ui_components
from foe_buildings.ui import tooltip as tooltip_renderer


def _render_stats_table(stats_data: list, lang_code: str) -> None:
    """Render the building stats table with icon, statistic, and value columns."""
    if stats_data:
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(
            stats_df,
            column_config={
                "Icon": st.column_config.ImageColumn(label="", width=None, pinned=True),
                "Statistic": st.column_config.TextColumn(
                    label=translations.get_text("stat_name", lang_code), width=None
                ),
                "Value": st.column_config.TextColumn(
                    label=translations.get_text("value", lang_code), width=None
                ),
            },
            hide_index=True,
            height=40 * len(stats_data) if len(stats_data) > 10 else 400,
            width="stretch",
        )
    else:
        st.info(translations.get_text("no_stats_available", lang_code))


def render_building_details(
    df_original: pd.DataFrame,
    selected_translated_era: str,
    lang_code: str,
    image_manager,
    show_per_square: bool,
    combine_army_stats: bool,
) -> None:
    """Render the Building Details tab."""
    st.header(translations.get_text("building_stats", lang_code))

    # Filter buildings by selected era (same as Home tab)
    df_era_filtered = df_original[
        df_original[config.COL_TRANSLATED_ERA] == selected_translated_era
    ].copy()

    # Create columns for layout
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        # Show currently selected era
        st.info(
            f"📍 {translations.translate_column('Era', lang_code)}: **{selected_translated_era}**",
            width=300,
        )

        # Building selection dropdown (only buildings from selected era)
        if config.SessionKeys.SELECTION_BUILDING not in st.session_state:
            st.session_state[config.SessionKeys.SELECTION_BUILDING] = 0

        building_names = sorted(df_era_filtered[config.COL_NAME].unique())
        selected_building = st.selectbox(
            label=translations.get_text("select_building", lang_code),
            options=[""] + building_names,
            index=st.session_state[config.SessionKeys.SELECTION_BUILDING],
            key="building_selector",
        )

        st.markdown("---")

    # Apply army stats combination if enabled
    if combine_army_stats:
        df_era_filtered = combine_army_with_ge_gbg(df_era_filtered)

    _building_match = (
        df_era_filtered[df_era_filtered[config.COL_NAME] == selected_building]
        if selected_building
        else pd.DataFrame()
    )
    if selected_building and selected_building != "" and not _building_match.empty:
        # Get the selected building data from the era-filtered dataframe
        building_data = _building_match.iloc[0].copy()

        # Apply per square calculation if enabled
        if (
            show_per_square
            and config.COL_SIZE in building_data
            and building_data[config.COL_SIZE] > 0
        ):
            building_size = building_data[config.COL_SIZE]
            # Apply per square calculation to numeric columns
            for col in building_data.index:
                if (
                    col not in config.PER_SQUARE_EXCLUDED_COLUMNS
                    and pd.api.types.is_numeric_dtype(type(building_data[col]))
                    and not pd.isna(building_data[col])
                ):
                    building_data[col] = round(building_data[col] / building_size, 8)

        # Show per square mode info if active
        if show_per_square:
            st.info("📐 " + translations.get_text("per_square_mode_active", lang_code))

        # Function to check if an icon exists for a column
        def has_icon(col_name: str) -> bool:
            return (
                col_name not in config.ICON_EXCLUDED_COLUMNS
                and ui_components.get_icon_base64(col_name) is not None
            )

        # --- Complete Stats Table with Image / In-Game Tooltip ---
        tab_stats, tab_tooltip = st.tabs(
            [
                translations.get_text("complete_stats_table", lang_code),
                translations.get_text("in_game_tooltip", lang_code),
            ],
            key="building_details_tabs",
            on_change="rerun",
        )

        if tab_stats.open:
            # Prepare data for the stats table
            stats_data = []

            # Get all columns from column groups in order
            for group_key, group_info in config.COLUMN_GROUPS.items():
                for col in group_info["columns"]:
                    if col in building_data:
                        value = building_data[col]

                        # Skip zero values and empty strings, but keep all boolean values (including False)
                        is_boolean = isinstance(
                            value, bool
                        ) or pd.api.types.is_bool_dtype(type(value))
                        if not is_boolean and (
                            value == 0 or value == "" or pd.isna(value)
                        ):
                            continue

                        # Get translated column name
                        translated_name = translations.translate_column(col, lang_code)

                        # Format value
                        if col in config.PERCENTAGE_COLUMNS:
                            formatted_value = f"{value:.0f}%"
                        elif isinstance(value, float):
                            formatted_value = (
                                f"{value:.2f}"
                                if value != int(value)
                                else f"{int(value)}"
                            )
                        elif is_boolean:
                            formatted_value = "✔️" if value else "❌"
                        else:
                            formatted_value = str(value)

                        # Check if column has an icon
                        icon_url = None
                        if col not in config.ICON_EXCLUDED_COLUMNS:
                            icon_base64 = ui_components.get_icon_base64(col)
                            if icon_base64:
                                icon_url = f"data:image/png;base64,{icon_base64}"

                        stats_data.append(
                            {
                                "Icon": icon_url,
                                "Statistic": translated_name,
                                "Value": formatted_value,
                            }
                        )

            with tab_stats:
                st.markdown(f"### {selected_building}")
                # Create layout with stats table on left and image on right
                building_asset_id = building_data.get(config.COL_ASSET_ID)
                if building_asset_id and image_manager.has_image(building_asset_id):
                    # Layout with table on left and image on right
                    table_col, img_col = st.columns([2, 4])

                    with table_col:
                        _render_stats_table(stats_data, lang_code)

                    with img_col:
                        image_url = image_manager.get_building_image_url(
                            building_asset_id
                        )
                        st.image(image_url, caption=selected_building, width="content")
                else:
                    # No image available, show table full width
                    _render_stats_table(stats_data, lang_code)

        if tab_tooltip.open:
            with tab_tooltip:
                try:
                    lookup = data_loader.load_building_entity_lookup()
                    building_id = building_data.get("id")
                    entity = lookup.get(building_id)
                    if entity and entity.get("components"):
                        building_asset_id = building_data.get(config.COL_ASSET_ID)
                        image_url = (
                            image_manager.get_building_image_url(building_asset_id)
                            if building_asset_id
                            and image_manager.has_image(building_asset_id)
                            else None
                        )
                        sections = tooltip_renderer.render_building_tooltip(
                            entity,
                            lang_code,
                            building_name=selected_building,
                            image_url=image_url,
                            era_key=building_data.get(config.COL_ERA),
                        )
                        tooltip_renderer.render_tooltip_sections(sections, lang_code)
                    else:
                        st.info(translations.get_text("no_tooltip_data", lang_code))
                except Exception:
                    logging.exception(
                        "Failed to render in-game tooltip for %s", selected_building
                    )
                    st.error(translations.get_text("tooltip_render_error", lang_code))
                    st.info(translations.get_text("no_tooltip_data", lang_code))
    else:
        st.info(translations.get_text("no_building_selected", lang_code))
