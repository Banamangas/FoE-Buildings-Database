from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, AgGridTheme, DataReturnMode

from foe_buildings import config
from foe_buildings import i18n as translations
from foe_buildings.data import calculations
from foe_buildings.ui import grid as ui_components


def _render_column_analysis_subtab(
    df: pd.DataFrame,
    selected_cols: list,
    config_builder_fn,
    export_prefix: str,
    no_buildings_key: str,
    lang_code: str,
    image_manager,
) -> None:
    """Render the shared results section for Consumables and QI Boosts subtabs.

    Args:
        df: Source DataFrame (all buildings for this era/filter).
        selected_cols: Columns chosen in the multiselect.
        config_builder_fn: Callable(display_df, selected_cols, lang_code) ->
            (display_df, extra_column_config_dict). May transform values and
            must return per-column NumberColumn config entries.
        export_prefix: File-name prefix for CSV/JSON downloads.
        no_buildings_key: i18n key shown when no buildings match the selection.
        lang_code: Active language code.
        image_manager: Cached image manager instance.
    """
    mask = (df[selected_cols] > 0).any(axis=1)
    df_filtered = df[mask].copy()

    if df_filtered.empty:
        st.info(translations.get_text(no_buildings_key, lang_code))
        return

    display_data = []
    for _, building in df_filtered.iterrows():
        building_id = building.get(config.COL_ASSET_ID)
        building_name = building.get(config.COL_NAME, "Unknown")
        building_size = building.get("size", "Unknown")
        needs_road = building.get("Road", False)
        road_text = (
            translations.get_text("yes", lang_code)
            if needs_road
            else translations.get_text("no", lang_code)
        )

        image_url = None
        if building_id and image_manager.has_image(building_id):
            image_url = image_manager.get_building_image_url(building_id)

        row_data = {
            "Building Image": image_url,
            "Building Name": building_name,
            "Size": building_size,
            "Road": road_text,
        }
        for col in selected_cols:
            value = building.get(col, 0)
            if value > 0:
                row_data[translations.translate_column(col, lang_code)] = value
        display_data.append(row_data)

    if not display_data:
        st.info(translations.get_text(no_buildings_key, lang_code))
        return

    display_df = pd.DataFrame(display_data)

    sort_cols = [
        translations.translate_column(col, lang_code)
        for col in selected_cols
        if translations.translate_column(col, lang_code) in display_df.columns
    ]
    if sort_cols:
        display_df = display_df.sort_values(by=sort_cols, ascending=False).reset_index(
            drop=True
        )

    display_df, extra_config = config_builder_fn(display_df, selected_cols, lang_code)

    column_config = {
        "Building Image": st.column_config.ImageColumn(label="🏢", width="small"),
        "Building Name": st.column_config.TextColumn(
            label=translations.get_text("building_name", lang_code), width="medium"
        ),
        "Size": st.column_config.TextColumn(
            label=translations.get_text("size", lang_code), width="small"
        ),
        "Road": st.column_config.TextColumn(
            label=translations.get_text("road", lang_code), width="small"
        ),
    }
    column_config.update(extra_config)

    st.subheader(f"📋 {translations.get_text('results_summary', lang_code)}")
    st.write(
        f"**{len(display_df)} {translations.get_text('buildings_found', lang_code)}**"
    )
    st.dataframe(
        display_df,
        column_config=column_config,
        hide_index=True,
        width="content",
        height=min(600, max(200, len(display_df) * 40 + 100)),
    )

    if len(display_df) > 0:
        st.markdown("---")
        export_df = display_df.drop(columns=["Building Image"], errors="ignore")
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label=translations.get_text("export_csv", lang_code),
                data=export_df.to_csv(index=False, sep=";").encode("utf-8"),
                file_name=f"{export_prefix}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv",
                mime="text/csv",
                key=f"export_{export_prefix}_csv",
            )
        with col2:
            st.download_button(
                label=translations.get_text("export_json", lang_code),
                data=export_df.to_json(orient="records", force_ascii=False).encode(
                    "utf-8"
                ),
                file_name=f"{export_prefix}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json",
                mime="application/json",
                key=f"export_{export_prefix}_json",
            )


def render_table_subtab(
    df_viz_filtered: pd.DataFrame,
    selected_columns: list,
    lang_code: str,
    image_manager,
    use_icons: bool,
    show_labels: bool,
    enable_heatmap: bool,
    show_per_square: bool,
    hide_zero_production: bool,
    buildings_filtered_by_zero_production: int,
    page_size: int,
    selected_translated_era: str,
) -> None:
    # --- Weight Presets ---
    preset_keys = list(config.WEIGHT_PRESETS.keys())

    st.markdown(
        f"<div style='padding-top:6px;padding-bottom:6px;font-size:1.2rem;font-weight:600'>{translations.get_text('weight_presets_label', lang_code)}</div>",
        unsafe_allow_html=True,
    )

    preset_col1, preset_col2 = st.columns([1, 3])

    with preset_col1:
        selected_preset_key = st.selectbox(
            translations.get_text("weight_presets_label", lang_code),
            options=[None] + preset_keys,
            format_func=lambda k: ""
            if k is None
            else translations.get_text(f"weight_preset_{k}", lang_code),
            label_visibility="collapsed",
            help=translations.get_text("weight_presets_help", lang_code),
            key="weight_preset_selector",
        )
    with preset_col2:
        if st.button(
            translations.get_text("load_preset", lang_code),
            disabled=selected_preset_key is None,
            key="load_preset_table",
        ):
            st.session_state["_pending_preset_load"] = config.WEIGHT_PRESETS[
                selected_preset_key
            ]
            st.rerun()

    try:
        # --- Prepare Display Columns ---
        # Filter columns that exist in the filtered dataframe
        existing_columns_for_display = []

        # Process selected columns in the order they were selected
        for col in selected_columns:
            if (
                col in df_viz_filtered.columns
                and col not in existing_columns_for_display
            ):
                existing_columns_for_display.append(col)

        # Ensure uniqueness while preserving order
        existing_columns_for_display = list(dict.fromkeys(existing_columns_for_display))
        config.logger.info(
            f"Columns selected for display: {existing_columns_for_display}"
        )

        # Create the final DataFrame for AgGrid
        if not existing_columns_for_display:
            st.warning("No columns selected or available for display.")
            st.stop()

        df_display = df_viz_filtered[existing_columns_for_display].copy()
        df_display = df_display.sort_values(by=config.COL_NAME, ascending=True)

        # --- Apply "Per Square" Calculation ---
        if show_per_square and config.COL_SIZE in df_viz_filtered.columns:
            divisor_col = (
                df_viz_filtered[config.COL_SIZE]
                .reindex(df_display.index, fill_value=1)
                .astype(float)
                .replace(0, 1)
            )
            df_display = calculations.apply_per_square(df_display, divisor_col)

        # --- Configure and Display AgGrid ---
        eff_min = (
            df_display[config.COL_WEIGHTED_EFFICIENCY].min()
            if config.COL_WEIGHTED_EFFICIENCY in df_display and not df_display.empty
            else 0
        )
        eff_max = (
            df_display[config.COL_WEIGHTED_EFFICIENCY].max()
            if config.COL_WEIGHTED_EFFICIENCY in df_display and not df_display.empty
            else 0
        )
        if pd.isna(eff_min):
            eff_min = 0
        if pd.isna(eff_max):
            eff_max = 0

        # --- Prepare Export DataFrame with Translated Column Names ---
        df_export = df_display.copy()
        # Create mapping of original to translated column names
        column_translation_map = {
            col: translations.translate_column(col, lang_code)
            for col in df_export.columns
        }
        # Rename columns to translated names
        df_export.rename(columns=column_translation_map, inplace=True)
        config.logger.info(f"Column translations for export: {column_translation_map}")

        # --- Export Buttons ---
        col1, col2 = st.columns([1, 10])
        with col1:
            # CSV Export with proper UTF-8 encoding and BOM
            buffer_csv = BytesIO()
            # Add UTF-8 BOM manually
            buffer_csv.write("\ufeff".encode("utf-8"))
            # Write CSV data with translated column names
            csv_string = df_export.to_csv(index=False, sep=";")
            buffer_csv.write(csv_string.encode("utf-8"))
            buffer_csv.seek(0)
            csv_data = buffer_csv.getvalue()

            st.download_button(
                label=translations.get_text("export_csv", lang_code),
                data=csv_data,
                file_name=f"foe_buildings_{selected_translated_era}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv",
                mime="text/csv; charset=utf-8",
                key="export_csv",
            )
        with col2:
            # JSON Export with translated column names and proper UTF-8 encoding
            json_string = df_export.to_json(
                orient="records", date_format="iso", force_ascii=False
            )
            json_data = json_string.encode("utf-8")

            st.download_button(
                label=translations.get_text("export_json", lang_code),
                data=json_data,
                file_name=f"foe_buildings_{selected_translated_era}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json",
                mime="application/json; charset=utf-8",
                key="export_json",
            )

        grid_options = ui_components.build_grid_options(
            df_display=df_display,
            lang_code=lang_code,
            use_icons=use_icons,
            show_labels=show_labels,
            enable_heatmap=enable_heatmap,
            eff_min=eff_min,
            eff_max=eff_max,
            page_size=page_size,
        )

        # --- Display Filter Information ---
        if hide_zero_production and buildings_filtered_by_zero_production > 0:
            st.info(
                translations.get_text("zero_production_filter_info", lang_code).format(
                    count=buildings_filtered_by_zero_production
                )
            )

        # --- Create a dynamic key to force re-render and auto-sizing when switching language ---
        grid_key = f"building_grid_{lang_code}"
        config.logger.debug(f"Using AgGrid key: {grid_key}")

        grid_return = AgGrid(
            df_display,
            gridOptions=grid_options,
            custom_css=ui_components.CUSTOM_CSS,
            allow_unsafe_jscode=True,
            theme=AgGridTheme.STREAMLIT,
            height=800,
            width="100%",
            key=grid_key,
            data_return_mode=DataReturnMode.AS_INPUT,
        )

        builingRows = grid_return.selected_rows  # Get selected row
        if builingRows is not None:  # if a row is selected
            buildingIndex = int(builingRows.index[0]) + 1  # Get selected row's Index
            if (
                buildingIndex != st.session_state[config.SessionKeys.SELECTION_BUILDING]
            ):  # if changed
                st.session_state[config.SessionKeys.SELECTION_BUILDING] = (
                    buildingIndex  # set to new value
                )
                st.rerun()

        # --- Display Disclaimer ---
        st.markdown("***")
        st.markdown(translations.get_text("efficiency_disclaimer", lang_code))

        # --- Credits Section ---
        st.markdown("***")
        st.markdown(translations.get_text("credits_title", lang_code))

        # Create columns for credits layout
        credits_col1, credits_col2 = st.columns(2)

        with credits_col1:
            st.markdown(f"**{translations.get_text('data_sources', lang_code)}**")
            st.markdown(f"- {translations.get_text('foe_buildings_db', lang_code)}")
            st.markdown(f"- {translations.get_text('innogames_foe', lang_code)}")

            st.markdown(f"**{translations.get_text('development_tools', lang_code)}**")
            st.markdown(
                f"- [Streamlit](https://streamlit.io/) - {translations.get_text('web_framework', lang_code)}"
            )
            st.markdown(
                f"- [AG-Grid](https://www.ag-grid.com/) - {translations.get_text('data_grid', lang_code)}"
            )
            st.markdown(
                f"- [Pandas](https://pandas.pydata.org/) - {translations.get_text('data_analysis', lang_code)}"
            )

        with credits_col2:
            st.markdown(f"**{translations.get_text('community', lang_code)}**")
            st.markdown(f"- {translations.get_text('foe_community', lang_code)}")
            st.markdown(f"- {translations.get_text('beta_testers', lang_code)}")

            st.markdown(f"**{translations.get_text('special_thanks', lang_code)}**")
            st.markdown(f"- {translations.get_text('github_contributors', lang_code)}")

        # Footer
        st.markdown("---")
        st.markdown(
            f"<div style='text-align: center; color: #666; font-size: 0.9em;'>"
            f"{translations.get_text('made_with_love', lang_code)} | "
            f"{translations.get_text('not_affiliated', lang_code)}"
            f"</div>",
            unsafe_allow_html=True,
        )

    except Exception as e:
        st.error(f"An error occurred during app execution: {str(e)}")
        config.logger.error(f"Error during main app execution: {e}", exc_info=True)
