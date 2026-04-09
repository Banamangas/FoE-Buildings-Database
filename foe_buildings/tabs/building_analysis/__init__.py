import pandas as pd
import streamlit as st

from foe_buildings import config
from foe_buildings import i18n as translations
from foe_buildings.data import calculations
from foe_buildings.data.calculations import cached_calculate_era_stats
from foe_buildings.tabs.building_analysis.weights import (
    _weights_state_hash,
    render_weights_subtab,
)
from foe_buildings.tabs.building_analysis.table import render_table_subtab
from foe_buildings.tabs.building_analysis.consumables import render_consumables_subtab
from foe_buildings.tabs.building_analysis.qi_boosts import render_qi_boosts_subtab

logger = config.logger


def render_building_analysis(
    df_viz_filtered: pd.DataFrame,
    df_original: pd.DataFrame,
    user_weights: dict,
    user_context: dict,
    user_boosts: dict,
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
    """Render the Building Analysis tab with subtab routing."""
    # Initialize active subtab in session state
    if config.SessionKeys.ACTIVE_ANALYSIS_SUBTAB not in st.session_state:
        st.session_state[config.SessionKeys.ACTIVE_ANALYSIS_SUBTAB] = 0

    # Subtab selector with session state persistence
    subtab_names = [
        translations.get_text("building_table", lang_code),
        translations.get_text("weights", lang_code),
        translations.get_text("consumables_analysis", lang_code),
        translations.get_text("qi_boosts_analysis", lang_code),
    ]

    selected_subtab = st.radio(
        label="Analysis Navigation",
        options=range(len(subtab_names)),
        format_func=lambda x: subtab_names[x],
        index=st.session_state[config.SessionKeys.ACTIVE_ANALYSIS_SUBTAB],
        key="analysis_subtab_selector",
        horizontal=True,
        label_visibility="collapsed",
    )

    # Update session state when subtab changes
    if selected_subtab != st.session_state[config.SessionKeys.ACTIVE_ANALYSIS_SUBTAB]:
        st.session_state[config.SessionKeys.ACTIVE_ANALYSIS_SUBTAB] = selected_subtab
        st.rerun()

    # --- Weights Subtab (Process first for user_weights, user_context, user_boosts) ---
    if st.session_state[config.SessionKeys.ACTIVE_ANALYSIS_SUBTAB] == 1:
        render_weights_subtab(
            df_original=df_original,
            user_weights=user_weights,
            user_context=user_context,
            user_boosts=user_boosts,
            lang_code=lang_code,
        )

    # Calculate efficiency if weights are set (after processing weights subtab)
    weights_active = (
        any(w > 0 for w in user_weights.values()) if user_weights else False
    )
    logger.debug(
        f"Main Analysis: Weights active: {weights_active}, User weights: {user_weights}"
    )

    if weights_active and not df_viz_filtered.empty:
        scoring_mode = st.session_state.get(config.SessionKeys.SCORING_MODE, "classic")
        w_hash = _weights_state_hash(
            user_weights, user_context, user_boosts, scoring_mode
        )
        df_hash = hash(tuple(df_viz_filtered.index.tolist()))
        cached = st.session_state.get(config.SessionKeys.EFFICIENCY_CACHE)

        if (
            cached is not None
            and cached.get("w_hash") == w_hash
            and cached.get("df_hash") == df_hash
        ):
            df_viz_filtered[config.COL_TOTAL_SCORE] = cached["scores"]
            df_viz_filtered[config.COL_WEIGHTED_EFFICIENCY] = cached["efficiency"]
            logger.debug("Efficiency scores served from session cache")
        else:
            logger.info("Applying efficiency calculations to main analysis table")
            era_stats_df = (
                cached_calculate_era_stats(df_original)
                if st.session_state.get(config.SessionKeys.SCORING_MODE, "classic")
                == "normalised"
                else None
            )
            with st.spinner(translations.get_text("calculating_scores", lang_code)):
                df_viz_filtered = calculations.calculate_direct_weighted_efficiency(
                    df=df_viz_filtered,
                    user_weights=user_weights,
                    user_context=user_context,
                    user_boosts=user_boosts,
                    era_stats_df=era_stats_df,
                )
            st.session_state[config.SessionKeys.EFFICIENCY_CACHE] = {
                "w_hash": w_hash,
                "df_hash": df_hash,
                "scores": df_viz_filtered[config.COL_TOTAL_SCORE].copy(),
                "efficiency": df_viz_filtered[config.COL_WEIGHTED_EFFICIENCY].copy(),
            }
            logger.info("Main Analysis: Efficiency calculations completed successfully")
    else:
        logger.info(
            "Main Analysis: No active weights or empty dataframe - efficiency columns remain at 0.0"
        )

    # --- Table Subtab ---
    if st.session_state[config.SessionKeys.ACTIVE_ANALYSIS_SUBTAB] == 0:
        render_table_subtab(
            df_viz_filtered=df_viz_filtered,
            selected_columns=selected_columns,
            lang_code=lang_code,
            image_manager=image_manager,
            use_icons=use_icons,
            show_labels=show_labels,
            enable_heatmap=enable_heatmap,
            show_per_square=show_per_square,
            hide_zero_production=hide_zero_production,
            buildings_filtered_by_zero_production=buildings_filtered_by_zero_production,
            page_size=page_size,
            selected_translated_era=selected_translated_era,
        )

    # --- Consumables Analysis Subtab ---
    if st.session_state[config.SessionKeys.ACTIVE_ANALYSIS_SUBTAB] == 2:
        render_consumables_subtab(
            df_viz_filtered=df_viz_filtered,
            lang_code=lang_code,
            image_manager=image_manager,
        )

    # --- QI Boosts Analysis Subtab ---
    if st.session_state[config.SessionKeys.ACTIVE_ANALYSIS_SUBTAB] == 3:
        render_qi_boosts_subtab(
            df_viz_filtered=df_viz_filtered,
            lang_code=lang_code,
            image_manager=image_manager,
        )
