import pandas as pd
import streamlit as st

from foe_buildings import config
from foe_buildings import i18n as translations
from foe_buildings.tabs.building_analysis.table import _render_column_analysis_subtab


def render_qi_boosts_subtab(
    df_viz_filtered: pd.DataFrame,
    lang_code: str,
    image_manager,
) -> None:
    st.header("🌌 " + translations.get_text("qi_boosts_analysis", lang_code))
    st.markdown(translations.get_text("qi_boosts_analysis_help", lang_code))

    # Get QI boost columns from config
    qi_boost_columns = config.COLUMN_GROUPS["qi"]["columns"]

    # Filter to only include QI boosts that exist in the data
    available_qi_boosts = [
        col for col in qi_boost_columns if col in df_viz_filtered.columns
    ]

    if not available_qi_boosts:
        st.warning(translations.get_text("no_qi_boosts_available", lang_code))
    else:
        # QI boost selection
        col1, col2 = st.columns([3, 1])

        with col1:
            selected_qi_boosts = st.multiselect(
                translations.get_text("qi_boosts_to_analyze", lang_code),
                options=available_qi_boosts,
                format_func=lambda x: translations.translate_column(x, lang_code),
                default=[],
                placeholder=translations.get_text("choose_an_option", lang_code),
                key="qi_boosts_selector",
            )

        with col2:
            # Display format toggle for percentage vs actual values
            show_actual_values = st.toggle(
                translations.get_text("show_actual_values_format", lang_code),
                value=True,
                key="qi_actual_values_toggle",
                help=translations.get_text("actual_values_format_help", lang_code),
            )

        if selected_qi_boosts:

            def _qi_config_builder(display_df, selected_cols, lang_code):
                extra = {}
                for col in selected_cols:
                    translated = translations.translate_column(col, lang_code)
                    if translated not in display_df.columns:
                        continue
                    if col in config.PERCENTAGE_COLUMNS:
                        fmt = "%.0f%%" if show_actual_values else "+%.0f%%"
                    else:
                        fmt = "%.0f"
                    extra[translated] = st.column_config.NumberColumn(
                        label=translated, width="medium", format=fmt
                    )
                return display_df, extra

            _render_column_analysis_subtab(
                df=df_viz_filtered,
                selected_cols=selected_qi_boosts,
                config_builder_fn=_qi_config_builder,
                export_prefix="qi_boosts_analysis",
                no_buildings_key="no_buildings_provide_qi_boosts",
                lang_code=lang_code,
                image_manager=image_manager,
            )
        else:
            st.info(translations.get_text("select_qi_boosts_to_analyze", lang_code))
