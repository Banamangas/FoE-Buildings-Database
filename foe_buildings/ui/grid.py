import base64
import os
from functools import lru_cache
from io import BytesIO
from typing import Dict, Any

import pandas as pd
from PIL import Image
from st_aggrid import GridOptionsBuilder, JsCode

# Import configurations and translations
from foe_buildings.config import (
    ASSETS_PATH,
    ICON_EXCLUDED_COLUMNS,
    PERCENTAGE_COLUMNS,
    logger,
    COL_NAME,
    COL_EVENT,
    COL_WEIGHTED_EFFICIENCY,
)
from foe_buildings.i18n import translate_column  # Import the specific function


# --- Icon Handling ---
@lru_cache(maxsize=128)
def load_icon(icon_name: str) -> Image.Image:
    """Load icon from assets folder, resize, and ensure RGBA."""
    try:
        icon_name = icon_name.lower().replace(" ", "_")
        icon_path = os.path.join(ASSETS_PATH, "icons", f"{icon_name}.png")

        if not os.path.exists(icon_path):
            logger.warning(
                f"Icon not found: {icon_name} at path: {icon_path}"
            )  # Can be noisy
            return None

        icon = Image.open(icon_path).convert("RGBA")
        new_icon = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
        scale = min(24 / icon.width, 24 / icon.height)
        new_size = (int(icon.width * scale), int(icon.height * scale))
        resized_icon = icon.resize(new_size, Image.Resampling.LANCZOS)
        position = ((24 - new_size[0]) // 2, (24 - new_size[1]) // 2)
        new_icon.paste(resized_icon, position, resized_icon)
        return new_icon
    except Exception as e:
        logger.error(f"Error loading icon {icon_name}: {str(e)}")
        return None


@lru_cache(maxsize=128)
def get_icon_base64(icon_name: str) -> str:
    """Convert icon to base64 string."""
    try:
        icon = load_icon(icon_name)
        if icon is None:
            return None

        buffered = BytesIO()
        icon.save(buffered, format="PNG", optimize=True)
        base64_str = base64.b64encode(buffered.getvalue()).decode()
        return base64_str
    except Exception as e:
        logger.error(f"Error converting icon {icon_name} to base64: {str(e)}")
        return None


def get_icon_html(col_name: str, show_label: bool, label_value: str) -> str:
    """Create HTML for column header with icon."""
    icon_name = col_name  # Use original col name for lookup if needed
    icon_base64 = get_icon_base64(icon_name)

    if icon_base64:
        label = (
            f'<span style="margin-left: 5px">{label_value}</span>' if show_label else ""
        )
        return f"""
            <img src="data:image/png;base64,{icon_base64}"
                 style="width: 24px; height: 24px; vertical-align: middle;">{label}
        """
    return label_value  # Return label if icon fails


# --- AgGrid JsCode Definitions ---

CUSTOM_HEADER_COMPONENT = JsCode("""class CustomIconHeader {
    init(params) {
        this.params = params;

        // Create the main container element directly with desired classes/role
        this.eGui = document.createElement('div');
        this.eGui.classList.add('ag-cell-label-container');
        this.eGui.setAttribute('role', 'presentation');
        this.eGui.style.display = 'flex';
        this.eGui.style.flexDirection = 'row-reverse';
        this.eGui.style.alignItems = 'center';
        this.eGui.style.width = '100%';
        this.eGui.style.justifyContent = 'space-between';


        // Initial sort class will be updated by onSortChanged


        // --- Create Filter Button ---
        this.eFilterButton = document.createElement('span');
        this.eFilterButton.setAttribute('data-ref', 'eFilterButton');
        this.eFilterButton.classList.add('ag-header-icon', 'ag-header-cell-filter-button');
        this.eFilterButton.setAttribute('aria-hidden', 'true');
        // Add inner span for icon if needed by theme, replicating default:
        this.eFilterButton.innerHTML = '<span class="ag-icon ag-icon-filter" unselectable="on" role="presentation"></span>';


        // --- Create Label Container ---
        this.eLabel = document.createElement('div');
        this.eLabel.setAttribute('data-ref', 'eLabel');
        this.eLabel.classList.add('ag-header-cell-label');
        this.eLabel.setAttribute('role', 'presentation');
        this.eLabel.style.display = 'flex';
        this.eLabel.style.flexDirection = 'row';

        // --- Create Text Span (for custom content) ---
        this.eText = document.createElement('span');
        this.eText.setAttribute('data-ref', 'eText');
        this.eText.classList.add('ag-header-cell-text');
        // Insert custom content (icon/label) into eText
        if (params.headerContent) {
            const tempElement = document.createElement('div');
            tempElement.innerHTML = params.headerContent.trim();
            while (tempElement.firstChild) {
                this.eText.appendChild(tempElement.firstChild);
            }
        } else {
            this.eText.innerText = params.displayName;
        }


        // --- Create Sort Indicator Container ---
        this.eSortIndicator = document.createElement('span');
        this.eSortIndicator.classList.add('ag-sort-indicator-container');
        this.eSortIndicator.setAttribute('data-ref', 'eSortIndicator');
        this.eSortIndicator.innerHTML = `
            <span data-ref="eSortOrder" class="ag-sort-indicator-icon ag-sort-order ag-hidden" aria-hidden="true"></span>
            <span data-ref="eSortAsc" class="ag-sort-indicator-icon ag-sort-ascending-icon ag-hidden" aria-hidden="true"><span class="ag-icon ag-icon-asc" unselectable="on" role="presentation"></span></span>
            <span data-ref="eSortDesc" class="ag-sort-indicator-icon ag-sort-descending-icon ag-hidden" aria-hidden="true"><span class="ag-icon ag-icon-desc" unselectable="on" role="presentation"></span></span>
            <span data-ref="eSortMixed" class="ag-sort-indicator-icon ag-sort-mixed-icon ag-hidden" aria-hidden="true"><span class="ag-icon ag-icon-none" unselectable="on" role="presentation"></span></span>
            <span data-ref="eSortNone" class="ag-sort-indicator-icon ag-sort-none-icon ag-hidden" aria-hidden="true"><span class="ag-icon ag-icon-none" unselectable="on" role="presentation"></span></span>
        `;
        // Get references to inner sort elements
        this.eSortOrder = this.eSortIndicator.querySelector('[data-ref="eSortOrder"]');
        this.eSortAsc = this.eSortIndicator.querySelector('[data-ref="eSortAsc"]');
        this.eSortDesc = this.eSortIndicator.querySelector('[data-ref="eSortDesc"]');
        this.eSortNone = this.eSortIndicator.querySelector('[data-ref="eSortNone"]');
        this.eSortMixed = this.eSortIndicator.querySelector('[data-ref="eSortMixed"]'); // Added reference


        // --- Assemble Label Container ---
        this.eLabel.appendChild(this.eText);
        this.eLabel.appendChild(this.eSortIndicator);


        // --- Assemble the main GUI (eGui) ---
        // Order based on default HTML: Filter, Label
        this.eGui.appendChild(this.eFilterButton);
        this.eGui.appendChild(this.eLabel);


        // --- Add Event Listeners ---
        // Filter listener
        if (params.enableFilter) {
            this.eFilterButton.addEventListener('click', (event) => {
                params.showFilter(this.eFilterButton); // Show filter menu anchored to our button
            });
        }

        // Sort listener (to the label)
        if (params.enableSorting) {
             this.eLabel.addEventListener('click', (event) => {
                 params.progressSort(); // Cycle through sort states
             });
             this.eLabel.style.cursor = 'pointer';
        }

        // Add sort state listener
        this.onSortChangedListener = this.onSortChanged.bind(this);
        params.column.addEventListener('sortChanged', this.onSortChangedListener);
        this.onSortChanged(); // Set initial sort icon visibility and container class
    }

    getGui() {
        return this.eGui; // Return the main container
    }

    destroy() {
        if (this.onSortChangedListener) {
            this.params.column.removeEventListener('sortChanged', this.onSortChangedListener);
        }
        // Remove other listeners if needed
    }

    onSortChanged() {
        const sort = this.params.column.getSort();
        const multiSort = this.params.column.getSortIndex() > 0;

        // Update main container's sort class
        this.eGui.classList.remove(
            'ag-header-cell-sorted-asc',
            'ag-header-cell-sorted-desc',
            'ag-header-cell-sorted-none'
            // Add 'ag-header-cell-sorted-mixed' if handling mixed sorting
        );
        if (sort === 'asc') {
            this.eGui.classList.add('ag-header-cell-sorted-asc');
        } else if (sort === 'desc') {
            this.eGui.classList.add('ag-header-cell-sorted-desc');
        } else {
            this.eGui.classList.add('ag-header-cell-sorted-none');
        }


        const updateVisibility = (element, visible) => {
            if (element) {
                element.classList.toggle('ag-hidden', !visible);
                element.setAttribute('aria-hidden', String(!visible));
            }
        };

        // Update sort indicator icons visibility
        updateVisibility(this.eSortAsc, sort === 'asc');
        updateVisibility(this.eSortDesc, sort === 'desc');
        updateVisibility(this.eSortNone, sort === 'none');
        // updateVisibility(this.eSortMixed, sort === 'mixed'); // Add if handling mixed sort state

        // Handle multi-sort order display
        if (this.eSortOrder) {
             if (multiSort && sort && sort !== 'mixed') { // Don't show order for mixed
                  this.eSortOrder.innerText = this.params.column.getSortIndex() + 1;
                  updateVisibility(this.eSortOrder, true);
             } else {
                  updateVisibility(this.eSortOrder, false);
             }
        }
    }
}
""")

PERCENTAGE_FORMATTER = JsCode("""
    function(params) {
        if (params.value != null && typeof params.value === 'number') {
            if (params.value !== 0) {
                return params.value + '%';
            }
            return '0%';
        }
        return params.value;
    }""")

NOPERCENTAGE_FORMATTER = JsCode("""
    function(params) {
        if (params.value != null) {
            if (typeof params.value === 'number') {
                if (params.value !== 0) {
                    return params.value;
                }
                return '0';
            }
            if (typeof params.value === 'boolean') {
                return params.value ? '✔️' : '❌';
            }
            return params.value;
        }
        return 'N/A'; // Default for null/undefined values
    }""")


def generate_heatmap_style_js(eff_min: float, eff_max: float) -> JsCode:
    """Generates the JsCode for heatmap cell styling."""
    return JsCode(f"""
        function(params) {{
            const value = params.value;
            const min = {eff_min};
            const max = {eff_max};

            if (value === null || value === undefined || isNaN(value) || max === min) {{
                return {{ 'textAlign': 'center' }}; // Use style centered
            }}

            const normalized = (value - min) / (max - min);
            const r = Math.round(44 + normalized * (184 - 44));
            const g = Math.round(62 + normalized * (162 - 62));
            const b = Math.round(80 + normalized * (20 - 80));
            const color = 'rgb(' + r + ',' + g + ',' + b + ')';

            // Return background color and ensure text is black and centered
            return {{ 'backgroundColor': color, 'color': 'black', 'fontWeight': 'bold', 'textAlign': 'center' }};
            // Centering is now handled by defaultColDef
        }}
    """)


# --- AgGrid Configuration Builder ---
def build_grid_options(
    df_display: pd.DataFrame,
    lang_code: str,
    use_icons: bool,
    show_labels: bool,
    enable_heatmap: bool,
    eff_min: float,
    eff_max: float,
    page_size: int = 50,
) -> Dict[str, Any]:
    """Builds the AgGrid GridOptions dictionary."""

    gb = GridOptionsBuilder.from_dataframe(df_display)
    gb.configure_selection(selection_mode="single")
    # Register custom header component
    gb.configure_grid_options(components={"CustomIconHeader": CUSTOM_HEADER_COMPONENT})

    # Generate heatmap style if enabled
    heatmap_style = (
        generate_heatmap_style_js(eff_min, eff_max) if enable_heatmap else None
    )

    # Configure columns individually
    for col in df_display.columns:
        # Get translated header name
        header_name = translate_column(col, lang_code)

        # Determine column type for filter configuration
        is_numeric = pd.api.types.is_numeric_dtype(df_display[col])

        # Set minimum width for columns
        if col == COL_NAME:
            min_width = 200
            max_width = 300
        elif col == COL_EVENT:
            min_width = 150
            max_width = None
        else:
            min_width = 100
            max_width = None

        # Base configuration
        base_config = {
            "headerName": header_name,
            "headerTooltip": header_name,
            "sortable": True,
            "filter": True,
            "resizable": True,
            "type": "customNumericColumn" if is_numeric else "customTextColumn",
            "minWidth": min_width,
        }
        if max_width is not None:
            base_config["maxWidth"] = max_width

        # --- Apply percentage formatter ---
        if col in PERCENTAGE_COLUMNS:
            base_config["valueFormatter"] = PERCENTAGE_FORMATTER
            base_config["filterParams"] = {"valueFormatter": PERCENTAGE_FORMATTER}
        else:
            base_config["valueFormatter"] = NOPERCENTAGE_FORMATTER
            base_config["filterParams"] = {"valueFormatter": NOPERCENTAGE_FORMATTER}

        # --- Apply Heatmap Style to Weighted Efficiency ---
        if col == COL_WEIGHTED_EFFICIENCY and heatmap_style:
            base_config["cellStyle"] = heatmap_style

        # --- Tooltip Logic ---
        base_config["tooltipValueGetter"] = JsCode("""
            function(params) {
                return params.colDef.headerName + ': ' + params.valueFormatted;
            }
        """)

        # --- Header Configuration (Icon / Default) ---
        if use_icons and col not in ICON_EXCLUDED_COLUMNS:
            icon_html = get_icon_html(col, show_labels, label_value=header_name)
            # Icon columns are narrower than text columns; override base_config widths.
            icon_config = {**base_config, "minWidth": 80, "maxWidth": 120}
            gb.configure_column(
                col,
                **icon_config,
                headerComponent="CustomIconHeader",
                headerComponentParams={
                    "headerContent": icon_html,
                    "enableFilter": True,
                    "enableSorting": True,
                },
            )
        else:
            base_config["headerComponent"] = "CustomIconHeader"
            base_config["headerComponentParams"] = {
                "headerContent": header_name,
                "enableFilter": True,
                "enableSorting": True,
            }
            gb.configure_column(col, **base_config)

    # Common grid configurations
    gb.configure_default_column(
        filter=True,
        sortable=True,
        resizable=True,
        cellStyle={"textAlign": "center"},  # Default center alignment
    )

    # Configure pagination
    gb.configure_pagination(paginationPageSize=page_size, paginationAutoPageSize=False)

    grid_options = gb.build()

    # Define custom column types
    grid_options["columnTypes"] = {
        "customTextColumn": {
            "filter": "agTextColumnFilter",
            "filterParams": {"buttons": ["reset", "apply"], "closeOnApply": True},
        },
        "customNumericColumn": {
            "filter": "agNumberColumnFilter",
            "filterParams": {"buttons": ["reset", "apply"], "closeOnApply": True},
        },
    }
    grid_options["autoSizeStrategy"] = {"type": "fitCellContents"}

    # Additional grid options outside builder
    grid_options.update(
        {
            "suppressColumnVirtualisation": True,
            "domLayout": "normal",  # Use 'normal' with explicit height for sticky headers
            "enableCellTextSelection": False,  # Enable text selection at grid level
        }
    )

    return grid_options


# --- Custom CSS --- (Can also be defined here)
CUSTOM_CSS = {
    ".ag-header-cell.ag-right-aligned-header .ag-cell-label-container": {
        "flex-direction": "row-reverse !important"
    },
    ".ag-header-cell.ag-right-aligned-header .ag-header-cell-text": {
        "text-align": "end !important"
    },
    ".ag-header-cell.ag-right-aligned-header .ag-header-cell-label": {
        "flex-direction": "row !important"
    },
}
