import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional
import config
import translations


class AdvancedFilterManager:
    """Advanced filtering system with range sliders, compound filters, presets, and exclusion modes."""
    
    # Predefined filter presets for common scenarios
    
    def __init__(self, df: pd.DataFrame, lang_code: str, selected_era: str = None):
        self.df = df
        self.lang_code = lang_code
        self.selected_era = selected_era
        self.numeric_columns = self._get_numeric_columns()
        self.categorical_columns = self._get_categorical_columns()
        
        # Initialize session state for filters
        if 'advanced_filters' not in st.session_state:
            st.session_state.advanced_filters = {}
        if 'filter_logic' not in st.session_state:
            st.session_state.filter_logic = "AND"
        if 'active_filters_count' not in st.session_state:
            st.session_state.active_filters_count = 0
    
    def _get_numeric_columns(self) -> List[str]:
        """Get list of numeric columns suitable for range filtering."""
        # Get all columns that are defined in COLUMN_GROUPS (user-visible columns)
        visible_columns = set()
        for group_info in config.COLUMN_GROUPS.values():
            visible_columns.update(group_info["columns"])
        
        numeric_cols = []
        for col in self.df.columns:
            if pd.api.types.is_numeric_dtype(self.df[col]):
                # Only include columns that are in the visible column groups
                # and exclude columns that shouldn't have range filters
                if col in visible_columns and col not in [config.COL_NAME, config.COL_ERA, config.COL_EVENT, config.COL_TRANSLATED_ERA]:
                    numeric_cols.append(col)
        return sorted(numeric_cols)
    
    def _get_categorical_columns(self) -> List[str]:
        """Get list of categorical columns suitable for selection filters."""
        # Get all columns that are defined in COLUMN_GROUPS (user-visible columns)
        visible_columns = set()
        for group_info in config.COLUMN_GROUPS.values():
            visible_columns.update(group_info["columns"])
        
        categorical_cols = []
        for col in self.df.columns:
            if not pd.api.types.is_numeric_dtype(self.df[col]):
                # Only include columns that are in the visible column groups
                # and exclude name as it has its own search
                if col in visible_columns and col not in [config.COL_NAME]:
                    categorical_cols.append(col)
        return sorted(categorical_cols)
    
    def _create_range_filter(self, column: str) -> Optional[Dict[str, Any]]:
        """Create a range filter widget for a numeric column with operator selection."""
        if column not in self.df.columns:
            return None
        
        col_data = self.df[column].dropna()
        if col_data.empty:
            return None
        
        min_val = float(col_data.min())
        max_val = float(col_data.max())
        
        if min_val == max_val:
            return None  # No range to filter
        
        translated_name = translations.translate_column(column, self.lang_code)
        
        # Get current filter values
        current_filter = st.session_state.advanced_filters.get(column, {})
        current_operator = current_filter.get('operator', 'between')
        current_value1 = current_filter.get('value1', min_val)
        current_value2 = current_filter.get('value2', max_val)
        current_exclude = current_filter.get('exclude', False)
        
        # Ensure current values are within bounds
        current_value1 = max(min_val, min(max_val, current_value1 if current_value1 is not None else min_val))
        current_value2 = max(min_val, min(max_val, current_value2 if current_value2 is not None else max_val))
        
        # Exclusion toggle
        exclude_mode = st.checkbox(
            translations.get_text("exclude_mode", self.lang_code),
            value=current_exclude,
            help=translations.get_text("exclude_mode_help", self.lang_code),
            key=f"exclude_numeric_{column}"
        )
        
        # Operator selection
        operator_options = {
            'between': translations.get_text("operator_between", self.lang_code),
            'greater_than': translations.get_text("operator_greater_than", self.lang_code),
            'greater_equal': translations.get_text("operator_greater_equal", self.lang_code),
            'less_than': translations.get_text("operator_less_than", self.lang_code),
            'less_equal': translations.get_text("operator_less_equal", self.lang_code),
            'equal': translations.get_text("operator_equal", self.lang_code),
            'not_equal': translations.get_text("operator_not_equal", self.lang_code)
        }
        
        selected_operator = st.selectbox(
            translations.get_text("filter_operator", self.lang_code),
            options=list(operator_options.keys()),
            format_func=lambda x: operator_options[x],
            index=list(operator_options.keys()).index(current_operator) if current_operator in operator_options else 0,
            key=f"operator_{column}"
        )
        
        # Value inputs based on operator
        step_size = 1.0 if max_val - min_val > 100 else 0.1
        
        if selected_operator == 'between':
            col1, col2 = st.columns(2)
            with col1:
                value1 = st.number_input(
                    translations.get_text("min_value", self.lang_code),
                    min_value=min_val,
                    max_value=max_val,
                    value=current_value1,
                    step=step_size,
                    key=f"filter_value1_{column}"
                )
            with col2:
                value2 = st.number_input(
                    translations.get_text("max_value", self.lang_code),
                    min_value=min_val,
                    max_value=max_val,
                    value=current_value2,
                    step=step_size,
                    key=f"filter_value2_{column}"
                )
            
            # Ensure min <= max
            if value1 > value2:
                value1, value2 = value2, value1
            
            return {
                "operator": selected_operator,
                "value1": value1,
                "value2": value2,
                "exclude": exclude_mode
            }
        
        else:
            # Single value operators
            value1 = st.number_input(
                f"{operator_options[selected_operator]} {translated_name}",
                min_value=min_val,
                max_value=max_val,
                value=current_value1,
                step=step_size,
                key=f"filter_single_value_{column}"
            )
            
            return {
                "operator": selected_operator,
                "value1": value1,
                "exclude": exclude_mode
            }
    
    def _create_categorical_filter(self, column: str) -> Optional[Dict[str, Any]]:
        """Create a categorical filter widget."""
        if column not in self.df.columns:
            return None
        
        unique_values = sorted([str(val) for val in self.df[column].dropna().unique()])
        if len(unique_values) <= 1:
            return None
        
        translated_name = translations.translate_column(column, self.lang_code)
        
        # Get current filter values
        current_filter = st.session_state.advanced_filters.get(column, {})
        current_values = current_filter.get('values', [])
        current_exclude = current_filter.get('exclude', False)
        
        # Ensure current values exist in the data
        current_values = [val for val in current_values if val in unique_values]
        
        # Exclusion toggle
        exclude_mode = st.checkbox(
            translations.get_text("exclude_mode", self.lang_code),
            value=current_exclude,
            help=translations.get_text("exclude_mode_help", self.lang_code),
            key=f"exclude_categorical_{column}"
        )
        
        selected_values = st.multiselect(
            translations.get_text('filter_column_label', self.lang_code).format(name=translated_name),
            options=unique_values,
            default=current_values,
            placeholder=translations.get_text("choose_an_option", self.lang_code),
            key=f"filter_cat_{column}"
        )
        
        if selected_values and len(selected_values) < len(unique_values):
            return {"values": selected_values, "operation": "isin", "exclude": exclude_mode}
        
        return None
    
    def _create_operator_mask(self, source_df: pd.DataFrame, column: str, filter_config: Dict[str, Any]) -> Optional[pd.Series]:
        """Build a boolean mask for a single filter criterion.

        Returns None if the filter config is unrecognised or has no applicable logic,
        signalling the caller to skip this filter entirely.
        """
        if "operator" in filter_config:
            op = filter_config["operator"]
            v1 = filter_config["value1"]
            v2 = filter_config.get("value2")
            if op == "between":
                return (source_df[column] >= v1) & (source_df[column] <= v2)
            elif op == "greater_than":
                return source_df[column] > v1
            elif op == "greater_equal":
                return source_df[column] >= v1
            elif op == "less_than":
                return source_df[column] < v1
            elif op == "less_equal":
                return source_df[column] <= v1
            elif op == "equal":
                return source_df[column] == v1
            elif op == "not_equal":
                return source_df[column] != v1
            return None  # Unknown operator → skip

        elif "min" in filter_config or "max" in filter_config:
            # Legacy numeric range filter
            mask = pd.Series([True] * len(source_df), index=source_df.index)
            if filter_config.get("min") is not None:
                mask &= source_df[column] >= filter_config["min"]
            if filter_config.get("max") is not None:
                mask &= source_df[column] <= filter_config["max"]
            return mask

        elif "values" in filter_config:
            if filter_config["operation"] == "isin":
                return source_df[column].isin(filter_config["values"])
            return None  # Unknown operation → skip

        elif "value" in filter_config:
            if filter_config.get("operation") == "contains":
                return source_df[column].astype(str).str.contains(
                    str(filter_config["value"]), case=False, na=False
                )
            return source_df[column] == filter_config["value"]

        return None  # Unrecognised filter config → skip

    def _apply_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply all active filters to the dataframe."""
        filtered_df = df.copy()
        filter_logic = st.session_state.filter_logic

        if not st.session_state.advanced_filters:
            return filtered_df

        if filter_logic == "AND":
            for column, filter_config in st.session_state.advanced_filters.items():
                if column not in filtered_df.columns:
                    continue
                mask = self._create_operator_mask(filtered_df, column, filter_config)
                if mask is None:
                    continue
                if filter_config.get("exclude", False):
                    mask = ~mask
                filtered_df = filtered_df[mask]

        else:  # OR logic
            combined_mask = pd.Series([False] * len(df), index=df.index)
            for column, filter_config in st.session_state.advanced_filters.items():
                if column not in df.columns:
                    continue
                mask = self._create_operator_mask(df, column, filter_config)
                if mask is None:
                    continue
                if filter_config.get("exclude", False):
                    mask = ~mask
                combined_mask |= mask
            filtered_df = df[combined_mask]

        return filtered_df
    
    def render_advanced_filters(self) -> pd.DataFrame:
        """Render the advanced filtering UI and return filtered dataframe."""
        
        with st.expander("🔧 " + translations.get_text("advanced_filters", lang_code=self.lang_code), expanded=False):
            
            # Filter logic selection
            st.subheader("🔗 " + translations.get_text("filter_logic", lang_code=self.lang_code))
            filter_logic = st.radio(
                translations.get_text("filter_logic_help", lang_code=self.lang_code),
                options=["AND", "OR"],
                index=0 if st.session_state.filter_logic == "AND" else 1,
                horizontal=True,
                key="filter_logic_radio"
            )
            st.session_state.filter_logic = filter_logic
            
            # Active filters management
            # Clear all button taking full width
            if st.button(translations.get_text("clear_all_filters", lang_code=self.lang_code), 
                       width='stretch', key="clear_filters"):
                st.session_state.advanced_filters = {}
                st.session_state.active_filters_count = 0
                st.rerun()
            
            # Filter creation section
            st.subheader("🎛️ " + translations.get_text("create_filters", lang_code=self.lang_code))
            
            # Tabs for different filter types
            filter_tabs = st.tabs([
                translations.get_text("numeric_filters", lang_code=self.lang_code),
                translations.get_text("categorical_filters", lang_code=self.lang_code)
            ])
            
            # Numeric filters tab
            with filter_tabs[0]:
                if self.numeric_columns:
                    selected_numeric_col = st.selectbox(
                        translations.get_text("select_numeric_column", lang_code=self.lang_code),
                        options=[""] + self.numeric_columns,
                        format_func=lambda x: translations.translate_column(x, self.lang_code) if x else translations.get_text("select_column", lang_code=self.lang_code),
                        key="numeric_filter_selector"
                    )
                    
                    if selected_numeric_col:
                        filter_result = self._create_range_filter(selected_numeric_col)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(translations.get_text("add_filter", lang_code=self.lang_code), 
                                       key="add_numeric_filter", width='stretch'):
                                if filter_result:
                                    st.session_state.advanced_filters[selected_numeric_col] = filter_result
                                    st.rerun()
                        
                        with col2:
                            if st.button(translations.get_text("remove_filter", lang_code=self.lang_code), 
                                       key="remove_numeric_filter", width='stretch'):
                                if selected_numeric_col in st.session_state.advanced_filters:
                                    del st.session_state.advanced_filters[selected_numeric_col]
                                    st.rerun()
                else:
                    st.info(translations.get_text("no_numeric_columns", lang_code=self.lang_code))
            
            # Categorical filters tab
            with filter_tabs[1]:
                if self.categorical_columns:
                    selected_cat_col = st.selectbox(
                        translations.get_text("select_categorical_column", lang_code=self.lang_code),
                        options=[""] + self.categorical_columns,
                        format_func=lambda x: translations.translate_column(x, self.lang_code) if x else translations.get_text("select_column", lang_code=self.lang_code),
                        key="categorical_filter_selector"
                    )
                    
                    if selected_cat_col:
                        filter_result = self._create_categorical_filter(selected_cat_col)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(translations.get_text("add_filter", lang_code=self.lang_code), 
                                       key="add_categorical_filter", width='stretch'):
                                if filter_result:
                                    st.session_state.advanced_filters[selected_cat_col] = filter_result
                                    st.rerun()
                        
                        with col2:
                            if st.button(translations.get_text("remove_filter", lang_code=self.lang_code), 
                                       key="remove_categorical_filter", width='stretch'):
                                if selected_cat_col in st.session_state.advanced_filters:
                                    del st.session_state.advanced_filters[selected_cat_col]
                                    st.rerun()
                else:
                    st.info(translations.get_text("no_categorical_columns", lang_code=self.lang_code))
            
            # Show active filters summary with individual remove buttons
            if st.session_state.advanced_filters:
                st.markdown("---")
                st.subheader("📋 " + translations.get_text("active_filters_summary", lang_code=self.lang_code))
                
                for column, filter_config in st.session_state.advanced_filters.items():
                    translated_name = translations.translate_column(column, self.lang_code)
                    exclude_mode = filter_config.get("exclude", False)
                    exclude_prefix = translations.get_text("not_label", self.lang_code) + " " if exclude_mode else ""
                    
                    # Create columns for filter description and remove button
                    desc_col, btn_col = st.columns([4, 1])
                    
                    with desc_col:
                        # Handle new operator-based numeric filters
                        if "operator" in filter_config:
                            operator = filter_config["operator"]
                            value1 = filter_config["value1"]
                            value2 = filter_config.get("value2")
                            
                            if operator == "between":
                                st.write(f"• **{exclude_prefix}{translated_name}**: {value1} ≤ value ≤ {value2}")
                            elif operator == "greater_than":
                                st.write(f"• **{exclude_prefix}{translated_name}**: > {value1}")
                            elif operator == "greater_equal":
                                st.write(f"• **{exclude_prefix}{translated_name}**: ≥ {value1}")
                            elif operator == "less_than":
                                st.write(f"• **{exclude_prefix}{translated_name}**: < {value1}")
                            elif operator == "less_equal":
                                st.write(f"• **{exclude_prefix}{translated_name}**: ≤ {value1}")
                            elif operator == "equal":
                                st.write(f"• **{exclude_prefix}{translated_name}**: = {value1}")
                            elif operator == "not_equal":
                                st.write(f"• **{exclude_prefix}{translated_name}**: ≠ {value1}")
                        
                        # Handle legacy min/max filters (for backward compatibility)
                        elif "min" in filter_config or "max" in filter_config:
                            min_val = filter_config.get("min", "∞")
                            max_val = filter_config.get("max", "∞")
                            st.write(f"• **{exclude_prefix}{translated_name}**: {min_val} ≤ value ≤ {max_val}")
                        
                        elif "values" in filter_config:
                            values_str = ", ".join(str(v) for v in filter_config["values"][:3])
                            if len(filter_config["values"]) > 3:
                                values_str += f" (+{len(filter_config['values']) - 3} more)"
                            st.write(f"• **{exclude_prefix}{translated_name}**: {values_str}")
                        
                        elif "value" in filter_config:
                            st.write(f"• **{exclude_prefix}{translated_name}**: {filter_config['value']}")
                    
                    with btn_col:
                        if st.button("🗑️", key=f"remove_filter_{column}", 
                                   help=translations.get_text("remove_this_filter", self.lang_code)):
                            del st.session_state.advanced_filters[column]
                            st.rerun()
        
        # Apply filters and return filtered dataframe
        return self._apply_filters(self.df)


def render_advanced_filters(df: pd.DataFrame, lang_code: str, selected_era: str = None) -> pd.DataFrame:
    """Convenience function to render advanced filters and return filtered dataframe."""
    filter_manager = AdvancedFilterManager(df, lang_code, selected_era)
    return filter_manager.render_advanced_filters() 