import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Set
import config
import translations
import ui_components


class ColumnSelector:
    """Enhanced column selection UI with search, presets, and better organization."""
    
    
    def __init__(self, df_original: pd.DataFrame, lang_code: str):
        self.df_original = df_original
        self.lang_code = lang_code
        self.available_columns = self._get_available_columns()
        
    def _get_available_columns(self) -> Dict[str, List[str]]:
        """Get all available columns organized by groups."""
        available_columns = {}
        virtual_columns = [config.COL_WEIGHTED_EFFICIENCY, config.COL_TOTAL_SCORE]
        
        for group_key, group_info in config.COLUMN_GROUPS.items():
            group_columns = []
            for col in group_info["columns"]:
                if col in self.df_original.columns or col in virtual_columns:
                    group_columns.append(col)
            
            if group_columns:
                available_columns[group_key] = group_columns
                
        return available_columns
    
    def _has_icon(self, col_name: str) -> bool:
        """Check if a column has an associated icon."""
        return col_name not in config.ICON_EXCLUDED_COLUMNS and ui_components.get_icon_base64(col_name) is not None
    
    def _create_column_item(self, col: str, selected_columns: Set[str], key_suffix: str = "") -> bool:
        """Create a column selection item with icon and translated name."""
        translated_name = translations.translate_column(col, self.lang_code)
        # Always read from session state to ensure checkboxes reflect current state
        is_selected = col in st.session_state.selected_columns_set
        # Include refresh counter in key to force widget recreation when buttons are clicked
        refresh_counter = st.session_state.get('column_selector_refresh', 0)
        
        if self._has_icon(col):
            icon_base64 = ui_components.get_icon_base64(col)
            # Create visual column item with icon
            col_container = st.container()
            with col_container:
                checkbox_col, icon_col = st.columns([0.8, 0.2])
                
                with checkbox_col:
                    new_selection = st.checkbox(
                        label=translated_name,
                        value=is_selected,
                        key=f"enhanced_col_select_{col}{key_suffix}_r{refresh_counter}",
                        help=translated_name
                    )
                
                with icon_col:
                    if icon_base64:
                        st.markdown(f"""
                        <div style="display: flex; justify-content: center; align-items: center; height: 24px;">
                            <img src="data:image/png;base64,{icon_base64}" 
                                 style="width: 20px; height: 20px;" 
                                 title="{translated_name}">
                        </div>
                        """, unsafe_allow_html=True)
        else:
            # Regular checkbox for columns without icons
            new_selection = st.checkbox(
                label=translated_name,
                value=is_selected,
                key=f"enhanced_col_select_{col}{key_suffix}_r{refresh_counter}",
                help=translated_name
            )
        
        return new_selection
    
    def _apply_preset(self, preset_key: str, selected_columns: Set[str]) -> Set[str]:
        """Apply a column preset."""
        if preset_key in config.COLUMN_PRESETS:
            preset_columns = config.COLUMN_PRESETS[preset_key]["columns"]
            # Only include columns that are actually available
            available_preset_columns = [
                col for col in preset_columns 
                if any(col in group_cols for group_cols in self.available_columns.values())
            ]
            return set(available_preset_columns + [config.COL_NAME])  # Always include name
        return selected_columns
    
    def _filter_columns_by_search(self, search_term: str) -> Dict[str, List[str]]:
        """Filter columns based on search term."""
        if not search_term:
            return self.available_columns
        
        search_term = search_term.lower()
        filtered_columns = {}
        
        for group_key, columns in self.available_columns.items():
            matching_columns = []
            for col in columns:
                translated_name = translations.translate_column(col, self.lang_code).lower()
                if search_term in translated_name or search_term in col.lower():
                    matching_columns.append(col)
            
            if matching_columns:
                filtered_columns[group_key] = matching_columns
        
        return filtered_columns
    
    def _sort_columns_by_group_order(self, selected_columns: Set[str]) -> List[str]:
        """Sort selected columns according to the order defined in COLUMN_GROUPS."""
        # Create a mapping of column names to their priority order
        column_order_map = {}
        priority = 0
        
        # Always put 'name' first
        column_order_map[config.COL_NAME] = priority
        priority += 1
        
        # Add columns in the order they appear in COLUMN_GROUPS
        for group_key, group_info in config.COLUMN_GROUPS.items():
            for col in group_info["columns"]:
                if col not in column_order_map:
                    column_order_map[col] = priority
                    priority += 1
        
        # Sort selected columns based on their priority order
        selected_list = list(selected_columns)
        selected_list.sort(key=lambda col: column_order_map.get(col, 9999))  # Unknown columns go to end
        
        return selected_list
    
    def render_enhanced_column_selector(self, show_search: bool = True) -> List[str]:
        """Render the enhanced column selection UI."""
        st.markdown("---")
        st.header(translations.get_text("column_selection", lang_code=self.lang_code))
        
        # Initialize session state for selected columns if not exists
        if 'selected_columns_set' not in st.session_state:
            # Default selection
            default_columns = config.COLUMN_PRESETS["basic_analysis"]["columns"]
            st.session_state.selected_columns_set = set(default_columns + [config.COL_NAME])
        
        # Initialize a counter to force widget refresh when buttons are clicked
        if 'column_selector_refresh' not in st.session_state:
            st.session_state.column_selector_refresh = 0
        
        selected_columns = st.session_state.selected_columns_set
        
        # Preset Selection
        with st.expander("📋 " + translations.get_text("column_presets", lang_code=self.lang_code), expanded=True):
            preset_cols = st.columns(2)
            
            with preset_cols[0]:
                if st.button(translations.get_text("preset_basic_analysis", lang_code=self.lang_code), 
                            width='stretch', key="preset_basic"):
                    st.session_state.selected_columns_set = self._apply_preset("basic_analysis", selected_columns)
                    st.session_state.column_selector_refresh += 1
                    st.rerun()
                
                if st.button(translations.get_text("preset_production_focus", lang_code=self.lang_code), 
                            width='stretch', key="preset_production"):
                    st.session_state.selected_columns_set = self._apply_preset("production_focus", selected_columns)
                    st.session_state.column_selector_refresh += 1
                    st.rerun()

                if st.button(translations.get_text("preset_military_focus", lang_code=self.lang_code), 
                            width='stretch', key="preset_military"):
                    st.session_state.selected_columns_set = self._apply_preset("military_focus", selected_columns)
                    st.session_state.column_selector_refresh += 1
                    st.rerun()
                
                if st.button(translations.get_text("preset_fsp_usage", lang_code=self.lang_code), 
                            width='stretch', key="preset_fsp"):
                    st.session_state.selected_columns_set = self._apply_preset("fsp_usage", selected_columns)
                    st.session_state.column_selector_refresh += 1
                    st.rerun()
            
            with preset_cols[1]:
                
                if st.button(translations.get_text("preset_gbg_focus", lang_code=self.lang_code), 
                            width='stretch', key="preset_gbg"):
                    st.session_state.selected_columns_set = self._apply_preset("gbg_focus", selected_columns)
                    st.session_state.column_selector_refresh += 1
                    st.rerun()

                if st.button(translations.get_text("preset_ge_focus", lang_code=self.lang_code), 
                            width='stretch', key="preset_ge"):
                    st.session_state.selected_columns_set = self._apply_preset("ge_focus", selected_columns)
                    st.session_state.column_selector_refresh += 1
                    st.rerun()

                if st.button(translations.get_text("preset_qi_focus", lang_code=self.lang_code), 
                            width='stretch', key="preset_qi"):
                    st.session_state.selected_columns_set = self._apply_preset("qi_focus", selected_columns)
                    st.session_state.column_selector_refresh += 1
                    st.rerun()

                if st.button(translations.get_text("preset_consumables_focus", lang_code=self.lang_code), 
                            width='stretch', key="preset_consumables"):
                    st.session_state.selected_columns_set = self._apply_preset("consumables_focus", selected_columns)
                    st.session_state.column_selector_refresh += 1
                    st.rerun()

        # Search functionality (only show if enabled)
        search_term = ""
        if show_search:
            st.subheader("🔍 " + translations.get_text("search_columns", lang_code=self.lang_code))
            search_term = st.text_input(
                translations.get_text("search_columns_placeholder", lang_code=self.lang_code),
                key="column_search",
                placeholder=translations.get_text("search_columns_placeholder", lang_code=self.lang_code)
            )
        
        # Filter columns based on search
        filtered_columns = self._filter_columns_by_search(search_term)
        
        # Quick actions (only show in advanced mode with search)
        if show_search:
            action_cols = st.columns(2)
            with action_cols[0]:
                if st.button(translations.get_text("select_all_visible", lang_code=self.lang_code), 
                            width='stretch', key="select_all_visible"):
                    for group_cols in filtered_columns.values():
                        st.session_state.selected_columns_set.update(group_cols)
                    st.session_state.column_selector_refresh += 1
                    st.rerun()
            
            with action_cols[1]:
                if st.button(translations.get_text("deselect_all_visible", lang_code=self.lang_code), 
                            width='stretch', key="deselect_all_visible"):
                    for group_cols in filtered_columns.values():
                        st.session_state.selected_columns_set.difference_update(group_cols)
                    # Always keep 'name' column
                    st.session_state.selected_columns_set.add(config.COL_NAME)
                    st.session_state.column_selector_refresh += 1
                    st.rerun()

        # Clear all button on its own row
        if st.button(translations.get_text("clear_all_selections", lang_code=self.lang_code),
                    width='stretch', key="clear_all"):
            st.session_state.selected_columns_set = {config.COL_NAME}
            st.session_state.column_selector_refresh += 1
            st.rerun()
        
        # Column selection by groups
        st.subheader("📂 " + translations.get_text("columns_by_group", lang_code=self.lang_code))
        
        if not filtered_columns:
            st.warning(translations.get_text("no_columns_match_search", lang_code=self.lang_code))
            return list(selected_columns)
        
        # Track changes to update session state
        changes_made = False
        
        for group_key, group_columns in filtered_columns.items():
            group_info = config.COLUMN_GROUPS[group_key]
            group_name = translations.get_text(group_info["key"], self.lang_code)
            
            with st.expander(f"{group_name} ({len(group_columns)} {translations.get_text('columns', self.lang_code)})", 
                           expanded=(group_key == "basic_info" or bool(search_term))):
                
                # Group-level controls
                group_cols = st.columns(2)
                
                with group_cols[0]:
                    if st.button(f"✅ {translations.get_text('select_all', self.lang_code)}", 
                               key=f"select_all_{group_key}", width='stretch'):
                        st.session_state.selected_columns_set.update(group_columns)
                        st.session_state.column_selector_refresh += 1
                        st.rerun()
                
                with group_cols[1]:
                    if st.button(f"❌ {translations.get_text('deselect_all', self.lang_code)}", 
                               key=f"deselect_all_{group_key}", width='stretch'):
                        st.session_state.selected_columns_set.difference_update(group_columns)
                        # Keep name column
                        st.session_state.selected_columns_set.add(config.COL_NAME)
                        st.session_state.column_selector_refresh += 1
                        st.rerun()
                
                # Show columns in this group
                for col in group_columns:
                    if col == config.COL_NAME:
                        continue  # Skip name as it's always selected
                    
                    new_selection = self._create_column_item(col, selected_columns, f"_{group_key}")
                    
                    # Use session state directly for change detection
                    if new_selection and col not in st.session_state.selected_columns_set:
                        st.session_state.selected_columns_set.add(col)
                        changes_made = True
                    elif not new_selection and col in st.session_state.selected_columns_set:
                        st.session_state.selected_columns_set.discard(col)
                        changes_made = True
                    
        
        # Always ensure 'name' is selected
        st.session_state.selected_columns_set.add(config.COL_NAME)
        
        if changes_made:
            st.rerun()
        
        # Sort selected columns according to COLUMN_GROUPS order
        return self._sort_columns_by_group_order(st.session_state.selected_columns_set)


def render_enhanced_column_selector(df_original: pd.DataFrame, lang_code: str, show_search: bool = True) -> List[str]:
    """Convenience function to render the enhanced column selector."""
    selector = ColumnSelector(df_original, lang_code)
    return selector.render_enhanced_column_selector(show_search=show_search) 