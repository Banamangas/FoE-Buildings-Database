import json
import os

import pandas as pd
import streamlit as st

from foe_buildings import config
from foe_buildings import i18n as translations
from foe_buildings.config import SessionKeys
from foe_buildings.data import calculations
from foe_buildings.data import loader as data_loader
from foe_buildings.data.calculations import (
    cached_calculate_era_stats,
    combine_army_with_ge_gbg,
)
from foe_buildings.ui import columns as column_selector
from foe_buildings.ui import filters as advanced_filters
from foe_buildings.ui.images import get_cached_image_manager
from foe_buildings.ui.styles import load_tab_css
from foe_buildings.tabs.building_analysis import render_building_analysis
from foe_buildings.tabs.building_details import render_building_details
from foe_buildings.tabs.city_analysis import render_city_analysis_tab
from foe_buildings.tabs.visualizations import render_data_visualizations

logger = config.logger

if not os.path.exists(config.APP_ICON):
    logger.warning(
        "App icon not found at '%s'; page icon will be missing.", config.APP_ICON
    )


@st.cache_data
def apply_translations(df: pd.DataFrame, language_code: str) -> pd.DataFrame:
    """Translate building names, events, eras, and yes/no values in-place (cached)."""
    df_translated = df.copy()

    if config.COL_NAME in df_translated.columns:
        df_translated[config.COL_NAME] = df_translated[config.COL_NAME].map(
            lambda name: translations.translate_building_name(name, language_code)
        )
    else:
        logger.error("'name' column missing after data load.")

    if config.COL_EVENT in df_translated.columns:
        df_translated[config.COL_EVENT] = df_translated[config.COL_EVENT].map(
            lambda key: translations.translate_event_key(key, language_code)
        )
    else:
        logger.error("'Event' column missing after data load.")

    if config.COL_ERA in df_translated.columns:
        df_translated[config.COL_TRANSLATED_ERA] = df_translated[config.COL_ERA].map(
            lambda key: translations.translate_era_key(key, language_code)
        )
    else:
        logger.error("'Era' column not found after data load. Cannot translate eras.")
        df_translated[config.COL_TRANSLATED_ERA] = "Error"

    if config.COL_LIMITED in df_translated.columns:
        df_translated[config.COL_LIMITED] = df_translated[config.COL_LIMITED].map(
            lambda key: translations.translate_yesno_key(key, language_code)
        )
    else:
        logger.error(
            "'Limited' column not found after data load. Cannot translate Limited."
        )
        df_translated[config.COL_LIMITED] = "Error"

    if config.COL_ALLY_ROOM in df_translated.columns:
        df_translated[config.COL_ALLY_ROOM] = df_translated[config.COL_ALLY_ROOM].map(
            lambda key: translations.translate_yesno_key(key, language_code)
        )
    else:
        logger.error(
            "'Ally room' column not found after data load. Cannot translate Ally room."
        )
        df_translated[config.COL_ALLY_ROOM] = "Error"

    return df_translated


def main() -> None:
    # --- Page Config ---
    st.set_page_config(
        layout="wide", page_title="FoE Building Database", page_icon=config.APP_ICON
    )

    # --- Language Selection with Session State ---
    # Initialize language in session state if not exists
    if SessionKeys.LANGUAGE not in st.session_state:
        st.session_state[SessionKeys.LANGUAGE] = "English"

    # Language selector with session state
    selected_language = st.sidebar.selectbox(
        "Select Language / Choisir la langue",
        options=list(translations.LANGUAGES.keys()),
        index=list(translations.LANGUAGES.keys()).index(
            st.session_state[SessionKeys.LANGUAGE]
        ),
        key="language_selector",
    )

    # Update session state if language changed
    if selected_language != st.session_state[SessionKeys.LANGUAGE]:
        st.session_state[SessionKeys.LANGUAGE] = selected_language
        # Force rerun to update translations
        st.rerun()

    lang_code = translations.LANGUAGES[selected_language]

    # --- App Title and Description ---
    st.title(translations.get_text("title", lang_code))
    st.markdown(translations.get_text("description", lang_code))

    # --- Data Loading (Cached) ---
    # load_and_process_data() fetches from the VPS API and caches for 23 hours.
    # To refresh immediately after a data update, use data_loader.clear_cache().
    try:
        with st.spinner(translations.get_text("loading_data", lang_code)):
            df_original = data_loader.load_and_process_data()

        if df_original.empty:
            st.warning(
                "No building data loaded. The API may be updating — please try again shortly."
            )
            st.stop()

        # Apply cached translations
        df_original = apply_translations(df_original, lang_code)

        # Save translation file (only when needed)
        with open(
            os.path.join(
                config.TRANSLATIONS_PATH, "to_be_translated_building_names.json"
            ),
            "w",
        ) as f:
            json.dump(translations.TO_BE_TRANSLATED_BUILDING_NAMES, f)

        # Use cached image manager
        cached_image_manager = get_cached_image_manager()

    except Exception as e:
        st.error(f"Failed during initial data loading or processing: {e}")
        logger.error(f"Failed during initial data load/process: {e}", exc_info=True)
        st.stop()

    # ================== Sidebar Configuration ==================
    st.sidebar.header(translations.get_text("filters", lang_code))

    # --- Advanced Mode Toggle ---
    advanced_mode = st.sidebar.toggle(
        "🔧 " + translations.get_text("advanced_mode", lang_code),
        value=False,
        key="advanced_mode_toggle",
        help=translations.get_text("advanced_mode_help", lang_code),
    )

    # --- Era Filter ---
    # Get unique raw era keys and sort them according to ERAS_DICT order
    unique_raw_eras = df_original[config.COL_ERA].unique()
    # Create a list of eras in ERAS_DICT order that exist in our data
    ordered_raw_eras = [
        era_key for era_key in config.ERAS_DICT.keys() if era_key in unique_raw_eras
    ]
    # Add any eras that exist in data but not in ERAS_DICT (fallback)
    missing_eras = [
        era for era in unique_raw_eras if era not in config.ERAS_DICT.keys()
    ]
    ordered_raw_eras.extend(
        sorted(missing_eras)
    )  # Sort missing ones alphabetically as fallback

    # Translate the ordered era keys to get the properly ordered translated names
    available_eras = [
        translations.translate_era_key(era_key, lang_code)
        for era_key in ordered_raw_eras
    ]

    default_translated_era = translations.translate_era_key(
        "SpaceAgeSpaceHub", lang_code
    )
    try:
        default_era_index = available_eras.index(default_translated_era)
    except ValueError:
        default_era_index = 0
        logger.warning(
            f"Default translated era '{default_translated_era}' not found. Defaulting to index 0."
        )

    selected_translated_era = st.sidebar.selectbox(
        label=translations.translate_column("era", lang_code),
        options=available_eras,
        index=default_era_index,
        key="era_filter",
    )

    # --- Event Filter ---
    available_events = sorted(df_original[config.COL_EVENT].unique())
    selected_events = st.sidebar.multiselect(
        label=translations.translate_column("Event", lang_code),
        options=available_events,
        placeholder=translations.get_text("choose_an_option", lang_code),
        key="event_filter",
    )

    # --- Dynamic Name Filter ---
    # Create a subset dataframe filtered by era and event for the name filter
    df_for_name_filter = df_original[
        df_original[config.COL_TRANSLATED_ERA] == selected_translated_era
    ].copy()
    if selected_events:
        df_for_name_filter = df_for_name_filter[
            df_for_name_filter[config.COL_EVENT].isin(selected_events)
        ]

    # Initialize dynamic filters for building names only
    with st.sidebar:
        available_name_filters = sorted(df_for_name_filter[config.COL_NAME].unique())
        name_filter = st.multiselect(
            label=translations.get_text("search_label", lang_code),
            options=available_name_filters,
            placeholder=translations.get_text("choose_an_option", lang_code),
            key="name_filter_fallback",
        )

    # --- UI Options ---
    if advanced_mode:
        # Full options in advanced mode
        use_icons = st.sidebar.checkbox(
            translations.get_text("display_icons", lang_code),
            value=True,
            key="display_icons_checkbox",
            help=translations.get_text("display_icons_help", lang_code),
        )
        show_labels = (
            st.sidebar.checkbox(
                translations.get_text("show_labels", lang_code),
                value=False,
                key="show_labels_checkbox",
            )
            if use_icons
            else False
        )
        show_per_square = st.sidebar.checkbox(
            "📐 " + translations.get_text("value_per_tile", lang_code),
            value=False,
            key="per_square_checkbox",
        )
        enable_heatmap = st.sidebar.checkbox(
            translations.get_text("enable_heatmap", lang_code),
            value=True,
            key="heatmap_checkbox",
        )
        hide_zero_production = st.sidebar.checkbox(
            translations.get_text("hide_zero_production", lang_code),
            value=False,
            key="hide_zero_production_checkbox",
            help=translations.get_text("hide_zero_production_help", lang_code),
        )

        combine_army_stats = st.sidebar.checkbox(
            "⚔️ " + translations.get_text("combine_army_stats", lang_code),
            value=False,
            key="combine_army_stats_checkbox",
            help=translations.get_text("combine_army_stats_help", lang_code),
        )
    else:
        # Simplified options in easy mode
        use_icons = True  # Always use icons in easy mode
        show_labels = False  # Never show labels in easy mode
        enable_heatmap = True  # Always enable heatmap in easy mode
        hide_zero_production = False  # Never hide zero production in easy mode

        # Only show essential options
        show_per_square = st.sidebar.checkbox(
            "📐 " + translations.get_text("value_per_tile", lang_code),
            value=False,
            key="per_square_checkbox_easy",
            help=translations.get_text("value_per_tile_help", lang_code),
        )

        combine_army_stats = st.sidebar.checkbox(
            "⚔️ " + translations.get_text("combine_army_stats", lang_code),
            value=False,
            key="combine_army_stats_checkbox_easy",
            help=translations.get_text("combine_army_simple_help", lang_code),
        )

    page_size_options = [25, 50, 100]
    page_size = st.sidebar.selectbox(
        translations.get_text("page_size", lang_code),
        options=page_size_options,
        index=1,  # default to 50
        key="page_size_selector",
    )

    # --- Advanced Filters ---
    if advanced_mode:
        with st.sidebar:
            # Apply army stats combination to the dataframe used for filters if enabled
            df_for_filters = (
                combine_army_with_ge_gbg(df_original)
                if combine_army_stats
                else df_original
            )
            df_filtered_by_advanced = advanced_filters.render_advanced_filters(
                df_for_filters, lang_code
            )
    else:
        # No advanced filters in easy mode
        df_filtered_by_advanced = df_original

    # --- Enhanced Column Selection ---
    with st.sidebar:
        # Apply army stats combination to the dataframe used for column selection if enabled
        df_for_columns = (
            combine_army_with_ge_gbg(df_original) if combine_army_stats else df_original
        )

        if advanced_mode:
            # Full column selector with all features in advanced mode
            selected_columns = column_selector.render_enhanced_column_selector(
                df_for_columns, lang_code
            )
        else:
            # Simplified column selector in easy mode (no search functionality)
            selected_columns = column_selector.render_enhanced_column_selector(
                df_for_columns, lang_code, show_search=False
            )

    # --- Initialize Weights ---
    # Initialize weights dictionary before tabs and preserve in session state
    if SessionKeys.USER_WEIGHTS not in st.session_state:
        st.session_state[SessionKeys.USER_WEIGHTS] = {}
    if SessionKeys.USER_CONTEXT not in st.session_state:
        st.session_state[SessionKeys.USER_CONTEXT] = {}
    if SessionKeys.USER_BOOSTS not in st.session_state:
        st.session_state[SessionKeys.USER_BOOSTS] = {}
    if SessionKeys.SCORING_MODE not in st.session_state:
        st.session_state[SessionKeys.SCORING_MODE] = "classic"

    # Apply any pending weight preset BEFORE weights are read or widgets are rendered.
    _pending_preset = st.session_state.pop("_pending_preset_load", None)
    if _pending_preset is not None:
        for k in list(st.session_state[SessionKeys.USER_WEIGHTS].keys()):
            st.session_state[SessionKeys.USER_WEIGHTS][k] = 0.0
            st.session_state[f"weight_{k}"] = 0.0
        for k, v in _pending_preset.get("weights", {}).items():
            st.session_state[SessionKeys.USER_WEIGHTS][k] = float(v)
            st.session_state[f"weight_{k}"] = float(v)
        mode = _pending_preset.get("mode", "classic")
        st.session_state[SessionKeys.SCORING_MODE] = mode
        st.session_state["scoring_mode_radio"] = mode
        if SessionKeys.SELECTED_COLUMNS_SET in st.session_state:
            st.session_state[SessionKeys.SELECTED_COLUMNS_SET].add(
                config.COL_WEIGHTED_EFFICIENCY
            )
        # Increment the refresh counter so all checkbox widgets get new keys on the next
        # render. Without this, Streamlit reuses stale widget state (False) for the
        # Weighted Efficiency checkbox, which causes the column selector to immediately
        # discard the column we just added.
        st.session_state[SessionKeys.COLUMN_SELECTOR_REFRESH] = (
            st.session_state.get(SessionKeys.COLUMN_SELECTOR_REFRESH, 0) + 1
        )
        st.rerun()

    # Load current values from session state
    user_weights = st.session_state[SessionKeys.USER_WEIGHTS].copy()
    user_context = st.session_state[SessionKeys.USER_CONTEXT].copy()
    user_boosts = st.session_state[SessionKeys.USER_BOOSTS].copy()

    # ================== Main Content Area ==================
    st.markdown(load_tab_css(), unsafe_allow_html=True)

    # Initialize active tab in session state
    if SessionKeys.ACTIVE_MAIN_TAB not in st.session_state:
        st.session_state[SessionKeys.ACTIVE_MAIN_TAB] = 0

    # Tab selector with session state persistence
    tab_names = [
        translations.get_text("building_analysis", lang_code),
        translations.get_text("building_details", lang_code),
        translations.get_text("city_analysis", lang_code),
        translations.get_text("visualizations", lang_code),
    ]

    selected_tab = st.radio(
        label="Navigation",
        options=range(len(tab_names)),
        format_func=lambda x: tab_names[x],
        index=st.session_state[SessionKeys.ACTIVE_MAIN_TAB],
        key="main_tab_selector",
        horizontal=True,
        label_visibility="collapsed",
    )

    # Update session state when tab changes
    if selected_tab != st.session_state[SessionKeys.ACTIVE_MAIN_TAB]:
        st.session_state[SessionKeys.ACTIVE_MAIN_TAB] = selected_tab
        st.rerun()

    # --- Building Details Tab ---
    if st.session_state[SessionKeys.ACTIVE_MAIN_TAB] == 1:
        render_building_details(
            df_original=df_original,
            selected_translated_era=selected_translated_era,
            lang_code=lang_code,
            image_manager=cached_image_manager,
            show_per_square=show_per_square,
            combine_army_stats=combine_army_stats,
        )

    # Prepare filtered data for Analysis and Visualizations tabs (shared data)
    df_viz_filtered = df_filtered_by_advanced[
        df_filtered_by_advanced[config.COL_TRANSLATED_ERA] == selected_translated_era
    ].copy()
    if selected_events:
        df_viz_filtered = df_viz_filtered[
            df_viz_filtered[config.COL_EVENT].isin(selected_events)
        ]
    if name_filter:
        df_viz_filtered = df_viz_filtered[
            df_viz_filtered[config.COL_NAME].isin(name_filter)
        ]

    # Apply army stats combination if enabled
    if combine_army_stats:
        df_viz_filtered = combine_army_with_ge_gbg(df_viz_filtered)

    # Apply zero-production filter if enabled
    buildings_filtered_by_zero_production = 0
    if hide_zero_production:
        basic_info_columns = config.COLUMN_GROUPS["basic_info"]["columns"]
        production_columns = [
            col
            for col in selected_columns
            if col not in basic_info_columns
            and col in df_viz_filtered.columns
            and pd.api.types.is_numeric_dtype(df_viz_filtered[col])
        ]

        if production_columns:
            n_before = len(df_viz_filtered)
            mask = (df_viz_filtered[production_columns] != 0).any(axis=1)
            df_viz_filtered = df_viz_filtered[mask]
            buildings_filtered_by_zero_production = n_before - len(df_viz_filtered)

    # Initialize efficiency columns if they don't exist
    df_viz_filtered[config.COL_WEIGHTED_EFFICIENCY] = 0.0
    df_viz_filtered[config.COL_TOTAL_SCORE] = 0.0

    # --- Building Analysis Tab ---
    if st.session_state[SessionKeys.ACTIVE_MAIN_TAB] == 0:
        render_building_analysis(
            df_viz_filtered=df_viz_filtered,
            df_original=df_original,
            user_weights=user_weights,
            user_context=user_context,
            user_boosts=user_boosts,
            selected_columns=selected_columns,
            lang_code=lang_code,
            image_manager=cached_image_manager,
            use_icons=use_icons,
            show_labels=show_labels,
            enable_heatmap=enable_heatmap,
            show_per_square=show_per_square,
            hide_zero_production=hide_zero_production,
            buildings_filtered_by_zero_production=buildings_filtered_by_zero_production,
            page_size=page_size,
            selected_translated_era=selected_translated_era,
        )

    # --- City Analysis Tab ---
    if st.session_state[SessionKeys.ACTIVE_MAIN_TAB] == 2:
        render_city_analysis_tab(
            df_original=df_original,
            user_weights=user_weights,
            user_context=user_context,
            user_boosts=user_boosts,
            selected_columns=selected_columns,
            lang_code=lang_code,
            era_stats_df=(
                cached_calculate_era_stats(df_original)
                if st.session_state.get(SessionKeys.SCORING_MODE, "classic")
                == "normalised"
                else None
            ),
        )

    # --- Visualizations Tab ---
    if st.session_state[SessionKeys.ACTIVE_MAIN_TAB] == 3:
        df_viz_display = df_viz_filtered.copy()
        if (
            show_per_square
            and config.COL_SIZE in df_viz_display.columns
            and not df_viz_display.empty
        ):
            divisor_col = (
                df_viz_display[config.COL_SIZE].replace([0, pd.NA], 1).astype(float)
            )
            df_viz_display = calculations.apply_per_square(df_viz_display, divisor_col)
        render_data_visualizations(df_viz_display, lang_code, show_per_square)
