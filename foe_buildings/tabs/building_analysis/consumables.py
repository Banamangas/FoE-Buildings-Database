import pandas as pd
import streamlit as st

from foe_buildings import config
from foe_buildings import i18n as translations
from foe_buildings.tabs.building_analysis.table import _render_column_analysis_subtab


def render_consumables_subtab(
    df_viz_filtered: pd.DataFrame,
    lang_code: str,
    image_manager,
) -> None:
    st.header("🛠️ " + translations.get_text("consumables_analysis", lang_code))
    st.markdown(translations.get_text("consumables_analysis_help", lang_code))

    # Get consumable columns from config
    consumable_columns = config.COLUMN_GROUPS["consumables"]["columns"]

    # Filter to only include consumables that exist in the data
    available_consumables = [
        col for col in consumable_columns if col in df_viz_filtered.columns
    ]

    if not available_consumables:
        st.warning(translations.get_text("no_consumables_available", lang_code))
    else:
        # Consumable selection
        col1, col2 = st.columns([3, 1])

        with col1:
            selected_consumables = st.multiselect(
                translations.get_text("consumables_to_analyze", lang_code),
                options=available_consumables,
                format_func=lambda x: translations.translate_column(x, lang_code),
                default=[],
                placeholder=translations.get_text("choose_an_option", lang_code),
                key="consumables_selector",
            )

        # Display format toggle
        show_frequency_format = st.toggle(
            translations.get_text("show_frequency_format", lang_code),
            value=False,
            key="consumables_frequency_toggle",
            help=translations.get_text("frequency_format_help", lang_code),
        )

        if selected_consumables:

            def _consumables_config_builder(display_df, selected_cols, lang_code):
                extra = {}
                for col in selected_cols:
                    translated = translations.translate_column(col, lang_code)
                    if translated not in display_df.columns:
                        continue
                    if show_frequency_format:
                        display_df[translated] = (1 / display_df[translated]).round(2)
                        suffix = " days" if lang_code == "en" else " jours"
                        prefix = "1 every " if lang_code == "en" else "1 tous les "
                        help_text = (
                            "Days per unit (lower is better)"
                            if lang_code == "en"
                            else "Jours par unité (moins c'est mieux)"
                        )
                        extra[translated] = st.column_config.NumberColumn(
                            label=translated,
                            width="medium",
                            format=prefix + "%.10g" + suffix,
                            help=help_text,
                        )
                    else:
                        suffix = "/day" if lang_code == "en" else "/jour"
                        display_df[translated] = display_df[translated].round(2)
                        extra[translated] = st.column_config.NumberColumn(
                            label=translated,
                            width="medium",
                            format="%.10g" + suffix,
                        )
                return display_df, extra

            _render_column_analysis_subtab(
                df=df_viz_filtered,
                selected_cols=selected_consumables,
                config_builder_fn=_consumables_config_builder,
                export_prefix="consumables_analysis",
                no_buildings_key="no_buildings_produce_consumables",
                lang_code=lang_code,
                image_manager=image_manager,
            )
        else:
            st.info(translations.get_text("select_consumables_to_analyze", lang_code))
