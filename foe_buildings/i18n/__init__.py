import json
import os
from functools import lru_cache
from typing import Dict
from re import sub

from foe_buildings.config import ERAS_DICT, logger
from foe_buildings.config import TRANSLATIONS_PATH

# --- Language Definitions ---
LANGUAGES = {
    "English": "en",
    "Français": "fr",
    # Add more languages as needed
}


# --- Translation Data Loading ---
# Use cache to load JSONs only once per session
@lru_cache(maxsize=len(LANGUAGES) * 3)  # Cache size based on languages * file types
def _load_translation_file(file_path: str) -> Dict:
    """Loads a single JSON translation file."""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading/parsing translation file {file_path}: {e}")
    return {}


def get_translation_dict(namespace: str, lang_code: str) -> Dict:
    """Gets the translation dictionary for a given namespace and language."""
    primary_path = f"{TRANSLATIONS_PATH}/{lang_code}/{namespace}.json"
    primary_dict = _load_translation_file(primary_path)

    if primary_dict:  # Return immediately if primary found and non-empty
        return primary_dict

    # Fallback to English if primary not found or empty
    if lang_code != "en":
        fallback_path = f"{TRANSLATIONS_PATH}/en/{namespace}.json"
        fallback_dict = _load_translation_file(fallback_path)
        if fallback_dict:
            return fallback_dict

    logger.warning(
        f"Translation namespace '{namespace}' not found for '{lang_code}' or fallback 'en'."
    )
    return {}


# --- Main UI Text Translations ---
# Load all main UI translations at once (could be done lazily if needed)
ALL_UI_TRANSLATIONS = {
    lang_code: get_translation_dict("ui", lang_code) for lang_code in LANGUAGES.values()
}


def get_text(key: str, lang_code: str) -> str:
    """Gets translated UI text for a given key and language code."""
    # Assumes UI translations are in a single 'ui.json' per language
    return ALL_UI_TRANSLATIONS.get(lang_code, {}).get(
        key, ALL_UI_TRANSLATIONS.get("en", {}).get(key, key)
    )  # Fallback to English, then key


# --- Column Name Translations ---
# Load all column translations
ALL_COLUMN_TRANSLATIONS = {
    lang_code: get_translation_dict("columns", lang_code)
    for lang_code in LANGUAGES.values()
}


def translate_column(col: str, lang_code: str) -> str:
    """Translates a DataFrame column name."""
    return ALL_COLUMN_TRANSLATIONS.get(lang_code, {}).get(
        col, ALL_COLUMN_TRANSLATIONS.get("en", {}).get(col, col)
    )


# --- Building Name Translations ---
# Load all building name translations
ALL_BUILDING_NAME_TRANSLATIONS = {
    lang_code: get_translation_dict("building_names", lang_code).get(
        "building_names", {}
    )
    for lang_code in LANGUAGES.values()
}

TO_BE_TRANSLATED_BUILDING_NAMES = {lang_code: {} for lang_code in LANGUAGES.values()}


def translate_building_name(name: str, lang_code: str) -> str:
    """Translates a building name using pre-loaded dictionaries."""
    translated_name = ALL_BUILDING_NAME_TRANSLATIONS.get(lang_code, {}).get(name)
    if (
        translated_name and translated_name != name
    ):  # Check if translation exists and is different
        return translated_name

    # Fallback to English if primary failed
    if lang_code != "en":
        en_translated_name = ALL_BUILDING_NAME_TRANSLATIONS.get("en", {}).get(name)
        if en_translated_name and en_translated_name != name:
            return en_translated_name
        if name not in TO_BE_TRANSLATED_BUILDING_NAMES[lang_code]:
            TO_BE_TRANSLATED_BUILDING_NAMES[lang_code][name] = name

    return name  # Return original if no valid translation found


# --- Event Translations ---
# Load all event translations
ALL_EVENT_TRANSLATIONS = {
    lang_code: get_translation_dict("events", lang_code)
    for lang_code in LANGUAGES.values()
}


def translate_event_key(event_key: str, lang_code: str) -> str:
    """Translate an event key using pre-loaded dictionaries."""
    return ALL_EVENT_TRANSLATIONS.get(lang_code, {}).get(
        event_key, ALL_EVENT_TRANSLATIONS.get("en", {}).get(event_key, event_key)
    )


# --- Era Translations ---
# Load all era translations
ALL_ERA_TRANSLATIONS = {
    lang_code: get_translation_dict("eras", lang_code)
    for lang_code in LANGUAGES.values()
}


def translate_era_key(era_key: str, lang_code: str) -> str:
    """Translate an era key using pre-loaded dictionaries and ERAS_DICT fallback."""
    # 1. Try specific language JSON
    translated_name = ALL_ERA_TRANSLATIONS.get(lang_code, {}).get(era_key)
    if translated_name and translated_name != era_key:
        return translated_name

    # 2. Try English JSON (if not already English)
    if lang_code != "en":
        en_translated_name = ALL_ERA_TRANSLATIONS.get("en", {}).get(era_key)
        if en_translated_name and en_translated_name != era_key:
            return en_translated_name

    # 3. Try hardcoded ERAS_DICT (English names)
    english_fallback = ERAS_DICT.get(era_key)
    if english_fallback:
        return english_fallback

    # 4. Return original key
    logger.warning(
        f"Could not translate era key '{era_key}' for lang '{lang_code}'. Returning key."
    )
    return era_key


def translate_yesno_key(yesno_key: str, lang_code: str) -> str:
    """Translate a composite production-description string into the target language.

    The API returns strings like "Yes collections", "No 3 days", "Military Rare".
    Each regex substitution targets a specific token position (prefix or suffix) so
    that only the expected token is replaced, not accidental occurrences mid-string.
    Tokens not listed here are returned unchanged (graceful degradation).
    """
    result = yesno_key
    result = sub("^No", get_text("No", lang_code), result)
    result = sub("^Yes", get_text("Yes", lang_code), result)
    result = sub("collections$", get_text("collections", lang_code), result)
    result = sub("days$", get_text("days", lang_code), result)
    result = sub("^Military", get_text("Military", lang_code), result)
    result = sub("Any rarity$", get_text("Any rarity", lang_code), result)
    result = sub("Common$", get_text("Common", lang_code), result)
    result = sub("Uncommon$", get_text("Uncommon", lang_code), result)
    result = sub("Rare$", get_text("Rare", lang_code), result)

    return result


# --- Generic Translation with Variables (Example, needs specific implementation if used) ---
# Placeholder - Adapt original logic if needed, using loaded dicts
# def get_localized_text_with_vars(key, lang_code, **variables):
#     # ... adapt original logic using get_translation_dict ...
#     pass
