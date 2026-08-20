import streamlit as st


# --- Session State Key Constants ---
# Centralised namespace to prevent typos and ease future refactoring.
class SessionKeys:
    LANGUAGE = "language"
    USER_WEIGHTS = "user_weights"
    USER_CONTEXT = "user_context"
    USER_BOOSTS = "user_boosts"
    ACTIVE_MAIN_TAB = "active_main_tab"
    ACTIVE_ANALYSIS_SUBTAB = "active_analysis_subtab"
    SELECTION_BUILDING = "selection_building"
    SELECTED_COLUMNS_SET = "selected_columns_set"
    COLUMN_SELECTOR_REFRESH = "column_selector_refresh"
    ADVANCED_FILTERS = "advanced_filters"
    FILTER_LOGIC = "filter_logic"
    ACTIVE_FILTERS_COUNT = "active_filters_count"
    IMPORTED_INVENTORY = "imported_inventory"
    IMPORTED_CITY = "imported_city"
    SESSION_ID = "session_id"
    EFFICIENCY_CACHE = "efficiency_cache"
    SCORING_MODE = "scoring_mode"  # "classic" or "normalised"
    SELECTED_EVENT_TOOLTIP_EVENT = "selected_event_tooltip_event"
    SELECTED_EVENT_TOOLTIP_ERA = "selected_event_tooltip_era"


def init_session_state() -> None:
    """Initialize all session state keys with defaults. Called once at app startup."""
    defaults = {
        SessionKeys.LANGUAGE: "English",
        SessionKeys.USER_WEIGHTS: {},
        SessionKeys.USER_CONTEXT: {},
        SessionKeys.USER_BOOSTS: {},
        SessionKeys.ACTIVE_MAIN_TAB: 0,
        SessionKeys.SCORING_MODE: "classic",
        SessionKeys.SELECTED_EVENT_TOOLTIP_EVENT: "",
        SessionKeys.SELECTED_EVENT_TOOLTIP_ERA: "",
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default
