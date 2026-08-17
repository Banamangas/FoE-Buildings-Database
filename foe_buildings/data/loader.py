"""
Data Loader — VPS API Client

Fetches FOE building data from the VPS REST API instead of parsing
the raw game JSON locally. All parsing and aggregation is handled
server-side; this module is a thin HTTP client with Streamlit caching.

API credentials are read from .streamlit/secrets.toml:
    [foe_api]
    url = "https://your-subdomain.duckdns.org"
    key = "foe_your_api_key_here"
"""

from typing import Dict, Any, Optional

import pandas as pd
import requests
import streamlit as st

from foe_buildings.config import get_api_config, logger

_API_TIMEOUT = 30  # seconds per request
_ENTITY_LOOKUP_TIMEOUT = 120  # seconds for the ~40 MB entity lookup payload
_PAGE_SIZE = 1000  # max page size allowed by the API
_CACHE_TTL = (
    82800  # 23 hours in seconds — data refreshes server-side once daily at ~18:00
)


def _make_request(
    endpoint: str,
    params: Optional[Dict] = None,
    fatal: bool = True,
    timeout: int = _API_TIMEOUT,
) -> Optional[Dict[str, Any]]:
    """Make an authenticated GET request to the API.

    Args:
        endpoint: Path relative to the API root (e.g. '/buildings').
        params: Optional query parameters.
        fatal: When True (default), a failure halts the app via st.stop() —
            used for endpoints the app cannot run without (e.g. /buildings).
            When False, the error is logged and None is returned so the caller
            can degrade gracefully (e.g. optional building-name translations).

    Returns:
        Parsed JSON response as a dict, or None when fatal=False and the
        request failed.
    """
    api_url, api_key = get_api_config()
    url = f"{api_url}/{endpoint.lstrip('/')}"
    headers = {"X-API-Key": api_key}

    try:
        response = requests.get(
            url, headers=headers, params=params, timeout=timeout
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if not fatal:
            logger.warning(f"Non-fatal API error fetching {endpoint}: {e}")
            return None
        status = e.response.status_code
        if status == 401:
            st.error("Invalid API key. Please check your secrets.toml configuration.")
        elif status == 429:
            retry_after = e.response.headers.get("Retry-After", "unknown")
            st.warning(f"Rate limit reached. Try again in {retry_after}s.")
        elif status == 503:
            st.error(
                "API data not ready. The daily update may still be running — please try again shortly."
            )
        else:
            st.error(f"API error {status}: {e}")
        st.stop()
    except requests.exceptions.RequestException as e:
        if not fatal:
            logger.warning(f"Non-fatal connection error fetching {endpoint}: {e}")
            return None
        st.error(f"Failed to connect to API: {e}")
        st.stop()


@st.cache_data(ttl=_CACHE_TTL)
def load_and_process_data() -> pd.DataFrame:
    """Fetch all buildings from the API and return a DataFrame.

    Paginates through the /buildings endpoint until all records are
    retrieved. Result is cached for 23 hours (just under the daily
    update interval) and shared across all active Streamlit sessions.

    Returns:
        DataFrame with one row per building-era combination, columns
        matching the VPS database schema.
    """
    rows = []
    offset = 0

    # First request also tells us the total count
    data = _make_request("/buildings", params={"limit": _PAGE_SIZE, "offset": 0})
    if not data or not data.get("buildings"):
        st.warning("No building data returned by the API.")
        return pd.DataFrame()

    rows.extend(data["buildings"])
    total = data.get("total", len(rows))

    # Fetch remaining pages
    offset = _PAGE_SIZE
    while offset < total:
        page = _make_request(
            "/buildings", params={"limit": _PAGE_SIZE, "offset": offset}
        )
        if not page or not page.get("buildings"):
            break
        rows.extend(page["buildings"])
        offset += _PAGE_SIZE

    logger.info("Loaded %d building records from API", len(rows))

    df = pd.DataFrame(rows)

    # Optimise dtypes — same categories as the original BuildingAnalyzer
    for col in ["Era", "Limited", "Ally room"]:
        if col in df.columns:
            df[col] = df[col].astype("category")
    if "Road" in df.columns:
        df["Road"] = df["Road"].astype(bool)

    return df


@st.cache_data(ttl=_CACHE_TTL)
def get_building_name_translations() -> Dict[str, Dict[str, str]]:
    """Fetch building-name translations keyed by asset_id.

    Endpoint: GET /building-names (X-API-Key auth).
    Returns:
        ``{asset_id: {"en": "...", "fr": "...", ...}, ...}`` — one entry per
        building, mapping each supported language code to its display name.
        Empty dict if the API returned nothing or the request failed (the
        fetch is non-fatal; callers fall back to the on-disk translation JSON).

    Cached for 23 hours (same TTL as ``load_and_process_data``) so building
    names refresh on the same daily cadence as the building data itself.
    """
    data = _make_request("/building-names", fatal=False)
    if not data or not data.get("buildings"):
        return {}
    return data["buildings"]


@st.cache_data(ttl=_CACHE_TTL)
def get_forgehx_data() -> Dict[str, str]:
    """Fetch the ForgeHX image hash map from the API.

    Returns a dict mapping asset paths to their cache-buster hashes,
    filtered to city building images only. Used by building_images.py
    to construct full CDN image URLs.

    Returns:
        Dict of {'/city/buildings/W_SS_XXX.png': 'hash', ...}
    """
    data = _make_request("/data/forgehx")
    if not data:
        return {}
    return {
        k: v
        for k, v in data.items()
        if k.startswith("/city/buildings/")
        and k.endswith(".png")
        and "/textures/" not in k
    }


@st.cache_data(ttl=_CACHE_TTL)
def load_building_entity_lookup() -> Dict[str, Any]:
    """Fetch the raw building entity lookup JSON from the API.

    Returns a dict mapping building ID (e.g. ``W_MultiAge_HAL19A1``) to the
    original game entity dict. Cached for 23 hours to match the daily data
    refresh cadence.

    Returns:
        Dict[str, Any]: empty dict if the request fails or returns nothing.
    """
    data = _make_request(
        "/data/download/building_entity_lookup.json",
        fatal=False,
        timeout=_ENTITY_LOOKUP_TIMEOUT,
    )
    if not data:
        return {}
    return data


def clear_cache():
    """Clear all cached API data. Call this after a known data update."""
    load_and_process_data.clear()
    get_forgehx_data.clear()
    get_building_name_translations.clear()
    load_building_entity_lookup.clear()
    st.success("Cache cleared — data will be refreshed on next load.")
