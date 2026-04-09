import logging
from pathlib import Path

# --- Logging Setup ---
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s - %(filename)s - %(lineno)d",
)
logger = logging.getLogger(__name__)

# --- File Paths ---
ASSETS_PATH = "assets"
TRANSLATIONS_PATH = str(Path(__file__).parents[1] / "i18n" / "locales")
APP_ICON = "assets/icons/icon.png"

# --- API Configuration ---
# Set these in .streamlit/secrets.toml:
#   [foe_api]
#   url = "https://your-subdomain.duckdns.org"
#   key = "foe_your_api_key_here"


def get_api_config() -> tuple:
    """Get API URL and key from Streamlit secrets."""
    import streamlit as st

    try:
        api_url = st.secrets["foe_api"]["url"]
        api_key = st.secrets["foe_api"]["key"]
        return api_url.rstrip("/"), api_key
    except KeyError:
        st.error(
            "API configuration not found in secrets. Please configure foe_api.url and foe_api.key in .streamlit/secrets.toml"
        )
        st.stop()
