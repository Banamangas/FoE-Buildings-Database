import streamlit as st
import pandas as pd
import json
import logging
from io import BytesIO
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import config
import translations
import calculations

# Use logger from config
logger = config.logger


def filter_buildings_by_era(df: pd.DataFrame, era_level: int) -> pd.DataFrame:
    """Return rows of df matching the era level, or the full df if era_level is not in ERAS_LEVEL_MAP."""
    era_key = config.ERAS_LEVEL_MAP.get(era_level)
    if era_key is None:
        return df
    return df[df[config.COL_ERA] == era_key]


def render_paste_interface(data_type: str = "", label: str = "", help_text: str = "", placeholder_text: str = "", key: str = "", lang_code: str = "") -> Optional[str]:
    """Render a paste interface using text area with clear instructions.
    
    Args:
        data_type: Type of data being pasted ("tsv" or "json")
        label: Interface label
        help_text: Help text to display
        placeholder_text: Placeholder text for the text area
        key: Unique key for the text area
        
    Returns:
        Pasted data string or None if no data
    """
    st.write(f"**{label}**")
    st.caption(help_text)
    
    # Instructions for the user
    st.info(translations.get_text("paste_instructions_tsv", lang_code))
    
    if data_type == "inventory":
        st.warning(translations.get_text("inventory_warning", lang_code))

    # Text area for pasting
    pasted_data = st.text_area(
        translations.get_text("paste_data_label", lang_code),
        height=120,
        placeholder=placeholder_text,
        key=key,
        help=f"Paste your {data_type.upper()} data here. Use Ctrl+V (Cmd+V on Mac) to paste."
    )
    
    # Process button
    if pasted_data and pasted_data.strip():
        if st.button(translations.get_text("process_data", lang_code), key=f"process_{key}", type="primary"):
            return pasted_data.strip()
    
    return None


def parse_tsv_inventory(tsv_data: str) -> Dict[str, Dict[str, Any]]:
    """Parse TSV inventory data from clipboard with enhanced validation.
    
    Expected format (no headers):
    building_id_1\tquantity_1[\tera_level_1]
    building_id_2\tquantity_2[\tera_level_2]
    
    Args:
        tsv_data: Raw TSV data string
        
    Returns:
        Dictionary mapping unique_key to {building_id, quantity, era_level}
        
    Raises:
        ValueError: If data format is invalid
    """
    if not tsv_data or not tsv_data.strip():
        raise ValueError("Empty inventory data provided")
    
    inventory = {}
    lines = tsv_data.strip().split('\n')
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
            
        # Try different delimiters
        parts = None
        for delimiter in ['\t', ';', ' ']:
            if delimiter in line:
                parts = [part.strip() for part in line.split(delimiter)]
                break
        
        if not parts:
            # Single value on line, skip
            logger.warning(f"Line {line_num}: No delimiter found, skipping: {line}")
            continue
            
        if len(parts) < 2:
            logger.warning(f"Line {line_num}: Invalid format, expected building_id and quantity (and optionally era_level): {line}")
            continue
            
        building_id = parts[0].strip()
        try:
            quantity = float(parts[1].strip())
            
            # Warn about decimal quantities
            if quantity != int(quantity):
                logger.warning(f"Line {line_num}: Decimal quantity {quantity} for {building_id}, converting to {int(quantity)}")
            
            quantity = int(quantity)
            
            # Skip zero quantities
            if quantity == 0:
                continue
                
        except ValueError:
            logger.warning(f"Line {line_num}: Invalid quantity '{parts[1]}' for building {building_id}")
            continue
        
        # Parse era level (optional third column)
        era_level = None
        if len(parts) >= 3:
            try:
                era_level = int(parts[2].strip())
                # Validate era level exists in mapping
                if era_level not in config.ERAS_LEVEL_MAP:
                    logger.warning(f"Line {line_num}: Invalid era level {era_level} for {building_id}, ignoring era")
                    era_level = None
            except ValueError:
                logger.warning(f"Line {line_num}: Invalid era level '{parts[2]}' for building {building_id}, ignoring era")
                era_level = None
        
        # Validate building ID format (basic check)
        if not building_id or len(building_id) < 3:
            logger.warning(f"Line {line_num}: Invalid building ID format: {building_id}")
            continue
            
        # Create unique key with era if provided
        if era_level is not None:
            key = f"{building_id}_{era_level}"
        else:
            key = building_id
            
        # Handle duplicates by summing quantities
        if key in inventory:
            old_quantity = inventory[key]['quantity']
            inventory[key]['quantity'] += quantity
            logger.warning(f"Line {line_num}: Duplicate building ID '{building_id}'. Adding {quantity} to existing {old_quantity} = {inventory[key]['quantity']}")
        else:
            inventory[key] = {
                'building_id': building_id,
                'quantity': quantity,
                'era_level': era_level
            }
    
    if not inventory:
        raise ValueError("No valid building entries found in inventory data")
        
    logger.info(f"Successfully parsed {len(inventory)} unique building entries from inventory")
    return inventory


def parse_tsv_city(tsv_data: str) -> Dict[str, Dict[str, Any]]:
    """Parse TSV city data from clipboard with enhanced validation.
    
    Expected format (no headers):
    building_id_1\tera_level_1\tquantity_1
    building_id_2\tera_level_2\tquantity_2
    
    Args:
        tsv_data: Raw TSV data string
        
    Returns:
        Dictionary mapping unique_key to {building_id, quantity, era_level}
        
    Raises:
        ValueError: If data format is invalid
    """
    if not tsv_data or not tsv_data.strip():
        raise ValueError("Empty city data provided")
    
    logger.info("Starting TSV city data parsing")
    
    city_data = {}
    lines = tsv_data.strip().split('\n')
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
            
        # Try different delimiters
        parts = None
        for delimiter in ['\t', ';', ' ']:
            if delimiter in line:
                parts = [part.strip() for part in line.split(delimiter)]
                break
        
        if not parts:
            # Single value on line, skip
            logger.warning(f"Line {line_num}: No delimiter found, skipping: {line}")
            continue
            
        # City format requires exactly 3 columns: building_id, era_level, quantity
        if len(parts) != 3:
            logger.warning(f"Line {line_num}: City format requires 3 columns (building_id, era_level, quantity), got {len(parts)}: {line}")
            continue
            
        building_id = parts[0].strip()
        
        # Parse era level (required for city format)
        try:
            era_level = int(parts[1].strip())
            # Validate era level exists in mapping
            if era_level not in config.ERAS_LEVEL_MAP:
                logger.warning(f"Line {line_num}: Invalid era level {era_level} for {building_id}, skipping line")
                continue
        except ValueError:
            logger.warning(f"Line {line_num}: Invalid era level '{parts[1]}' for building {building_id}, skipping line")
            continue
            
        # Parse quantity
        try:
            quantity = float(parts[2].strip())
            
            # Warn about decimal quantities
            if quantity != int(quantity):
                logger.warning(f"Line {line_num}: Decimal quantity {quantity} for {building_id}, converting to {int(quantity)}")
            
            quantity = int(quantity)
            
            # Skip zero quantities
            if quantity == 0:
                continue
                
        except ValueError:
            logger.warning(f"Line {line_num}: Invalid quantity '{parts[2]}' for building {building_id}, skipping line")
            continue
        
        # Validate building ID format (basic check)
        if not building_id or len(building_id) < 3:
            logger.warning(f"Line {line_num}: Invalid building ID format: {building_id}")
            continue
            
        # Create unique key with era
        unique_key = f"{building_id}_{era_level}"
            
        # Handle duplicates by summing quantities
        if unique_key in city_data:
            old_quantity = city_data[unique_key]['quantity']
            city_data[unique_key]['quantity'] += quantity
            logger.warning(f"Line {line_num}: Duplicate building ID '{building_id}' at era {era_level}. Adding {quantity} to existing {old_quantity} = {city_data[unique_key]['quantity']}")
        else:
            city_data[unique_key] = {
                'building_id': building_id,
                'quantity': quantity,
                'era_level': era_level
            }
    
    if not city_data:
        raise ValueError("No valid building entries found in city data")
    
    # Log summary statistics
    total_buildings = sum(data['quantity'] for data in city_data.values())
    unique_buildings = len(city_data)
    
    # Log building type distribution
    building_type_stats = {}
    for data in city_data.values():
        building_id = data['building_id']
        if '_' in building_id:
            prefix = building_id.split('_')[0] + '_'
            building_type_stats[prefix] = building_type_stats.get(prefix, 0) + 1
    
    logger.info(f"TSV city parsing completed: {unique_buildings} unique buildings, {total_buildings} total buildings")
    logger.info(f"Building type distribution: {building_type_stats}")
    
    return city_data


def validate_building_data(building_data: Dict[str, Any], df_original: pd.DataFrame) -> Tuple[Dict[str, Any], List[str]]:
    """Validate building data against the database and return valid entries with unmatched log.
    
    Args:
        building_data: Dictionary of unique_key -> building data with era info
        df_original: Original buildings dataframe
        
    Returns:
        Tuple of (valid_building_data, unmatched_building_ids)
    """
    # Get all building IDs from the database
    db_building_ids = set(df_original['id'].unique()) if 'id' in df_original.columns else set()
    
    valid_data = {}
    unmatched_ids = []
    
    for unique_key, data in building_data.items():
        # Extract building_id from data structure
        if isinstance(data, dict):
            building_id = data.get('building_id', unique_key)
        else:
            # Handle legacy format where data might be just quantity
            building_id = unique_key
        
        # For era-specific entries, check the base building ID
        base_building_id = building_id.split('_')[0] + '_' + '_'.join(building_id.split('_')[1:-1]) if '_' in building_id and building_id.count('_') > 1 else building_id
        
        if building_id in db_building_ids:
            valid_data[unique_key] = data
        else:
            unmatched_ids.append(building_id)
            logger.info(f"Building ID '{building_id}' (from key '{unique_key}') not found in database")
    
    # Log unmatched IDs to backend file
    if unmatched_ids:
        log_unmatched_buildings(unmatched_ids)
    
    return valid_data, unmatched_ids


def log_unmatched_buildings(unmatched_ids: List[str]) -> None:
    """Log unmatched building IDs to a backend file.
    
    Args:
        unmatched_ids: List of building IDs that weren't found in the database
    """
    try:
        import os
        
        # Create logs directory if it doesn't exist
        logs_dir = "logs"
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        
        # Create log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": st.session_state.get("session_id", "unknown"),
            "unmatched_building_ids": unmatched_ids,
            "count": len(unmatched_ids),
            "source": "city_analysis"
        }
        
        # Write to daily log file
        log_filename = f"unmatched_buildings_{datetime.now().strftime('%Y-%m-%d')}.log"
        log_filepath = os.path.join(logs_dir, log_filename)
        
        with open(log_filepath, "a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(log_entry) + "\n")
        
        # Also log to application logger
        logger.info(f"Logged {len(unmatched_ids)} unmatched building IDs to {log_filepath}")
        logger.debug(f"Unmatched building IDs: {unmatched_ids}")
        
    except Exception as e:
        logger.error(f"Failed to log unmatched building IDs: {e}")
        # Fallback to just application logging
        logger.info(f"Unmatched building IDs (fallback): {unmatched_ids}")


def merge_with_database(building_data: Dict[str, Any], df_original: pd.DataFrame, 
                       source_type: str, user_weights: Dict[str, float], 
                       user_context: Dict[str, float], user_boosts: Dict[str, float],
                       lang_code: str) -> pd.DataFrame:
    """Merge building data with the database and calculate efficiency with enhanced validation.
    
    Args:
        building_data: Valid building data from parse functions
        df_original: Original buildings dataframe
        source_type: "inventory" or "city"
        user_weights: User weight configuration
        user_context: User context configuration
        user_boosts: User boost configuration
        lang_code: Language code
        
    Returns:
        Filtered dataframe with quantity and source columns
    """
    logger.info(f"Starting data merge for {source_type} with {len(building_data)} building types")
    
    # Create a list to store the building entries
    building_entries = []
    total_quantity = 0
    processed_buildings = 0
    
    for unique_key, data in building_data.items():
        # Extract building_id and era information
        if isinstance(data, dict) and 'building_id' in data:
            building_id = data['building_id']
            era_level = data.get('era_level')
        else:
            # Handle legacy format
            building_id = unique_key
            era_level = None
            
        # Get building data from database
        building_rows = df_original[df_original['id'] == building_id]
        
        if building_rows.empty:
            logger.warning(f"Building ID '{building_id}' not found in database during merge (should have been filtered)")
            continue  # Should not happen as we validated, but safety check
        
        # Filter by era if specified
        if era_level is not None:
            filtered = filter_buildings_by_era(building_rows, era_level)
            if filtered.empty:
                logger.warning(f"Building '{building_id}' not found in era level {era_level} ({config.ERAS_LEVEL_MAP.get(era_level)})")
                continue
            building_rows = filtered

        # Handle multiple eras for the same building (if no era specified)
        for _, building_row in building_rows.iterrows():
            building_entry = building_row.copy()
            
            # Add quantity and source columns
            if source_type == "inventory":
                if isinstance(data, dict):
                    quantity = data.get('quantity', data.get('count', 1))
                else:
                    quantity = data  # data is just the quantity for inventory
                building_entry['Quantity'] = quantity
                building_entry['Source'] = translations.get_text("inventory", lang_code)
                total_quantity += quantity
            else:  # city
                quantity = data.get('count', 1) if isinstance(data, dict) else 1
                building_entry['Quantity'] = quantity
                building_entry['Source'] = translations.get_text("city", lang_code)
                total_quantity += quantity
                
                # Store coordinates as metadata (not displayed but available for future features)
                if isinstance(data, dict) and 'coordinates' in data and data['coordinates']:
                    building_entry['_coordinates'] = data['coordinates']  # Private field
            
            building_entries.append(building_entry)
            processed_buildings += 1
    
    if not building_entries:
        logger.warning("No valid building entries created during merge")
        return pd.DataFrame()
    
    logger.info(f"Created {len(building_entries)} building entries from {processed_buildings} database matches")
    
    # Create DataFrame from building entries
    result_df = pd.DataFrame(building_entries)
    
    # Ensure required columns exist
    if 'Weighted Efficiency' not in result_df.columns:
        result_df['Weighted Efficiency'] = 0.0
    if 'Total Score' not in result_df.columns:
        result_df['Total Score'] = 0.0
    
    # Calculate efficiency if weights are provided
    weights_active = any(w > 0 for w in user_weights.values()) if user_weights else False
    logger.info(f"Merge function: Weights active: {weights_active}, User weights: {user_weights}")
    
    if weights_active:
        logger.info("Applying efficiency calculations to merged data")
        try:
            result_df = calculations.calculate_direct_weighted_efficiency(
                df=result_df,
                user_weights=user_weights,
                user_context=user_context,
                user_boosts=user_boosts
            )
            logger.info("Efficiency calculations completed successfully")
        except Exception as e:
            logger.error(f"Error applying efficiency calculations: {e}")
            # Continue without efficiency calculations
    else:
        logger.info("No active weights - skipping efficiency calculations")
    
    # Log summary statistics
    unique_buildings = result_df['name'].nunique() if 'name' in result_df.columns else 0
    logger.info(f"Merge completed: {len(result_df)} rows, {unique_buildings} unique buildings, {total_quantity} total items")
    
    return result_df


def save_to_session_state(data: Dict[str, Any], key: str) -> None:
    """Save data to browser localStorage via session state (Streamlit-compatible persistence).
    
    Args:
        data: Data to save
        key: Storage key
    """
    try:
        # Use Streamlit session state for persistence instead of localStorage
        # This provides better compatibility and reliability
        storage_key = f"city_analysis_{key}"
        st.session_state[storage_key] = data
        logger.info(f"Saved data to session storage: {storage_key}")
    except Exception as e:
        logger.error(f"Failed to save to session storage: {e}")


def load_from_session_state(key: str) -> Optional[Dict[str, Any]]:
    """Load data from browser localStorage via session state (Streamlit-compatible persistence).
    
    Args:
        key: Storage key
        
    Returns:
        Loaded data or None if not found
    """
    try:
        storage_key = f"city_analysis_{key}"
        data = st.session_state.get(storage_key)
        if data:
            logger.info(f"Loaded data from session storage: {storage_key}")
        return data
    except Exception as e:
        logger.error(f"Failed to load from session storage: {e}")
        return None


def show_toast_notification(message: str, notification_type: str = "success") -> None:
    """Show a toast notification to the user.
    
    Args:
        message: Message to display
        notification_type: Type of notification ("success", "error", "warning", "info")
    """
    try:
        # Map notification types to Streamlit methods and icons
        notification_map = {
            "success": (st.success, "✅"),
            "error": (st.error, "❌"),
            "warning": (st.warning, "⚠️"),
            "info": (st.info, "ℹ️")
        }
        
        if notification_type in notification_map:
            method, icon = notification_map[notification_type]
            method(f"{icon} {message}")
        else:
            st.info(f"ℹ️ {message}")
            
        logger.info(f"Toast notification ({notification_type}): {message}")
    except Exception as e:
        logger.error(f"Failed to show toast notification: {e}")
        # Fallback to simple text display
        st.write(f"{notification_type.upper()}: {message}")


def clear_all_data() -> None:
    """Clear all imported city analysis data from session state.
    
    Returns:
        None
    """
    try:
        # Clear session state data
        keys_to_clear = [
            'imported_inventory',
            'imported_city',
            'city_analysis_inventory_data',
            'city_analysis_city_data',
            'city_analysis_merged_data'
        ]
        
        cleared_count = 0
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
                cleared_count += 1
        
        logger.info(f"Cleared {cleared_count} city analysis data keys from session state")
        return cleared_count
        
    except Exception as e:
        logger.error(f"Failed to clear data: {e}")
        return 0


def render_city_analysis_tab(df_original: pd.DataFrame, user_weights: Dict[str, float], 
                           user_context: Dict[str, float], user_boosts: Dict[str, float],
                           selected_columns: List[str], lang_code: str) -> None:
    """Render the main City Analysis tab interface.
    
    Args:
        df_original: Original buildings dataframe
        user_weights: User weight configuration (from session state)
        user_context: User context configuration (from session state)
        user_boosts: User boost configuration (from session state)
        selected_columns: Selected columns for display
        lang_code: Language code
    """
    st.header(translations.get_text("city_analysis", lang_code))
    st.markdown(translations.get_text("city_analysis_help", lang_code))
    
    # Initialize session state for imported data and session tracking
    if 'session_id' not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())[:8]  # Short session ID
    
    if 'imported_inventory' not in st.session_state:
        st.session_state.imported_inventory = None
    if 'imported_city' not in st.session_state:
        st.session_state.imported_city = None
    
    # Load persisted data on startup
    if st.session_state.imported_inventory is None:
        st.session_state.imported_inventory = load_from_session_state("inventory_data")
    if st.session_state.imported_city is None:
        st.session_state.imported_city = load_from_session_state("city_data")
    
    # Import section
    st.subheader("📥 " + translations.get_text("import_data", lang_code))
    
    # Create columns for the import interfaces
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        # TSV Inventory Import
        with st.expander(translations.get_text("how_to_import_inventory_data", lang_code)):
            st.write(translations.get_text("inventory_analysis_help_import", lang_code))
            st.code(r"""copy(Object.values(MainParser.Inventory).filter((t=>"InventoryItem"===t.__class__&&"BuildingItemPayload"===t.item.__class__&&t.item.cityEntityId&&["A_","D_","G_","L_","M_","P_","R_","T_","W_","Z_"].some((e=>t.item.cityEntityId.startsWith(e))))).sort(((t,e)=>t.name.localeCompare(e.name))).map((t=>`${t.item.cityEntityId}\t${t.inStock}\t${t.item.level}`)).join("\n"));""", language="javascript", wrap_lines=False)

        inventory_data = render_paste_interface(
            data_type="inventory",
            label=translations.get_text("paste_tsv_inventory", lang_code),
            help_text=translations.get_text("tsv_inventory_help", lang_code),
            placeholder_text="W_MultiAge_SummerBonus20\t5\t22\nW_MultiAge_WinterBonus21\t3\t21",
            key="tsv_inventory_paste",
            lang_code=lang_code
        )
        
        if inventory_data:
            try:
                parsed_inventory = parse_tsv_inventory(inventory_data)
                valid_inventory, unmatched_ids = validate_building_data(parsed_inventory, df_original)
                
                if valid_inventory:
                    st.session_state.imported_inventory = valid_inventory
                    # Save to persistence
                    save_to_session_state(valid_inventory, "inventory_data")
                    
                    # Calculate totals for success message
                    total_quantity = sum(data.get('quantity', data) if isinstance(data, dict) else data for data in valid_inventory.values())
                    
                    # Show success notification
                    success_msg = f"{translations.get_text('import_success', lang_code)}: {len(valid_inventory)} {translations.get_text('unique_buildings', lang_code)}, {total_quantity} {translations.get_text('total_buildings', lang_code)}"
                    show_toast_notification(success_msg, "success")
                    
                    if unmatched_ids:
                        # Log unmatched IDs for backend analysis
                        log_unmatched_buildings(unmatched_ids)
                        warning_msg = f"{len(unmatched_ids)} building IDs not found in database"
                        show_toast_notification(warning_msg, "warning")
                else:
                    show_toast_notification("No valid buildings found in inventory data", "error")
                    
            except ValueError as e:
                show_toast_notification(f"{translations.get_text('data_corrupted', lang_code)}: {str(e)}", "error")
    
    with col2:
        # TSV City Import
        with st.expander(translations.get_text("how_to_import_city_data", lang_code)):
            st.write(translations.get_text("city_analysis_help_import", lang_code))
            st.code(r"""copy(Object.entries(Object.values(MainParser.CityMapData).filter(({cityentity_id:c})=>['A_','D_','G_','L_','M_','P_','R_','T_','W_','Z_'].some(p=>c.startsWith(p))).map(({cityentity_id:c,level:l})=>`${((MainParser.CityEntities[c]||{}).cityentity_id||c).replace(/\s*[-–—]\s+Niveau\s*(\d+)/gi,' $1').replace(/ [-–—]\s+Actief/gi,'').replace(/\s*[-–—]\s+Niv\.\s*(\d+)/gi,' $1').replace(/ [-–—]\s+Actief/gi,'').replace(/\s*[-–—]\s+Lv\.\s*(\d+)/gi,' $1').replace(/ [-–—]\s+Active/gi,'').replace(/\s*[-–—]\s+taso\s*(\d+)/gi,' $1').replace(/ [-–—]\s+(aktiivinen|käytössä)/gi,'').replace(/\s*[-–—]\s+Niv\.\s*(\d+)/gi,' $1').replace(/ [-–—]\s+actif/gi,'').replace(/\s*[-–—]\s+St\.\s*(\d+)/gi,' $1').replace(/ [-–—]\s+Aktiv/gi,'').replace(/\s*[-–—]\s+Επ\.\s*(\d+)/gi,' $1').replace(/ [-–—]\s+(Ενεργός|Ενεργό|Ενεργή)/gi,'').replace(/\s*[-–—]\s+szint:?\s*(\d+)/gi,' $1').replace(/\s*[-–—]\s+(\d+)\. szint/gi,' $1').replace(/ [-–—]\s+Aktív/gi,'').replace(/\s*[-–—]\s+Liv\.\s*(\d+)/gi,' $1').replace(/ [-–—]\s+Attivo/gi,'').replace(/\s*[-–—]\s+poz\.\s*(\d+)/gi,' $1').replace(/ [-–—]\s+aktywna/gi,'').replace(/\s*[-–—]\s+(Nv\.|Nivel)\s*(\d+)/gi,' $2').replace(/ [-–—]\s+(Ativo|Ativa)/gi,'').replace(/\s*[-–—]\s+Nvl\s*(\d+)/gi,' $1').replace(/ [-–—]\s+(Ativo|Ativa)/gi,'').replace(/\s*[-–—]\s+ур\.\s*(\d+)/gi,' $1').replace(/ [-–—]\s+(активно|активн.|включено|вкл.)/gi,'').replace(/\s*[-–—]\s+(Nv|Nvl)\.\s*(\d+)/gi,' $2').replace(/ [-–—]\s+Activo/gi,'')}\t${l||'N/A'}`).reduce((a,n)=>(a[n]=(a[n]||0)+1,a),{})).sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>`${k}\t${v}`).join('\n'));""", language="javascript", wrap_lines=False)
        
        city_data = render_paste_interface(
            data_type="city",
            label=translations.get_text("paste_tsv_city", lang_code),
            help_text=translations.get_text("tsv_city_help", lang_code),
            placeholder_text="W_MultiAge_SummerBonus20\t21\t5\nW_MultiAge_WinterBonus21\t21\t3",
            key="tsv_city_paste",
            lang_code=lang_code
        )
        
        if city_data:
            try:
                parsed_city = parse_tsv_city(city_data)
                # Validate using the new format that includes era information
                valid_city, unmatched_ids = validate_building_data(parsed_city, df_original)
                
                if valid_city:
                    st.session_state.imported_city = parsed_city
                    # Save to persistence
                    save_to_session_state(parsed_city, "city_data")
                    
                    # Show success notification
                    total_buildings = sum(data['quantity'] for data in parsed_city.values())
                    success_msg = f"{translations.get_text('import_success', lang_code)}: {len(valid_city)} {translations.get_text('unique_buildings', lang_code)}, {total_buildings} {translations.get_text('total_buildings', lang_code)}"
                    show_toast_notification(success_msg, "success")
                    
                    if unmatched_ids:
                        # Log unmatched IDs for backend analysis
                        log_unmatched_buildings(unmatched_ids)
                        warning_msg = f"{len(unmatched_ids)} building IDs not found in database"
                        show_toast_notification(warning_msg, "warning")
                else:
                    show_toast_notification("No valid buildings found in city data", "error")
                    
            except ValueError as e:
                show_toast_notification(f"{translations.get_text('data_corrupted', lang_code)}: {str(e)}", "error")
    
    with col3:
        # Clear data section
        st.write(f"**{translations.get_text('clear_all', lang_code)}**")
        st.caption(translations.get_text("clear_data_help", lang_code))
        
        if st.button(translations.get_text("clear_all", lang_code), type="secondary", key="clear_all_data"):
            # Clear session state
            st.session_state.imported_inventory = None
            st.session_state.imported_city = None
            
            # Clear persistence
            cleared_count = clear_all_data()
            
            # Show success notification
            show_toast_notification(translations.get_text("data_cleared", lang_code), "success")
            st.rerun()
    
    # Display imported data if available
    if st.session_state.imported_inventory or st.session_state.imported_city:
        st.markdown("---")
        st.subheader("📊 " + translations.get_text("imported_data_analysis", lang_code))
        
        # Combine all imported data using era-specific keys
        all_building_data = {}
        
        if st.session_state.imported_inventory:
            for unique_key, data in st.session_state.imported_inventory.items():
                quantity = data.get('quantity', data) if isinstance(data, dict) else data
                all_building_data[unique_key] = {
                    'inventory_quantity': quantity,
                    'city_quantity': 0,
                    'building_id': data.get('building_id', unique_key) if isinstance(data, dict) else unique_key,
                    'era_level': data.get('era_level') if isinstance(data, dict) else None
                }
        
        if st.session_state.imported_city:
            for unique_key, data in st.session_state.imported_city.items():
                if unique_key not in all_building_data:
                    all_building_data[unique_key] = {
                        'inventory_quantity': 0,
                        'city_quantity': data.get('quantity', 1),
                        'building_id': data.get('building_id', unique_key),
                        'era_level': data.get('era_level')
                    }
                else:
                    all_building_data[unique_key]['city_quantity'] = data.get('quantity', 1)
        
        # Build merged display dataframe using merge_with_database for both sources
        merged_parts = []
        if st.session_state.imported_inventory:
            merged_inventory = merge_with_database(
                st.session_state.imported_inventory, df_original,
                source_type="inventory",
                user_weights=user_weights, user_context=user_context,
                user_boosts=user_boosts, lang_code=lang_code
            )
            if not merged_inventory.empty:
                merged_parts.append(merged_inventory)
        if st.session_state.imported_city:
            merged_city = merge_with_database(
                st.session_state.imported_city, df_original,
                source_type="city",
                user_weights=user_weights, user_context=user_context,
                user_boosts=user_boosts, lang_code=lang_code
            )
            if not merged_city.empty:
                merged_parts.append(merged_city)

        df_imported = pd.concat(merged_parts, ignore_index=True) if merged_parts else pd.DataFrame()

        if not df_imported.empty:
            # Save processed data to persistence
            save_to_session_state(all_building_data, "merged_data")
            
            # Always show only owned buildings from imported data
            df_display = df_imported.copy()
            filter_info = f"Showing {len(df_display)} buildings from your imported data"
            
            # Display filter information
            st.info(f"📊 {filter_info}")
            
            # Buildings Table
            st.subheader("🏗️ " + translations.get_text("buildings_table", lang_code))
            
            # Define required columns in specific order: Name, Event, Era, Source, Quantity, Weighted Efficiency, Total Score
            required_columns_order = ['name', 'Event', 'Translated Era', 'Source', 'Quantity', 'Weighted Efficiency', 'Total Score']
            
            # Start with required columns that exist in the dataframe
            ordered_columns = []
            for col in required_columns_order:
                if col in df_display.columns:
                    ordered_columns.append(col)
            
            # Add other selected columns (excluding those already added)
            for col in selected_columns:
                if col in df_display.columns and col not in ordered_columns:
                    ordered_columns.append(col)
            
            available_columns = ordered_columns
            
            # Create display dataframe with selected columns
            if available_columns:
                df_table = df_display[available_columns].copy()
                
                # Sort by name for better organization
                df_table = df_table.sort_values(by='name', ascending=True)
                
                # Configure AgGrid for city analysis using existing ui_components
                from st_aggrid import AgGrid, AgGridTheme, ColumnsAutoSizeMode
                import ui_components
                
                # Calculate efficiency range for heatmap (if Weighted Efficiency exists)
                eff_min = df_table['Weighted Efficiency'].min() if 'Weighted Efficiency' in df_table.columns and not df_table.empty else 0
                eff_max = df_table['Weighted Efficiency'].max() if 'Weighted Efficiency' in df_table.columns and not df_table.empty else 0
                if pd.isna(eff_min): eff_min = 0
                if pd.isna(eff_max): eff_max = 0
                
                # Use the existing build_grid_options function
                grid_options = ui_components.build_grid_options(
                    df_display=df_table,
                    lang_code=lang_code,
                    use_icons=True,  # Always use icons in city analysis
                    show_labels=False,  # Keep labels minimal for cleaner look
                    enable_heatmap=True,  # Enable heatmap for efficiency visualization
                    eff_min=eff_min,
                    eff_max=eff_max
                )
                
                # Display the grid
                grid_response = AgGrid(
                    df_table,
                    gridOptions=grid_options,
                    custom_css=ui_components.CUSTOM_CSS,
                    allow_unsafe_jscode=True,
                    theme=AgGridTheme.STREAMLIT,
                    height=600,
                    width='100%',
                    columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
                    key="city_analysis_grid"
                )
                
                # Export functionality
                st.markdown("---")
                st.subheader("📤 " + translations.get_text("export_results", lang_code))
                
                # Prepare export data with translations
                df_export = df_table.copy()
                column_translation_map = {
                    col: translations.translate_column(col, lang_code) 
                    for col in df_export.columns
                }
                df_export.rename(columns=column_translation_map, inplace=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # CSV Export
                    buffer_csv = BytesIO()
                    buffer_csv.write('\ufeff'.encode('utf-8'))  # UTF-8 BOM
                    csv_string = df_export.to_csv(index=False, sep=";")
                    buffer_csv.write(csv_string.encode('utf-8'))
                    buffer_csv.seek(0)
                    csv_data = buffer_csv.getvalue()
                    
                    st.download_button(
                        label=translations.get_text("export_csv", lang_code),
                        data=csv_data,
                        file_name=f"city_analysis_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv",
                        mime="text/csv; charset=utf-8",
                        key="export_city_csv"
                    )
                
                with col2:
                    # JSON Export
                    json_string = df_export.to_json(orient="records", date_format="iso", force_ascii=False)
                    json_data = json_string.encode('utf-8')
                    
                    st.download_button(
                        label=translations.get_text("export_json", lang_code),
                        data=json_data,
                        file_name=f"city_analysis_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json",
                        mime="application/json; charset=utf-8",
                        key="export_city_json"
                    )
                
            else:
                st.warning(translations.get_text("no_columns_selected", lang_code))
                
        else:
            st.info(translations.get_text("no_valid_buildings_found", lang_code))
    
    else:
        st.info(translations.get_text("no_data_imported", lang_code)) 