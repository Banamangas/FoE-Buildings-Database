import logging
import os
from io import BytesIO
from datetime import datetime

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, AgGridTheme, DataReturnMode, JsCode 
import json

# --- Local Modules Imports ---
import config
import data_loader
import translations
import calculations
import ui_components
import column_selector
import advanced_filters
import data_visualizations
import building_images
# import qi_optimizer_test
import city_analysis

# Use logger from config
logger = config.logger



def main():
    # --- Page Config ---
    st.set_page_config(
        layout="wide",
        page_title="FoE Building Database",
        page_icon=config.APP_ICON 
    )

    # --- Language Selection with Session State ---
    # Initialize language in session state if not exists
    if 'language' not in st.session_state:
        st.session_state.language = 'English'
    
    # Language selector with session state
    selected_language = st.sidebar.selectbox(
        "Select Language / Choisir la langue",
        options=list(translations.LANGUAGES.keys()),
        index=list(translations.LANGUAGES.keys()).index(st.session_state.language),
        key="language_selector"
    )
    
    # Update session state if language changed
    if selected_language != st.session_state.language:
        st.session_state.language = selected_language
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
        df_original = data_loader.load_and_process_data()

        if df_original.empty:
            st.warning("No building data loaded. The API may be updating — please try again shortly.")
            st.stop()

        # Round float columns (can be done earlier in data_loader if preferred)
        # float_cols = df_original.select_dtypes(include=['float64']).columns
        # df_original[float_cols] = df_original[float_cols].round(2)

        # --- Initial Data Transformation (Translations) ---
        @st.cache_data
        def apply_translations(df: pd.DataFrame, language_code: str) -> pd.DataFrame:
            df_translated = df.copy()
            
            # Translate building names
            if 'name' in df_translated.columns:
                df_translated['name'] = df_translated['name'].map(
                    lambda name: translations.translate_building_name(name, language_code)
                )
            else:
                logger.error("'name' column missing after data load.")

            # Translate event keys
            if 'Event' in df_translated.columns:
                df_translated['Event'] = df_translated['Event'].map(
                    lambda key: translations.translate_event_key(key, language_code)
                )
            else:
                logger.error("'Event' column missing after data load.")

            # Add Translated Era column
            if 'Era' in df_translated.columns:
                df_translated['Translated Era'] = df_translated['Era'].map(
                    lambda key: translations.translate_era_key(key, language_code)
                )
            else:
                logger.error("'Era' column not found after data load. Cannot translate eras.")
                df_translated['Translated Era'] = "Error"

            # Translate yes/no values
            if 'Limited' in df_translated.columns:
                df_translated['Limited'] = df_translated['Limited'].map(
                    lambda key: translations.translate_yesno_key(key, language_code)
                )
            else:
                logger.error("'Limited' column not found after data load. Cannot translate Limited.")
                df_translated['Limited'] = "Error"
            
            if 'Ally room' in df_translated.columns:
                df_translated['Ally room'] = df_translated['Ally room'].map(
                    lambda key: translations.translate_yesno_key(key, language_code)
                )
            else:
                logger.error("'Ally room' column not found after data load. Cannot translate Ally room.")
                df_translated['Ally room'] = "Error"

            return df_translated
        
        # Apply cached translations
        df_original = apply_translations(df_original, lang_code)
        
        # Save translation file (only when needed)
        with open(os.path.join(config.TRANSLATIONS_PATH, "to_be_translated_building_names.json"), "w") as f:
            json.dump(translations.TO_BE_TRANSLATED_BUILDING_NAMES, f)

        # --- Pre-calculate Stats (Cached) ---
        # Apply cache decorator here as it depends on df_original
        @st.cache_data
        def cached_calculate_era_stats(df: pd.DataFrame) -> pd.DataFrame:
            return calculations.calculate_era_stats(df)
        
        # --- Cache Building Images Manager ---
        @st.cache_resource
        def get_cached_image_manager():
            return building_images.get_image_manager()
        
        # Use cached image manager
        cached_image_manager = get_cached_image_manager()

        # --- Function to combine army stats ---
        def combine_army_with_ge_gbg(df: pd.DataFrame) -> pd.DataFrame:
            """Combine base army stats with GE/GBG equivalents and remove base columns."""
            df_combined = df.copy()
            
            # Define the mapping of base stats to their GE/GBG equivalents
            army_mappings = {
                'Red Attack': ['Red GE Attack', 'Red GBG Attack'],
                'Red Defense': ['Red GE Defense', 'Red GBG Defense'],
                'Blue Attack': ['Blue GE Attack', 'Blue GBG Attack'],
                'Blue Defense': ['Blue GE Defense', 'Blue GBG Defense']
            }
            
            for base_stat, target_stats in army_mappings.items():
                if base_stat in df_combined.columns:
                    base_values = df_combined[base_stat].fillna(0)
                    
                    # Add base values to GE and GBG equivalents
                    for target_stat in target_stats:
                        if target_stat in df_combined.columns:
                            df_combined[target_stat] = df_combined[target_stat].fillna(0) + base_values
                    
                    # Remove the base column
                    df_combined = df_combined.drop(columns=[base_stat])
            
            return df_combined

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
        help=translations.get_text("advanced_mode_help", lang_code)
    )

    # --- Era Filter ---
    # Get unique raw era keys and sort them according to ERAS_DICT order
    unique_raw_eras = df_original['Era'].unique()
    # Create a list of eras in ERAS_DICT order that exist in our data
    ordered_raw_eras = [era_key for era_key in config.ERAS_DICT.keys() if era_key in unique_raw_eras]
    # Add any eras that exist in data but not in ERAS_DICT (fallback)
    missing_eras = [era for era in unique_raw_eras if era not in config.ERAS_DICT.keys()]
    ordered_raw_eras.extend(sorted(missing_eras))  # Sort missing ones alphabetically as fallback
    
    # Translate the ordered era keys to get the properly ordered translated names
    available_eras = [translations.translate_era_key(era_key, lang_code) for era_key in ordered_raw_eras]
    
    default_translated_era = translations.translate_era_key("SpaceAgeSpaceHub", lang_code)
    try:
        default_era_index = available_eras.index(default_translated_era)
    except ValueError:
        default_era_index = 0
        logger.warning(f"Default translated era '{default_translated_era}' not found. Defaulting to index 0.")

    selected_translated_era = st.sidebar.selectbox(
        label=translations.translate_column("era", lang_code),
        options=available_eras,
        index=default_era_index,
        key="era_filter"
    )

    # --- Event Filter ---
    available_events = sorted(df_original['Event'].unique())
    selected_events = st.sidebar.multiselect(
        label=translations.translate_column("Event", lang_code),
        options=available_events,
        placeholder=translations.get_text("choose_an_option", lang_code),
        key="event_filter"
    )

    # --- Dynamic Name Filter ---
    # Create a subset dataframe filtered by era and event for the name filter
    df_for_name_filter = df_original[df_original['Translated Era'] == selected_translated_era].copy()
    if selected_events:
        df_for_name_filter = df_for_name_filter[df_for_name_filter['Event'].isin(selected_events)]
    
    # Initialize dynamic filters for building names only
    with st.sidebar:
        available_name_filters = sorted(df_for_name_filter['name'].unique())
        name_filter = st.multiselect(
                label=translations.get_text("search_label", lang_code),
                options=available_name_filters,
                placeholder=translations.get_text("choose_an_option", lang_code),
                key="name_filter_fallback"
        )

    # --- UI Options ---
    if advanced_mode:
        # Full options in advanced mode
        use_icons = st.sidebar.checkbox(translations.get_text("display_icons", lang_code), value=True, key="display_icons_checkbox")
        show_labels = st.sidebar.checkbox(translations.get_text("show_labels", lang_code), value=False, key="show_labels_checkbox") if use_icons else False
        show_per_square = st.sidebar.checkbox("📐 " + translations.get_text("value_per_tile", lang_code), value=False, key="per_square_checkbox")
        enable_heatmap = st.sidebar.checkbox(translations.get_text("enable_heatmap", lang_code), value=True, key="heatmap_checkbox")
        hide_zero_production = st.sidebar.checkbox(
            translations.get_text("hide_zero_production", lang_code), 
            value=False, 
            key="hide_zero_production_checkbox",
            help=translations.get_text("hide_zero_production_help", lang_code)
        )
        
        combine_army_stats = st.sidebar.checkbox(
            "⚔️ " + translations.get_text("combine_army_stats", lang_code),
            value=False,
            key="combine_army_stats_checkbox",
            help=translations.get_text("combine_army_stats_help", lang_code)
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
            help=translations.get_text("value_per_tile_help", lang_code)
        )
        
        combine_army_stats = st.sidebar.checkbox(
            "⚔️ " + translations.get_text("combine_army_stats", lang_code),
            value=False,
            key="combine_army_stats_checkbox_easy",
            help=translations.get_text("combine_army_simple_help", lang_code)
        )

    # --- Advanced Filters ---
    if advanced_mode:
        with st.sidebar:
            # Apply army stats combination to the dataframe used for filters if enabled
            df_for_filters = combine_army_with_ge_gbg(df_original) if combine_army_stats else df_original
            df_filtered_by_advanced = advanced_filters.render_advanced_filters(df_for_filters, lang_code, selected_translated_era)
    else:
        # No advanced filters in easy mode
        df_filtered_by_advanced = df_original

    # --- Enhanced Column Selection ---
    with st.sidebar:
        # Apply army stats combination to the dataframe used for column selection if enabled
        df_for_columns = combine_army_with_ge_gbg(df_original) if combine_army_stats else df_original
        
        if advanced_mode:
            # Full column selector with all features in advanced mode
            selected_columns = column_selector.render_enhanced_column_selector(df_for_columns, lang_code)
        else:
            # Simplified column selector in easy mode (no search functionality)
            selected_columns = column_selector.render_enhanced_column_selector(df_for_columns, lang_code, show_search=False)

                    

    # --- Initialize Weights ---
    # Initialize weights dictionary before tabs and preserve in session state
    if 'user_weights' not in st.session_state:
        st.session_state.user_weights = {}
    if 'user_context' not in st.session_state:
        st.session_state.user_context = {}
    if 'user_boosts' not in st.session_state:
        st.session_state.user_boosts = {}
    
    # Load current values from session state
    user_weights = st.session_state.user_weights.copy()
    user_context = st.session_state.user_context.copy()
    user_boosts = st.session_state.user_boosts.copy()

    # ================== Main Content Area ==================
    # CSS for tab-like radio buttons with session state persistence
    st.markdown("""
    <style>
    /* Style for main tab selector (radio buttons styled as tabs) */
    div[data-testid="stHorizontalBlock"]:has(div[data-testid="stRadio"]) {
        background-color: transparent;
        margin-bottom: 1.5rem;
    }
    
    div[data-testid="stRadio"] div[role="radiogroup"] {
        gap: 0.25rem !important;
        background-color: transparent;
        border-bottom: 0.125rem solid rgba(250, 250, 250, 0.1);
        padding-bottom: 0;
        display: flex;
        flex-wrap: wrap;
    }
    
    div[data-testid="stRadio"] div[role="radiogroup"] label {
        background-color: black;
        border-bottom: 0.125rem solid rgba(250, 250, 250, 0.1);
        border-radius: 8px 8px 0 0;
        padding: 0.75rem 1.5rem;
        cursor: pointer;
        transition: all 0.2s ease;
        font-weight: 600;
        color: white;
        font-size: 1.1rem;
        position: relative;
        margin-bottom: -2px;
    }

    div[data-testid="stRadio"] div[role="radiogroup"] label p {
        font-size: 1.4rem;
        font-weight: 600;
    }
    
    div[data-testid="stRadio"] div[role="radiogroup"] label:hover {
        background-color: black;
    }

    div[data-testid="stRadio"] div[role="radiogroup"] label:hover p {
        color: rgb(184, 162, 20);
        font-weight: 600;   
    }
    
    div[data-testid="stRadio"] div[role="radiogroup"] label:has(input[type="radio"]:checked) {
        background-color: black;
        border-bottom: 3px solid rgb(184, 162, 20);
        font-weight: 600;
        color: black!important;
        box-shadow: 0 -2px 8px rgba(0,0,0,0.05);
    }

    div[data-testid="stRadio"] div[role="radiogroup"] label div[class*="st-bg"] {
        display:none;
    }

    div[data-testid="stRadio"] div[role="radiogroup"] label:has(input[type="radio"]:checked) p {
        color: rgb(184, 162, 20);
        font-weight: 600;
    }
    
    /* Hide the radio button circles */
    div[data-testid="stRadio"] input[type="radio"] {
        position: absolute;
        opacity: 0;
        display:none;
    }
    
    /* Ensure text is visible */
    div[data-testid="stRadio"] label div[data-testid="stMarkdownContainer"] p {
        margin: 0;
        padding: 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize active tab in session state
    if 'active_main_tab' not in st.session_state:
        st.session_state.active_main_tab = 0
    
    # Tab selector with session state persistence
    tab_names = [
        translations.get_text("building_details", lang_code),
        translations.get_text("building_analysis", lang_code),
        translations.get_text("city_analysis", lang_code),
        translations.get_text("visualizations", lang_code)
    ]
    
    selected_tab = st.radio(
        label="Navigation",
        options=range(len(tab_names)),
        format_func=lambda x: tab_names[x],
        index=st.session_state.active_main_tab,
        key="main_tab_selector",
        horizontal=True,
        label_visibility="collapsed"
    )
    
    # Update session state when tab changes
    if selected_tab != st.session_state.active_main_tab:
        st.session_state.active_main_tab = selected_tab
        st.rerun()
    
    # --- Building Details Tab (First Tab) ---
    if st.session_state.active_main_tab == 0:
        
        st.header(translations.get_text("building_stats", lang_code))
        
        # Filter buildings by selected era (same as Home tab)
        df_era_filtered = df_original[df_original['Translated Era'] == selected_translated_era].copy()

        # Create columns for layout
        col1, col2, col3 = st.columns([1,1,2])
        with col1:
            # Show currently selected era
            st.info(f"📍 {translations.translate_column('Era', lang_code)}: **{selected_translated_era}**", width=300)

            # Building selection dropdown (only buildings from selected era)
            if 'selection_building' not in st.session_state:
                st.session_state['selection_building'] = 0

            building_names = sorted(df_era_filtered['name'].unique())
            selected_building = st.selectbox(
                label=translations.get_text("select_building", lang_code),
                options=[""] + building_names,
                index=st.session_state['selection_building'],
                key="building_selector"
            )

            st.markdown("---")
        
        # Apply army stats combination if enabled
        if combine_army_stats:
            df_era_filtered = combine_army_with_ge_gbg(df_era_filtered)
        
        _building_match = df_era_filtered[df_era_filtered['name'] == selected_building] if selected_building else pd.DataFrame()
        if selected_building and selected_building != "" and not _building_match.empty:
            # Get the selected building data from the era-filtered dataframe
            building_data = _building_match.iloc[0].copy()
            
            # Apply per square calculation if enabled
            if show_per_square and 'Nbr of squares (Avg)' in building_data and building_data['Nbr of squares (Avg)'] > 0:
                building_size = building_data['Nbr of squares (Avg)']
                # Apply per square calculation to numeric columns
                for col in building_data.index:
                    if (col not in config.PER_SQUARE_EXCLUDED_COLUMNS and 
                        pd.api.types.is_numeric_dtype(type(building_data[col])) and 
                        not pd.isna(building_data[col])):
                        building_data[col] = round(building_data[col] / building_size, 8)
            
            # Display building name as header
            st.markdown(f"### {selected_building}")
            
            # Show per square mode info if active
            if show_per_square:
                st.info("📐 " + translations.get_text("per_square_mode_active", lang_code))
            
            # Function to check if an icon exists for a column
            def has_icon(col_name: str) -> bool:
                return col_name not in config.ICON_EXCLUDED_COLUMNS and ui_components.get_icon_base64(col_name) is not None
            
            # --- Complete Stats Table with Image ---
            st.subheader(f"📊 {translations.get_text('complete_stats_table', lang_code)}")
            
            # Prepare data for the stats table
            stats_data = []
            
            # Get all columns from column groups in order
            for group_key, group_info in config.COLUMN_GROUPS.items():
                for col in group_info["columns"]:
                    if col in building_data:
                        value = building_data[col]

                        # Skip zero values and empty strings, but keep all boolean values (including False)
                        is_boolean = isinstance(value, bool) or pd.api.types.is_bool_dtype(type(value))
                        if not is_boolean and (value == 0 or value == '' or pd.isna(value)):
                            continue
                        
                        # Get translated column name
                        translated_name = translations.translate_column(col, lang_code)
                        
                        # Format value
                        if col in config.PERCENTAGE_COLUMNS:
                            formatted_value = f"{value:.0f}%"
                        elif isinstance(value, float):
                            formatted_value = f"{value:.2f}" if value != int(value) else f"{int(value)}"
                        elif is_boolean:
                            formatted_value = translations.get_text("yes", lang_code) if value else translations.get_text("no", lang_code)
                        else:
                            formatted_value = str(value)
                        
                        # Check if column has an icon
                        icon_url = None
                        if col not in config.ICON_EXCLUDED_COLUMNS:
                            icon_base64 = ui_components.get_icon_base64(col)
                            if icon_base64:
                                icon_url = f"data:image/png;base64,{icon_base64}"
                        
                        stats_data.append({
                            "Icon": icon_url,
                            "Statistic": translated_name,
                            "Value": formatted_value
                        })
            
            # Create layout with stats table on left and image on right
            building_asset_id = building_data.get('asset_id')
            if building_asset_id and cached_image_manager.has_image(building_asset_id):
                # Layout with table on left and image on right
                table_col, img_col = st.columns([2, 4])
                
                with table_col:
                    if stats_data:
                        # Create DataFrame for the stats table
                        stats_df = pd.DataFrame(stats_data)
                        
                        # Display the stats table using Streamlit's dataframe with column config
                        st.dataframe(
                            stats_df,
                            column_config={
                                "Icon": st.column_config.ImageColumn(
                                    label="",
                                    width=None,
                                    pinned=True
                                ),
                                "Statistic": st.column_config.TextColumn(
                                    label=translations.get_text("stat_name", lang_code),
                                    width=None
                                ),
                                "Value": st.column_config.TextColumn(
                                    label=translations.get_text("value", lang_code),
                                    width=None
                                )
                            },
                            hide_index=True,
                            height=40*len(stats_data) if len(stats_data) > 10 else 400,
                            width=600
                        )
                    else:
                        st.info(translations.get_text("no_stats_available", lang_code))
                
                with img_col:
                    image_url = cached_image_manager.get_building_image_url(building_asset_id)
                    st.image(
                        image_url,
                        caption=selected_building,
                        width='content'
                    )
            else:
                # No image available, show table full width
                if stats_data:
                    # Create DataFrame for the stats table
                    stats_df = pd.DataFrame(stats_data)
                    
                    # Display the stats table using Streamlit's dataframe with column config
                    st.dataframe(
                        stats_df,
                        column_config={
                            "Icon": st.column_config.ImageColumn(
                                label="",
                                width=None,
                                pinned=True
                            ),
                            "Statistic": st.column_config.TextColumn(
                                label=translations.get_text("stat_name", lang_code),
                                width=None
                            ),
                            "Value": st.column_config.TextColumn(
                                label=translations.get_text("value", lang_code),
                                width=None
                            )
                        },
                        hide_index=True,
                        height=40*len(stats_data) if len(stats_data) > 10 else 400,
                        width=600
                    )
                else:
                    st.info(translations.get_text("no_stats_available", lang_code))
        else:
            st.info(translations.get_text("no_building_selected", lang_code))
    
    # Prepare filtered data for Analysis and Visualizations tabs (shared data)
    # Apply the same filtering as the previous Home tab for consistency
    df_viz_filtered = df_filtered_by_advanced[df_filtered_by_advanced['Translated Era'] == selected_translated_era].copy()
    if selected_events:
        df_viz_filtered = df_viz_filtered[df_viz_filtered['Event'].isin(selected_events)]
    if name_filter:
        df_viz_filtered = df_viz_filtered[df_viz_filtered['name'].isin(name_filter)]
    
    # Apply army stats combination if enabled
    if combine_army_stats:
        df_viz_filtered = combine_army_with_ge_gbg(df_viz_filtered)
    
    # Apply zero-production filter if enabled
    buildings_filtered_by_zero_production = 0
    if hide_zero_production:
        basic_info_columns = config.COLUMN_GROUPS["basic_info"]["columns"]
        production_columns = [
            col for col in selected_columns
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
    df_viz_filtered['Weighted Efficiency'] = 0.0 # Initialize
    df_viz_filtered['Total Score'] = 0.0 # Initialize
    
    # --- Building Analysis Tab (Second Tab) ---
    if st.session_state.active_main_tab == 1:
        
        # Initialize active subtab in session state
        if 'active_analysis_subtab' not in st.session_state:
            st.session_state.active_analysis_subtab = 0
        
        # Subtab selector with session state persistence
        subtab_names = [
            translations.get_text("building_table", lang_code),
            translations.get_text("weights", lang_code),
            translations.get_text("consumables_analysis", lang_code),
            translations.get_text("qi_boosts_analysis", lang_code)
            # translations.get_text("qi_optimizer", lang_code)
        ]
        
        selected_subtab = st.radio(
            label="Analysis Navigation",
            options=range(len(subtab_names)),
            format_func=lambda x: subtab_names[x],
            index=st.session_state.active_analysis_subtab,
            key="analysis_subtab_selector",
            horizontal=True,
            label_visibility="collapsed"
        )
        
        # Update session state when subtab changes
        if selected_subtab != st.session_state.active_analysis_subtab:
            st.session_state.active_analysis_subtab = selected_subtab
            st.rerun()

        # --- Weights Subtab (Process first for user_weights, user_context, user_boosts) ---
        if st.session_state.active_analysis_subtab == 1:
            # --- Weighting Inputs ---
            st.header(translations.get_text("efficiency_weights", lang_code))
            st.markdown(translations.get_text("efficiency_help_direct", lang_code))
            st.info(translations.get_text("reminder_city_context", lang_code))
            st.markdown("---")
            
            # Create two columns for better layout
            left_col, right_col = st.columns(2)
            
            # Split the column groups between the two columns
            column_groups_list = list(config.COLUMN_GROUPS.items())
            mid_point = len(column_groups_list) // 2
            
            for col, groups in [(left_col, column_groups_list[:mid_point]), (right_col, column_groups_list[mid_point:])]:
                with col:
                    for group_key, group_info in groups:
                        # Find weightable columns within this group that exist in the data
                        cols_in_group = group_info["columns"]
                        inputs_to_create = []
                        for col_name in cols_in_group:
                            # Check if the column exists in the loaded data
                            if col_name in df_original.columns and col_name in config.WEIGHTABLE_COLUMNS:
                                # Check if the column is numeric before allowing weighting
                                if pd.api.types.is_numeric_dtype(df_original[col_name]):
                                    inputs_to_create.append(col_name)

                        if inputs_to_create:  # Only show expander if there are inputs to create
                            with st.expander(translations.get_text(group_info["key"], lang_code), expanded=False):
                                for col_name in inputs_to_create:
                                    # Skip boost metrics as they're now integrated into base metrics
                                    if col_name in config.BOOST_TO_BASE_MAPPING:
                                        continue
                                        
                                    help_text = f"Points per {translations.translate_column(col_name, lang_code).lower()}"
                                    
                                    weight_value = st.number_input(
                                        label=f"1 {translations.translate_column(col_name, lang_code)} = ___ Points",
                                        help=help_text,
                                        value=user_weights.get(col_name, 0.0),
                                        min_value=0.0,
                                        step=0.1,
                                        format="%.1f",
                                        key=f"weight_{col_name}"
                                    )
                                    user_weights[col_name] = weight_value
                                    st.session_state.user_weights[col_name] = weight_value
            st.markdown("---")
            # --- User Context Section ---
            st.header(translations.get_text("user_context", lang_code))
            st.markdown(translations.get_text("user_context_help", lang_code))
            
            # Base Production Section
            st.subheader(translations.get_text("base_production_section", lang_code))
            
            # Create two columns for base production inputs
            ctx_left_col, ctx_right_col = st.columns(2)
            
            context_fields = list(config.USER_CONTEXT_FIELDS.items())
            mid_point = len(context_fields) // 2
            
            for col, fields in [(ctx_left_col, context_fields[:mid_point]), (ctx_right_col, context_fields[mid_point:])]:
                with col:
                    for field_key, field_config in fields:
                        context_value = st.number_input(
                            label=translations.get_text(field_config["label_key"], lang_code),
                            help=translations.get_text(field_config["help_key"], lang_code),
                            value=user_context.get(field_key, float(field_config["default"])),
                            min_value=0.0,
                            step=1.0 if field_key in ["fp_daily_production", "medal_production", "special_goods_production", "guild_goods_production"] else 100.0,
                            key=f"context_{field_key}"
                        )
                        user_context[field_key] = context_value
                        st.session_state.user_context[field_key] = context_value
            
            # Current Boosts Section
            st.subheader(translations.get_text("current_boosts_section", lang_code))
            
            # Create two columns for boost inputs
            boost_left_col, boost_right_col = st.columns(2)
            
            boost_fields = list(config.USER_BOOST_FIELDS.items())
            boost_mid_point = len(boost_fields) // 2
            
            for col, fields in [(boost_left_col, boost_fields[:boost_mid_point]), (boost_right_col, boost_fields[boost_mid_point:])]:
                with col:
                    for field_key, field_config in fields:
                        boost_value = st.number_input(
                            label=translations.get_text(field_config["label_key"], lang_code),
                            help=translations.get_text(field_config["help_key"], lang_code),
                            value=user_boosts.get(field_key, float(field_config["default"])),
                            min_value=0.0,
                            max_value=1000.0,
                            step=1.0,
                            format="%.1f",
                            key=f"boost_{field_key}"
                        )
                        user_boosts[field_key] = boost_value
                        st.session_state.user_boosts[field_key] = boost_value

        # Calculate efficiency if weights are set (after processing weights subtab)
        weights_active = any(w > 0 for w in user_weights.values()) if user_weights else False
        logger.debug(f"Main Analysis: Weights active: {weights_active}, User weights: {user_weights}")
        
        if weights_active and not df_viz_filtered.empty:
            logger.info("Applying efficiency calculations to main analysis table")
            df_viz_filtered = calculations.calculate_direct_weighted_efficiency(
                df=df_viz_filtered,
                user_weights=user_weights,
                user_context=user_context,
                user_boosts=user_boosts
            )
            logger.info("Main Analysis: Efficiency calculations completed successfully")
        else:
            logger.info("Main Analysis: No active weights or empty dataframe - efficiency columns remain at 0.0")

        # --- Table Subtab ---
        if st.session_state.active_analysis_subtab == 0:
            try:
                # --- Prepare Display Columns ---
                # Filter columns that exist in the filtered dataframe
                existing_columns_for_display = []
                
                # Process selected columns in the order they were selected
                for col in selected_columns:
                    if col in df_viz_filtered.columns and col not in existing_columns_for_display:
                        existing_columns_for_display.append(col)
                
                # Ensure uniqueness while preserving order
                existing_columns_for_display = list(dict.fromkeys(existing_columns_for_display))
                logger.info(f"Columns selected for display: {existing_columns_for_display}")

                # Create the final DataFrame for AgGrid
                if not existing_columns_for_display:
                    st.warning("No columns selected or available for display.")
                    st.stop()
                    
                df_display = df_viz_filtered[existing_columns_for_display].copy()
                df_display=df_display.sort_values(by='name',ascending=True)


                # --- Apply "Per Square" Calculation ---
                if show_per_square and 'Nbr of squares (Avg)' in df_viz_filtered.columns:
                    numeric_cols = [
                        col for col in df_display.columns
                        if col not in config.PER_SQUARE_EXCLUDED_COLUMNS
                        and pd.api.types.is_numeric_dtype(df_display[col])
                    ]
                    # Use divisor from the filtered df *before* potential division
                    divisor_col = df_viz_filtered.loc[df_display.index, 'Nbr of squares (Avg)']
                    divisor_col = divisor_col.replace([0, pd.NA], 1).astype(float) # Avoid division by zero/NA

                    for col in numeric_cols:
                        if col in df_display:
                            # Ensure column is numeric before dividing
                            if pd.api.types.is_numeric_dtype(df_display[col]):
                                df_display[col] = (df_display[col] / divisor_col).round(8)
                            else:
                                logger.warning(f"Column '{col}' intended for per-square calc is not numeric.")

                # --- Configure and Display AgGrid ---
                eff_min = df_display['Weighted Efficiency'].min() if 'Weighted Efficiency' in df_display and not df_display.empty else 0
                eff_max = df_display['Weighted Efficiency'].max() if 'Weighted Efficiency' in df_display and not df_display.empty else 0
                if pd.isna(eff_min): eff_min = 0
                if pd.isna(eff_max): eff_max = 0

                # --- Prepare Export DataFrame with Translated Column Names ---
                df_export = df_display.copy()
                # Create mapping of original to translated column names
                column_translation_map = {
                    col: translations.translate_column(col, lang_code) 
                    for col in df_export.columns
                }
                # Rename columns to translated names
                df_export.rename(columns=column_translation_map, inplace=True)
                logger.info(f"Column translations for export: {column_translation_map}")

                # --- Export Buttons ---
                col1, col2 = st.columns([1, 10])
                with col1:
                    # CSV Export with proper UTF-8 encoding and BOM
                    buffer_csv = BytesIO()
                    # Add UTF-8 BOM manually
                    buffer_csv.write('\ufeff'.encode('utf-8'))
                    # Write CSV data with translated column names
                    csv_string = df_export.to_csv(index=False, sep=";")
                    buffer_csv.write(csv_string.encode('utf-8'))
                    buffer_csv.seek(0)
                    csv_data = buffer_csv.getvalue()
                    
                    st.download_button(
                        label=translations.get_text("export_csv", lang_code),
                        data=csv_data,
                        file_name=f"foe_buildings_{selected_translated_era}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv",
                        mime="text/csv; charset=utf-8",
                        key="export_csv"
                    )
                with col2:
                    # JSON Export with translated column names and proper UTF-8 encoding
                    json_string = df_export.to_json(orient="records", date_format="iso", force_ascii=False)
                    json_data = json_string.encode('utf-8')
                    
                    st.download_button(
                        label=translations.get_text("export_json", lang_code),
                        data=json_data,
                        file_name=f"foe_buildings_{selected_translated_era}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json",
                        mime="application/json; charset=utf-8",
                        key="export_json"
                    )

                grid_options = ui_components.build_grid_options(
                    df_display=df_display,
                    lang_code=lang_code,
                    use_icons=use_icons,
                    show_labels=show_labels,
                    enable_heatmap=enable_heatmap,
                    eff_min=eff_min,
                    eff_max=eff_max
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
                logger.debug(f"Using AgGrid key: {grid_key}")

                grid_return = AgGrid(
                    df_display,
                    gridOptions=grid_options,
                    custom_css=ui_components.CUSTOM_CSS,
                    allow_unsafe_jscode=True,
                    theme=AgGridTheme.STREAMLIT,
                    height=800,
                    width='100%',
                    key=grid_key,
                    data_return_mode=DataReturnMode.AS_INPUT
                )

                builingRows=grid_return.selected_rows                               # Get selected row
                if builingRows is not None:                                         # if a row is selected
                    buildingIndex=int(builingRows.index[0])+1                       # Get selected row's Index
                    if buildingIndex!=st.session_state['selection_building']:       # if changed
                        st.session_state['selection_building']  =  buildingIndex    # set to new value
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
                    st.markdown(f"- [Streamlit](https://streamlit.io/) - {translations.get_text('web_framework', lang_code)}")
                    st.markdown(f"- [AG-Grid](https://www.ag-grid.com/) - {translations.get_text('data_grid', lang_code)}")
                    st.markdown(f"- [Pandas](https://pandas.pydata.org/) - {translations.get_text('data_analysis', lang_code)}")
                
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
                    unsafe_allow_html=True
                )

            except Exception as e:
                st.error(f"An error occurred during app execution: {str(e)}")
                logger.error(f"Error during main app execution: {e}", exc_info=True)
        
        # --- Consumables Analysis Subtab ---
        if st.session_state.active_analysis_subtab == 2:
            st.header("🛠️ " + translations.get_text("consumables_analysis", lang_code))
            st.markdown(translations.get_text("consumables_analysis_help", lang_code))
            
            # Get consumable columns from config
            consumable_columns = config.COLUMN_GROUPS["consumables"]["columns"]
            
            # Filter to only include consumables that exist in the data
            available_consumables = [col for col in consumable_columns if col in df_viz_filtered.columns]
            
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
                        key="consumables_selector"
                    )
                
                with col2:
                    # Display format toggle
                    show_frequency_format = st.toggle(
                        translations.get_text("show_frequency_format", lang_code),
                        value=True,
                        key="consumables_frequency_toggle",
                        help=translations.get_text("frequency_format_help", lang_code)
                    )
                
                if selected_consumables:
                    # Create a copy of the data without per-square calculation
                    df_consumables = df_viz_filtered.copy()
                    
                    # Filter buildings that produce at least one of the selected consumables
                    consumables_mask = (df_consumables[selected_consumables] > 0).any(axis=1)
                    df_consumables_filtered = df_consumables[consumables_mask].copy()
                    
                    if df_consumables_filtered.empty:
                        st.info(translations.get_text("no_buildings_produce_consumables", lang_code))
                    else:
                        # Prepare the display data
                        display_data = []
                        
                        for _, building in df_consumables_filtered.iterrows():
                            building_id = building.get('asset_id')
                            building_name = building.get('name', 'Unknown')
                            building_size = building.get('size', 'Unknown')
                            needs_road = building.get('Road', False)
                            road_text = translations.get_text("yes", lang_code) if needs_road else translations.get_text("no", lang_code)
                            
                            # Get building image URL
                            image_url = None
                            if building_id and cached_image_manager.has_image(building_id):
                                image_url = cached_image_manager.get_building_image_url(building_id)
                            
                            # Create base row data
                            row_data = {
                                "Building Image": image_url,
                                "Building Name": building_name,
                                "Size": building_size,
                                "Road": road_text
                            }
                            
                            # Add consumable production data (store as numeric for proper sorting)
                            for consumable in selected_consumables:
                                production_value = building.get(consumable, 0)
                                if production_value > 0:
                                    translated_consumable = translations.translate_column(consumable, lang_code)
                                    # Store the raw numeric value for sorting
                                    row_data[translated_consumable] = production_value
                                else:
                                    # Don't include buildings that don't produce this consumable
                                    continue
                            
                            # Only add row if it produces at least one selected consumable
                            has_production = any(building.get(cons, 0) > 0 for cons in selected_consumables)
                            if has_production:
                                display_data.append(row_data)
                        
                        if display_data:
                            # Create DataFrame for display (values are already numeric for proper sorting)
                            consumables_df = pd.DataFrame(display_data)
                            
                            # Sort columns list
                            sort_columns = [translations.translate_column(consumable, lang_code) 
                                          for consumable in selected_consumables 
                                          if translations.translate_column(consumable, lang_code) in consumables_df.columns]
                            
                            # Initial sort by production values (descending - highest production first)
                            if sort_columns:
                                consumables_df = consumables_df.sort_values(
                                    by=sort_columns, 
                                    ascending=False
                                ).reset_index(drop=True)
                            
                            # Transform values if frequency format is selected
                            if show_frequency_format:
                                for consumable in selected_consumables:
                                    translated_name = translations.translate_column(consumable, lang_code)
                                    if translated_name in consumables_df.columns:
                                        # Transform to days per unit (1 / production_per_day)
                                        consumables_df[translated_name] = 1 / consumables_df[translated_name]
                            
                            # Configure column display
                            column_config = {
                                "Building Image": st.column_config.ImageColumn(
                                    label="🏢",
                                    width="small"
                                ),
                                "Building Name": st.column_config.TextColumn(
                                    label=translations.get_text("building_name", lang_code),
                                    width="medium"
                                ),
                                "Size": st.column_config.TextColumn(
                                    label=translations.get_text("size", lang_code),
                                    width="small"
                                ),
                                "Road": st.column_config.TextColumn(
                                    label=translations.get_text("road", lang_code),
                                    width="small"
                                )
                            }
                            
                            # Add consumable columns to config with numeric formatting
                            for consumable in selected_consumables:
                                translated_name = translations.translate_column(consumable, lang_code)
                                if translated_name in consumables_df.columns:
                                    # Use NumberColumn for proper numeric sorting
                                    if show_frequency_format:
                                        # Frequency format - showing days per unit
                                        suffix = " days" if lang_code == "en" else " jours"
                                        help_text = "Days per unit (lower is better)" if lang_code == "en" else "Jours par unité (moins c'est mieux)"
                                        
                                        column_config[translated_name] = st.column_config.NumberColumn(
                                            label=translated_name,
                                            width="medium",
                                            format="%.2f" + suffix,
                                            help=help_text
                                        )
                                    else:
                                        # Show per day format
                                        suffix = "/day" if lang_code == "en" else "/jour"
                                        column_config[translated_name] = st.column_config.NumberColumn(
                                            label=translated_name,
                                            width="medium",
                                            format="%.2f" + suffix
                                        )
                            
                            # Display summary
                            st.subheader(f"📋 {translations.get_text('results_summary', lang_code)}")
                            st.write(f"**{len(consumables_df)} {translations.get_text('buildings_found', lang_code)}**")
                            
                            # Display the table
                            st.dataframe(
                                consumables_df,
                                column_config=column_config,
                                hide_index=True,
                                width='content',
                                height=min(600, max(200, len(consumables_df) * 40 + 100))
                            )
                            
                            # Export functionality
                            if len(consumables_df) > 0:
                                st.markdown("---")
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    # CSV Export
                                    csv_string = consumables_df.to_csv(index=False, sep=";")
                                    st.download_button(
                                        label=translations.get_text("export_csv", lang_code),
                                        data=csv_string.encode('utf-8'),
                                        file_name=f"consumables_analysis_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv",
                                        mime="text/csv",
                                        key="export_consumables_csv"
                                    )
                                
                                with col2:
                                    # JSON Export
                                    json_string = consumables_df.to_json(orient="records", force_ascii=False)
                                    st.download_button(
                                        label=translations.get_text("export_json", lang_code),
                                        data=json_string.encode('utf-8'),
                                        file_name=f"consumables_analysis_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json",
                                        mime="application/json",
                                        key="export_consumables_json"
                                    )
                        else:
                            st.info(translations.get_text("no_buildings_produce_selected_consumables", lang_code))
                else:
                    st.info(translations.get_text("select_consumables_to_analyze", lang_code))
        
        # --- QI Boosts Analysis Subtab ---
        if st.session_state.active_analysis_subtab == 3:
            st.header("🌌 " + translations.get_text("qi_boosts_analysis", lang_code))
            st.markdown(translations.get_text("qi_boosts_analysis_help", lang_code))
            
            # Get QI boost columns from config
            qi_boost_columns = config.COLUMN_GROUPS["qi"]["columns"]
            
            # Filter to only include QI boosts that exist in the data
            available_qi_boosts = [col for col in qi_boost_columns if col in df_viz_filtered.columns]
            
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
                        key="qi_boosts_selector"
                    )
                
                with col2:
                    # Display format toggle for percentage vs actual values
                    show_actual_values = st.toggle(
                        translations.get_text("show_actual_values_format", lang_code),
                        value=True,
                        key="qi_actual_values_toggle",
                        help=translations.get_text("actual_values_format_help", lang_code)
                    )
                
                if selected_qi_boosts:
                    # Create a copy of the data without per-square calculation
                    df_qi_boosts = df_viz_filtered.copy()
                    
                    # Filter buildings that provide at least one of the selected QI boosts
                    qi_boosts_mask = (df_qi_boosts[selected_qi_boosts] > 0).any(axis=1)
                    df_qi_boosts_filtered = df_qi_boosts[qi_boosts_mask].copy()
                    
                    if df_qi_boosts_filtered.empty:
                        st.info(translations.get_text("no_buildings_provide_qi_boosts", lang_code))
                    else:
                        # Prepare the display data
                        display_data = []
                        
                        for _, building in df_qi_boosts_filtered.iterrows():
                            building_id = building.get('asset_id')
                            building_name = building.get('name', 'Unknown')
                            building_size = building.get('size', 'Unknown')
                            needs_road = building.get('Road', False)
                            road_text = translations.get_text("yes", lang_code) if needs_road else translations.get_text("no", lang_code)
                            
                            # Get building image URL
                            image_url = None
                            if building_id and cached_image_manager.has_image(building_id):
                                image_url = cached_image_manager.get_building_image_url(building_id)
                            
                            # Create base row data
                            row_data = {
                                "Building Image": image_url,
                                "Building Name": building_name,
                                "Size": building_size,
                                "Road": road_text
                            }
                            
                            # Add QI boost data (store as numeric values for proper sorting)
                            for qi_boost in selected_qi_boosts:
                                boost_value = building.get(qi_boost, 0)
                                if boost_value > 0:
                                    # Store numeric value - formatting will be handled by column_config
                                    translated_qi_boost = translations.translate_column(qi_boost, lang_code)
                                    row_data[translated_qi_boost] = boost_value
                                else:
                                    # Don't include buildings that don't provide this QI boost
                                    continue
                            
                            # Only add row if it provides at least one selected QI boost
                            has_qi_boost = any(building.get(boost, 0) > 0 for boost in selected_qi_boosts)
                            if has_qi_boost:
                                display_data.append(row_data)
                        
                        if display_data:
                            # Create DataFrame for display (values are already numeric for proper sorting)
                            qi_boosts_df = pd.DataFrame(display_data)
                            
                            # Sort by QI boost values numerically (descending - highest first)
                            sort_columns = [translations.translate_column(qi_boost, lang_code) 
                                          for qi_boost in selected_qi_boosts 
                                          if translations.translate_column(qi_boost, lang_code) in qi_boosts_df.columns]
                            
                            if sort_columns:
                                qi_boosts_df = qi_boosts_df.sort_values(
                                    by=sort_columns, 
                                    ascending=False
                                ).reset_index(drop=True)
                            
                            # Configure column display
                            column_config = {
                                "Building Image": st.column_config.ImageColumn(
                                    label="🏢",
                                    width="small"
                                ),
                                "Building Name": st.column_config.TextColumn(
                                    label=translations.get_text("building_name", lang_code),
                                    width="medium"
                                ),
                                "Size": st.column_config.TextColumn(
                                    label=translations.get_text("size", lang_code),
                                    width="small"
                                ),
                                "Road": st.column_config.TextColumn(
                                    label=translations.get_text("road", lang_code),
                                    width="small"
                                )
                            }
                            
                            # Add QI boost columns to config with numeric formatting
                            for qi_boost in selected_qi_boosts:
                                translated_name = translations.translate_column(qi_boost, lang_code)
                                if translated_name in qi_boosts_df.columns:
                                    # Use NumberColumn for proper numeric sorting
                                    if qi_boost in config.PERCENTAGE_COLUMNS:
                                        if show_actual_values:
                                            format_string = "%.0f%%"
                                        else:
                                            format_string = "+%.0f%%"
                                    else:
                                        format_string = "%.0f"
                                    
                                    column_config[translated_name] = st.column_config.NumberColumn(
                                        label=translated_name,
                                        width="medium",
                                        format=format_string
                                    )
                            
                            # Display summary
                            st.subheader(f"📋 {translations.get_text('results_summary', lang_code)}")
                            st.write(f"**{len(qi_boosts_df)} {translations.get_text('buildings_found', lang_code)}**")
                            
                            # Display the table
                            st.dataframe(
                                qi_boosts_df,
                                column_config=column_config,
                                hide_index=True,
                                width='content',
                                height=min(600, max(200, len(qi_boosts_df) * 40 + 100))
                            )
                            
                            # Export functionality
                            if len(qi_boosts_df) > 0:
                                st.markdown("---")
                                st.subheader("📤 " + translations.get_text("export_results", lang_code))
                                
                                # Prepare export data
                                export_data = []
                                for _, combo in qi_boosts_df.iterrows():
                                    row = {
                                        translations.get_text("building_name", lang_code): combo.get("Building Name", ""),
                                        translations.get_text("size", lang_code): combo.get("Size", ""),
                                        translations.get_text("road", lang_code): combo.get("Road", "")
                                    }
                                    
                                    # Add QI boost columns
                                    for qi_boost in selected_qi_boosts:
                                        translated_qi_boost = translations.translate_column(qi_boost, lang_code)
                                        if translated_qi_boost in combo:
                                            row[translated_qi_boost] = combo[translated_qi_boost]
                                    
                                    export_data.append(row)
                                
                                export_df = pd.DataFrame(export_data)
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    csv_string = export_df.to_csv(index=False, sep=";")
                                    st.download_button(
                                        label=translations.get_text("export_csv", lang_code),
                                        data=csv_string.encode('utf-8'),
                                        file_name=f"qi_boosts_analysis_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv",
                                        mime="text/csv",
                                        key="export_qi_boosts_csv"
                                    )
                                
                                with col2:
                                    json_string = export_df.to_json(orient="records", force_ascii=False)
                                    st.download_button(
                                        label=translations.get_text("export_json", lang_code),
                                        data=json_string.encode('utf-8'),
                                        file_name=f"qi_boosts_analysis_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json",
                                        mime="application/json",
                                        key="export_qi_boosts_json"
                                    )
                        else:
                            st.info(translations.get_text("no_buildings_provide_selected_qi_boosts", lang_code))
                else:
                    st.info(translations.get_text("select_qi_boosts_to_analyze", lang_code))
        
        # --- QI Optimizer Subtab ---
        # with analysis_subtabs[4]:
            # qi_optimizer_test.render_qi_optimizer(df_viz_filtered, lang_code, cached_image_manager)
    
    # --- City Analysis Tab ---
    if st.session_state.active_main_tab == 2:
        
        # Render the City Analysis interface
        city_analysis.render_city_analysis_tab(
            df_original=df_original,
            user_weights=user_weights,
            user_context=user_context,
            user_boosts=user_boosts,
            selected_columns=selected_columns,
            lang_code=lang_code
        )
    
    # --- Visualizations Tab ---
    if st.session_state.active_main_tab == 3:
        
        # Use the same filtered data from the analysis tab
        # Apply "Per Square" Calculation to visualization data if enabled
        df_viz_display = df_viz_filtered.copy()
        if show_per_square and 'Nbr of squares (Avg)' in df_viz_display.columns and not df_viz_display.empty:
            numeric_cols = [
                col for col in df_viz_display.columns
                if col not in config.PER_SQUARE_EXCLUDED_COLUMNS
                and pd.api.types.is_numeric_dtype(df_viz_display[col])
            ]
            # Use divisor from the filtered df
            divisor_col = df_viz_display['Nbr of squares (Avg)']
            divisor_col = divisor_col.replace([0, pd.NA], 1).astype(float) # Avoid division by zero/NA

            for col in numeric_cols:
                if col in df_viz_display:
                    # Ensure column is numeric before dividing
                    if pd.api.types.is_numeric_dtype(df_viz_display[col]):
                        df_viz_display[col] = (df_viz_display[col] / divisor_col).round(8)
        
        # Render the visualizations
        data_visualizations.render_data_visualizations(df_viz_display, lang_code, show_per_square)
    


# --- Main Execution Guard ---
if __name__ == "__main__":
    main()