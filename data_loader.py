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

import logging
from typing import Dict, Any, Optional

import pandas as pd
import requests
import streamlit as st

from config import get_api_config, logger

_API_TIMEOUT = 30  # seconds per request
_PAGE_SIZE = 1000  # max allowed by the API


def _make_request(endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
    """Make an authenticated GET request to the API.

    Args:
        endpoint: Path relative to the API root (e.g. '/buildings').
        params: Optional query parameters.

    Returns:
        Parsed JSON response as a dict.

    Raises:
        Calls st.stop() on authentication or server errors.
    """
    api_url, api_key = get_api_config()
    url = f"{api_url}/{endpoint.lstrip('/')}"
    headers = {"X-API-Key": api_key}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=_API_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code
        if status == 401:
            st.error("Invalid API key. Please check your secrets.toml configuration.")
        elif status == 429:
            retry_after = e.response.headers.get("Retry-After", "unknown")
            st.warning(f"Rate limit reached. Try again in {retry_after}s.")
        elif status == 503:
            st.error("API data not ready. The daily update may still be running — please try again shortly.")
        else:
            st.error(f"API error {status}: {e}")
        st.stop()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to connect to API: {e}")
        st.stop()


@st.cache_data(ttl=82800)  # 23 hours — data updates at most once daily at 18:00
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
        page = _make_request("/buildings", params={"limit": _PAGE_SIZE, "offset": offset})
        if not page or not page.get("buildings"):
            break
        rows.extend(page["buildings"])
        offset += _PAGE_SIZE

    logger.info("Loaded %d building records from API", len(rows))

    df = pd.DataFrame(rows)

    # Optimise dtypes — same categories as the original BuildingAnalyzer
    for col in ['Era', 'Limited', 'Ally room']:
        if col in df.columns:
            df[col] = df[col].astype('category')
    if 'Road' in df.columns:
        df['Road'] = df['Road'].astype(bool)

    return df


@st.cache_data(ttl=82800)
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
        k: v for k, v in data.items()
        if k.startswith("/city/buildings/") and k.endswith(".png") and "/textures/" not in k
    }


def clear_cache():
    """Clear all cached API data. Call this after a known data update."""
    load_and_process_data.clear()
    get_forgehx_data.clear()
    st.success("Cache cleared — data will be refreshed on next load.")
