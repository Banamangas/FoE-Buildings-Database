import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Dict, Any, Optional
import numpy as np
import config
import translations
import ui_components
import building_images


class DataVisualizationManager:
    """Advanced data visualization system with charts, comparisons, and interactive analysis."""
    
    def __init__(self, df: pd.DataFrame, lang_code: str):
        self.df = df
        self.lang_code = lang_code
        self.numeric_columns = self._get_numeric_columns()
        self.categorical_columns = self._get_categorical_columns()
    
    def _get_numeric_columns(self) -> List[str]:
        """Get list of numeric columns suitable for visualization, ordered by COLUMN_GROUPS."""
        # Get all columns in the order they appear in COLUMN_GROUPS
        ordered_columns = []
        for group_info in config.COLUMN_GROUPS.values():
            ordered_columns.extend(group_info["columns"])
        
        numeric_cols = []
        for col in ordered_columns:
            if col in self.df.columns and col not in ['name']:
                # Check if column is numeric but not boolean
                if pd.api.types.is_numeric_dtype(self.df[col]) and not pd.api.types.is_bool_dtype(self.df[col]):
                    numeric_cols.append(col)
        return numeric_cols
    
    def _get_categorical_columns(self) -> List[str]:
        """Get list of categorical columns for grouping."""
        # Get all columns that are defined in COLUMN_GROUPS (user-visible columns)
        visible_columns = set()
        for group_info in config.COLUMN_GROUPS.values():
            visible_columns.update(group_info["columns"])
        categorical_cols = []
        for col in self.df.columns:
            if not pd.api.types.is_numeric_dtype(self.df[col]):
                if col in visible_columns and col not in ['name'] and self.df[col].nunique() < 20:  # Reasonable number of categories
                    categorical_cols.append(col)
        return sorted(categorical_cols)
    
    def _translate_column(self, col: str) -> str:
        """Translate column name."""
        return translations.translate_column(col, self.lang_code)
    
    def create_efficiency_scatter_plot(self, x_column: str, y_column: str, color_by: str = None, size_by: str = None) -> go.Figure:
        """Create an interactive scatter plot for efficiency analysis."""
        
        # Filter out rows with missing data
        plot_df = self.df.dropna(subset=[x_column, y_column])
        
        if plot_df.empty:
            fig = go.Figure()
            fig.add_annotation(text="No data available for selected columns", 
                             xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            return fig
        
        # Handle negative values in size column by setting them to 0
        if size_by and size_by in plot_df.columns:
            plot_df = plot_df.copy()
            plot_df[size_by] = plot_df[size_by].clip(lower=0)
        
        # Create hover template
        hover_template = "<b>%{customdata[0]}</b><br>"
        hover_template += f"{self._translate_column(x_column)}: %{{x}}<br>"
        hover_template += f"{self._translate_column(y_column)}: %{{y}}<br>"
        
        customdata = [plot_df['name'].tolist()]
        
        # Add color information if specified
        if color_by and color_by in plot_df.columns:
            hover_template += f"{self._translate_column(color_by)}: %{{customdata[1]}}<br>"
            customdata.append(plot_df[color_by].tolist())
        
        # Add size information if specified
        if size_by and size_by in plot_df.columns:
            hover_template += f"{self._translate_column(size_by)}: %{{customdata[2]}}<br>"
            if len(customdata) == 1:
                customdata.append([None] * len(plot_df))
            customdata.append(plot_df[size_by].tolist())
        
        hover_template += "<extra></extra>"
        
        # Create the plot
        fig = px.scatter(
            plot_df,
            x=x_column,
            y=y_column,
            color=color_by if color_by and color_by in plot_df.columns else None,
            size=size_by if size_by and size_by in plot_df.columns else None,
            title=f"{self._translate_column(y_column)} vs {self._translate_column(x_column)}",
            labels={
                x_column: self._translate_column(x_column),
                y_column: self._translate_column(y_column),
                color_by: self._translate_column(color_by) if color_by else None,
                size_by: self._translate_column(size_by) if size_by else None
            },
            hover_name='name'
        )
        
        # Customize layout
        fig.update_layout(
            title_x=0.5,
            height=600,
            showlegend=True if color_by else False
        )
        
        # Add trend line if both axes are numeric
        if len(plot_df) > 2:
            try:
                z = np.polyfit(plot_df[x_column], plot_df[y_column], 1)
                p = np.poly1d(z)
                x_trend = np.linspace(plot_df[x_column].min(), plot_df[x_column].max(), 100)
                y_trend = p(x_trend)
                
                fig.add_trace(go.Scatter(
                    x=x_trend,
                    y=y_trend,
                    mode='lines',
                    name='Trend Line',
                    line=dict(dash='dash', color='red', width=2),
                    showlegend=True
                ))
            except:
                pass  # Skip trend line if calculation fails
        
        return fig
    
    def create_distribution_chart(self, column: str, chart_type: str = "histogram", ignore_zeros: bool = False) -> go.Figure:
        """Create distribution charts (histogram, box plot, violin plot)."""
        
        plot_df = self.df.dropna(subset=[column])
        
        # Filter out zero values if requested
        if ignore_zeros:
            plot_df = plot_df[plot_df[column] != 0]
        
        if plot_df.empty:
            fig = go.Figure()
            fig.add_annotation(text="No data available for selected column", 
                             xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            return fig
        
        translated_name = self._translate_column(column)
        
        # Add suffix to title if zeros are excluded
        title_suffix = " (Excluding Zeros)" if ignore_zeros else ""
        
        if chart_type == "histogram":
            fig = px.histogram(
                plot_df, 
                x=column,
                title=f"{translated_name} Distribution{title_suffix}",
                labels={column: translated_name},
                nbins=min(30, int(plot_df[column].nunique()))
            )
        
        elif chart_type == "box":
            fig = px.box(
                plot_df,
                y=column,
                title=f"{translated_name} Box Plot{title_suffix}",
                labels={column: translated_name}
            )
        
        elif chart_type == "violin":
            fig = px.violin(
                plot_df,
                y=column,
                title=f"{translated_name} Violin Plot{title_suffix}",
                labels={column: translated_name},
                box=True
            )
        
        fig.update_layout(title_x=0.5, height=500)
        return fig
    
    def create_top_buildings_chart(self, metric_column: str, top_n: int = 10, chart_type: str = "bar") -> go.Figure:
        """Create charts showing top N buildings by a specific metric."""
        
        plot_df = self.df.dropna(subset=[metric_column]).nlargest(top_n, metric_column)
        
        if plot_df.empty:
            fig = go.Figure()
            fig.add_annotation(text="No data available", 
                             xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            return fig
        
        translated_name = self._translate_column(metric_column)
        
        if chart_type == "bar":
            fig = px.bar(
                plot_df,
                x='name',
                y=metric_column,
                title=f"Top {top_n} Buildings by {translated_name}",
                labels={'name': translations.get_text('building_name', self.lang_code), metric_column: translated_name}
            )
            fig.update_xaxes(tickangle=45)

        elif chart_type == "horizontal_bar":
            fig = px.bar(
                plot_df,
                x=metric_column,
                y='name',
                orientation='h',
                title=f"Top {top_n} Buildings by {translated_name}",
                labels={'name': translations.get_text('building_name', self.lang_code), metric_column: translated_name}
            )
            fig.update_layout(yaxis={'categoryorder': 'total ascending'})
        
        elif chart_type == "pie":
            fig = px.pie(
                plot_df,
                values=metric_column,
                names='name',
                title=f"Top {top_n} Buildings by {translated_name}"
            )
        
        fig.update_layout(title_x=0.5, height=600)
        return fig
    
    def create_comparison_chart(self, selected_buildings: List[str], metrics: List[str], show_per_square: bool = False) -> go.Figure:
        """Create a radar/spider chart for building comparison."""
        
        comparison_df = self.df[self.df['name'].isin(selected_buildings)]
        
        if comparison_df.empty or len(metrics) < 3:
            fig = go.Figure()
            fig.add_annotation(text="Select buildings and at least 3 metrics for comparison", 
                             xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
            return fig
        
        fig = go.Figure()
        
        # Normalize metrics to 0-100 scale for better comparison
        normalized_df = comparison_df[metrics].copy()
        for metric in metrics:
            max_val = self.df[metric].max()
            min_val = self.df[metric].min()
            if max_val > min_val:
                normalized_df[metric] = ((comparison_df[metric] - min_val) / (max_val - min_val)) * 100
            else:
                normalized_df[metric] = 50  # Default to middle if no variance
        
        # Create radar chart for each building
        colors = px.colors.qualitative.Set1[:len(selected_buildings)]
        
        for idx, (_, building) in enumerate(comparison_df.iterrows()):
            values = normalized_df.iloc[idx].tolist()
            values.append(values[0])  # Close the radar chart
            
            translated_metrics = [self._translate_column(m) for m in metrics]
            translated_metrics.append(translated_metrics[0])  # Close the labels
            
            fig.add_trace(go.Scatterpolar(
                r=values,
                text=values,
                theta=translated_metrics,
                fill='toself',
                name=building['name'],
                line_color=colors[idx % len(colors)]
            ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )),
            showlegend=True,
            title=f"{translations.get_text('building_comparison', self.lang_code)} ({translations.get_text('normalized_0_100', self.lang_code)}){' - ' + translations.get_text('stats_per_square', self.lang_code) if show_per_square else ''}",
            title_x=0.25,
            height=600
        )
        
        return fig
    
    def render_building_placement_simulator(self) -> None:
        """Render an interactive building placement simulator."""
        
        st.subheader("🏗️ " + translations.get_text("building_placement_simulator", self.lang_code))
        
        # City size configuration
        col1, col2 = st.columns(2)
        with col1:
            available_space = st.number_input(
                translations.get_text("available_space", self.lang_code),
                min_value=1, max_value=1000, value=100,
                help=translations.get_text("available_space_help", self.lang_code)
            )
        
        with col2:
            max_buildings = st.number_input(
                translations.get_text("max_buildings", self.lang_code),
                min_value=1, max_value=50, value=10,
                help=translations.get_text("max_buildings_help", self.lang_code)
            )
        
        # Building selection for simulation
        available_buildings = self.df[self.df['Nbr of squares (Avg)'] > 0]['name'].tolist()
        selected_buildings = st.multiselect(
            translations.get_text("select_buildings_for_simulation", self.lang_code),
            options=available_buildings,
            default=available_buildings[:5] if len(available_buildings) >= 5 else available_buildings,
            placeholder=translations.get_text("choose_an_option", self.lang_code)
        )
        
        if not selected_buildings:
            st.info(translations.get_text("select_buildings_for_simulation_help", self.lang_code))
            return
        
        # Optimization criteria
        optimization_criteria = st.selectbox(
            translations.get_text("optimization_criteria", self.lang_code),
            options=['Weighted Efficiency', 'Forge Points', 'Coins', 'Supplies'] + 
                   [col for col in self.df.columns if 'Goods' in col and pd.api.types.is_numeric_dtype(self.df[col])],
            format_func=lambda x: self._translate_column(x)
        )
        
        if st.button(translations.get_text("run_simulation", self.lang_code)):
            simulation_df = self.df[self.df['name'].isin(selected_buildings)].copy()
            
            if optimization_criteria not in simulation_df.columns:
                st.error(translations.get_text("optimization_criteria_not_available", self.lang_code))
                return
            
            # Simple greedy optimization algorithm
            simulation_df = simulation_df.dropna(subset=[optimization_criteria, 'Nbr of squares (Avg)'])
            
            if simulation_df.empty:
                st.warning(translations.get_text("no_valid_buildings_for_simulation", self.lang_code))
                return
            
            # Calculate efficiency per square
            simulation_df['efficiency_per_square'] = simulation_df[optimization_criteria] / simulation_df['Nbr of squares (Avg)']
            simulation_df = simulation_df.sort_values('efficiency_per_square', ascending=False)
            
            # Greedy selection
            selected_for_placement = []
            total_space_used = 0
            total_production = 0
            
            for _, building in simulation_df.iterrows():
                building_size = building['Nbr of squares (Avg)']
                if (total_space_used + building_size <= available_space and 
                    len(selected_for_placement) < max_buildings):
                    selected_for_placement.append({
                        'name': building['name'],
                        'size': building_size,
                        'production': building[optimization_criteria],
                        'efficiency_per_square': building['efficiency_per_square']
                    })
                    total_space_used += building_size
                    total_production += building[optimization_criteria]
            
            if not selected_for_placement:
                st.warning(translations.get_text("no_buildings_fit_constraints", self.lang_code))
                return
            
            # Display results
            st.success(translations.get_text("simulation_complete", self.lang_code))
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(translations.get_text("buildings_placed", self.lang_code), len(selected_for_placement))
            with col2:
                st.metric(translations.get_text("space_used", self.lang_code), f"{total_space_used:.1f}")
            with col3:
                st.metric(translations.get_text("space_efficiency", self.lang_code), 
                         f"{(total_space_used/available_space)*100:.1f}%")
            with col4:
                st.metric(translations.get_text("total_production", self.lang_code), f"{total_production:.1f}")
            
            # Detailed results table
            st.subheader(translations.get_text("placement_results", self.lang_code))
            results_df = pd.DataFrame(selected_for_placement)
            
            # Translate column names for display
            results_df_display = results_df.copy()
            results_df_display.columns = [
                translations.get_text("building_name", self.lang_code),
                translations.get_text("size", self.lang_code),
                self._translate_column(optimization_criteria),
                translations.get_text("efficiency_per_square", self.lang_code)
            ]
            
            st.dataframe(results_df_display, width='stretch')
            
            # Visualization of the placement
            if len(selected_for_placement) > 0:
                fig = px.treemap(
                    results_df,
                    path=['name'],
                    values='size',
                    color='efficiency_per_square',
                    color_continuous_scale='RdYlGn',
                    title=translations.get_text("space_allocation_visualization", self.lang_code)
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, width='stretch')
    
    def render_building_comparison_table(self, selected_buildings: List[str], selected_metrics: List[str], show_per_square: bool = False) -> None:
        """Render a detailed side-by-side comparison table."""
        
        if not selected_buildings or not selected_metrics:
            st.info(translations.get_text("select_buildings_and_metrics", self.lang_code))
            return
        
        comparison_df = self.df[self.df['name'].isin(selected_buildings)]
        
        if comparison_df.empty:
            st.warning(translations.get_text("no_buildings_found", self.lang_code))
            return
        
        # Prepare comparison data with icons
        table_data = []
        
        for metric in selected_metrics:
            # Get icon for the metric
            icon_url = None
            if metric not in config.ICON_EXCLUDED_COLUMNS:
                icon_base64 = ui_components.get_icon_base64(metric)
                if icon_base64:
                    icon_url = f"data:image/png;base64,{icon_base64}"
            
            # Create row data
            row_data = {
                "Icon": icon_url,
                "Metric": self._translate_column(metric)
            }
            
            # Add values for each building
            for building_name in selected_buildings:
                _rows = comparison_df[comparison_df['name'] == building_name]
                if _rows.empty:
                    continue
                building_data = _rows.iloc[0]
                value = building_data[metric]
                
                # Format value
                if metric in config.PERCENTAGE_COLUMNS:
                    formatted_value = f"{value}%"
                elif isinstance(value, float):
                    formatted_value = f"{value:.2f}" if value != int(value) else f"{int(value)}"
                elif isinstance(value, bool):
                    formatted_value = "Yes" if value else "No"
                else:
                    formatted_value = str(value)
                
                row_data[building_name] = formatted_value
            
            table_data.append(row_data)
        
        # Create DataFrame
        display_df = pd.DataFrame(table_data)
        
        # Style the dataframe to highlight maximum values
        def highlight_max_in_row(row):
            """Highlight the maximum value in each row for numeric columns."""
            styles = [''] * len(row)
            
            # Get building columns (exclude Icon and Metric columns)
            building_columns = [col for col in row.index if col not in ['Icon', 'Metric']]
            
            if len(building_columns) > 1:
                # Try to convert values to numeric for comparison
                numeric_values = {}
                for col in building_columns:
                    try:
                        # Remove % sign and convert to float
                        val_str = str(row[col]).replace('%', '').replace(',', '')
                        if val_str.lower() not in ['yes', 'no', 'true', 'false', '']:
                            numeric_values[col] = float(val_str)
                    except (ValueError, TypeError):
                        pass
                
                # Highlight maximum value if we have numeric values
                if numeric_values:
                    max_col = max(numeric_values.keys(), key=lambda k: numeric_values[k])
                    max_idx = row.index.get_loc(max_col)
                    styles[max_idx] = 'background-color: green'
            
            return styles
        
        # Apply styling
        styled_df = display_df.style.apply(highlight_max_in_row, axis=1)
        
        # Configure column config for the dataframe
        column_config = {
            "Icon": st.column_config.ImageColumn(
                label="",
                width=None,
                pinned=True
            ),
            "Metric": st.column_config.TextColumn(
                label=translations.get_text("metric", self.lang_code),
                width=None
            )
        }
        
        # Add column config for each building
        for building_name in selected_buildings:
            column_config[building_name] = st.column_config.TextColumn(
                label=building_name,
                width=None
            )
        
        st.subheader(translations.get_text("building_comparison_table", self.lang_code) + (" - " + translations.get_text("stats_per_square", self.lang_code) if show_per_square else ""))
        st.dataframe(
            styled_df,
            column_config=column_config,
            hide_index=True,
            use_container_width=False,
            height = 300 if len(styled_df.index) <= 10 else 600,
            width = 600
        )


def render_data_visualizations(df: pd.DataFrame, lang_code: str, show_per_square: bool = False) -> None:
    """Main function to render all data visualization components."""
    
    if df.empty:
        st.warning(translations.get_text("no_data_for_visualization", lang_code))
        return
    
    viz_manager = DataVisualizationManager(df, lang_code)
    
    st.header("📊 " + translations.get_text("data_visualizations", lang_code))

    # Create tabs for different visualization types
    viz_tabs = st.tabs([
        translations.get_text("top_buildings", lang_code),
        translations.get_text("building_comparison", lang_code)
    ])
    
    # Top Buildings Tab
    with viz_tabs[0]:
        st.subheader("🏆 " + translations.get_text("top_buildings_charts", lang_code))
        
        if show_per_square:
            st.info("📐 " + translations.get_text("per_square_mode_active", lang_code))
        
        col1, col2, col3 = st.columns(3)
        with col1:
            top_metric = st.selectbox(
                translations.get_text("select_metric", lang_code),
                options=viz_manager.numeric_columns,
                format_func=lambda x: viz_manager._translate_column(x),
                key="top_metric",
                index=6 if len(viz_manager.numeric_columns) > 1 else 0
            )
        
        with col2:
            top_n = st.slider(
                translations.get_text("number_of_buildings", lang_code),
                min_value=5, max_value=20, value=10,
                key="top_n"
            )
        
        with col3:
            top_chart_type = st.selectbox(
                translations.get_text("chart_type", lang_code),
                options=["horizontal_bar", "bar"],
                format_func=lambda x: translations.get_text(f"chart_type_{x}", lang_code),
                key="top_chart_type"
            )
        
        if top_metric:
            fig = viz_manager.create_top_buildings_chart(top_metric, top_n, top_chart_type)
            st.plotly_chart(fig, width='stretch')
    
    # Building Comparison Tab
    with viz_tabs[1]:
        st.subheader("⚖️ " + translations.get_text("building_comparison_analysis", lang_code))
        
        # Building selection (limited to 5)
        available_buildings = df['name'].unique().tolist()
        selected_buildings = st.multiselect(
            translations.get_text("select_buildings_to_compare", lang_code),
            options=available_buildings,
            max_selections=5,
            placeholder=translations.get_text("choose_an_option", lang_code),
            key="comparison_buildings"
        )
        
        # Auto-populate metrics when 2 or more buildings are selected
        auto_metrics = []
        if len(selected_buildings) >= 2:
            # Get all stats that at least one of the selected buildings has (non-zero values)
            selected_building_data = []
            for building_name in selected_buildings:
                _rows = df[df['name'] == building_name]
                if _rows.empty:
                    continue
                building_data = _rows.iloc[0]
                selected_building_data.append(building_data)
            
            for col in viz_manager.numeric_columns:
                # Check if at least one building has a non-zero value for this metric
                has_non_zero = False
                for building_data in selected_building_data:
                    if col in building_data:
                        val = building_data[col]
                        if val != 0 and not pd.isna(val):
                            has_non_zero = True
                            break
                
                if has_non_zero:
                    auto_metrics.append(col)
        
        # Metrics selection with auto-population
        comparison_metrics = st.multiselect(
            translations.get_text("select_metrics_to_compare", lang_code),
            options=viz_manager.numeric_columns,
            format_func=lambda x: viz_manager._translate_column(x),
            default=auto_metrics if len(selected_buildings) >= 2 else [],
            placeholder=translations.get_text("choose_an_option", lang_code),
            key="comparison_metrics"
        )
        
        if show_per_square:
            st.info("📐 " + translations.get_text("per_square_mode_active", lang_code))
        
        if len(selected_buildings) >= 2 and len(comparison_metrics) >= 3:
            # Create columns for side-by-side layout
            if selected_buildings and comparison_metrics:
                # Both radar chart and table are available - display side by side
                chart_col, table_col = st.columns([1, 1])

                with chart_col:
                    st.subheader("📊 " + translations.get_text("radar_chart", lang_code))
                    fig = viz_manager.create_comparison_chart(selected_buildings, comparison_metrics, show_per_square)
                    st.plotly_chart(fig, width='stretch')
                
                with table_col:
                                        
                    # Create a container for the table to center it
                    with st.container(key="comparison_table_container"):
                        st.markdown("<style> .st-key-comparison_table_container { display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100%; min-height: 600px; } </style>", unsafe_allow_html=True)
                        viz_manager.render_building_comparison_table(selected_buildings, comparison_metrics, show_per_square)
                
                # Add summary statistics below both components
                if len(selected_buildings) > 1:
                    st.subheader(translations.get_text("comparison_summary", lang_code))
                    
                    summary_cols = st.columns(len(selected_buildings))
                    
                    for idx, building_name in enumerate(selected_buildings):
                        with summary_cols[idx]:
                            _rows = df[df['name'] == building_name]
                            if _rows.empty:
                                continue
                            building_idx = _rows.index[0]
                            building_data = df.loc[building_idx]

                            # Add building image above the summary
                            building_id = building_data.get('id')
                            if building_id and building_images.has_building_image(building_id):
                                image_url = building_images.get_building_image_url(building_id)
                                # Use HTML/CSS for consistent height
                                image_width = int(800/len(selected_buildings))
                                st.markdown(
                                    f"""
                                    <div style="text-align: center;">
                                        <img src="{image_url}"
                                             style="width: {image_width}px; height: 200px; object-fit: contain; border-radius: 8px;"
                                             alt="{building_name}">
                                        <p style="margin-top: 5px; font-size: 14px; color: #666;">{building_name}</p>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )
                            else:
                                # Placeholder for buildings without images
                                st.markdown(f"**{building_name}**")
                                st.markdown("---")

                            # Calculate building's rank in each metric
                            ranks = []
                            for metric in comparison_metrics:
                                if pd.api.types.is_numeric_dtype(df[metric]):
                                    rank = df[metric].rank(ascending=False, method='min')[building_idx]
                                    ranks.append(f"#{int(rank)} in {viz_manager._translate_column(metric)}")

                            if ranks:
                                st.write("**Rankings:**")
                                for rank in ranks:  # Show top 3 rankings
                                    st.write(f"• {rank}")
            else:
                # Only radar chart available
                fig = viz_manager.create_comparison_chart(selected_buildings, comparison_metrics, show_per_square)
                st.plotly_chart(fig, width='stretch')
        
        elif selected_buildings and comparison_metrics:
            # Only table available (less than 3 metrics for radar chart)
            viz_manager.render_building_comparison_table(selected_buildings, comparison_metrics, show_per_square)
            
            # Add summary statistics below table
            if len(selected_buildings) > 1:
                st.subheader(translations.get_text("comparison_summary", lang_code))
                
                summary_cols = st.columns(len(selected_buildings))
                
                for idx, building_name in enumerate(selected_buildings):
                    with summary_cols[idx]:
                        _rows = df[df['name'] == building_name]
                        if _rows.empty:
                            continue
                        building_idx = _rows.index[0]
                        building_data = df.loc[building_idx]

                        # Add building image above the summary
                        building_id = building_data.get('id')
                        if building_id and building_images.has_building_image(building_id):
                            image_url = building_images.get_building_image_url(building_id)
                            # Use HTML/CSS for consistent height
                            image_width = int(800/len(selected_buildings))
                            st.markdown(
                                f"""
                                <div style="text-align: center;">
                                    <img src="{image_url}"
                                         style="width: {image_width}px; height: 200px; object-fit: contain; border-radius: 8px;"
                                         alt="{building_name}">
                                    <p style="margin-top: 5px; font-size: 14px; color: #666;">{building_name}</p>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                        else:
                            # Placeholder for buildings without images
                            st.markdown(f"**{building_name}**")
                            st.markdown("---")

                        # Calculate building's rank in each metric
                        ranks = []
                        for metric in comparison_metrics:
                            if pd.api.types.is_numeric_dtype(df[metric]):
                                rank = df[metric].rank(ascending=False, method='min')[building_idx]
                                ranks.append(f"#{int(rank)} in {viz_manager._translate_column(metric)}")

                        if ranks:
                            st.write("**Rankings:**")
                            for rank in ranks:  # Show top 3 rankings
                                st.write(f"• {rank}")
    
 