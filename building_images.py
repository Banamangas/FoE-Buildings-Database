"""
Building Images

Resolves building asset IDs to their full CDN image URLs using the
ForgeHX hash map fetched from the VPS API (/data/forgehx).

Image URL format:
    https://foezz.innogamescdn.com/assets/city/buildings/W_SS_MultiAge_XXX-{hash}.png
"""

import logging
from typing import Dict, Optional

import streamlit as st

import config
import data_loader

logger = config.logger

FORGEHX_IMAGE_BASE = "https://foezz.innogamescdn.com/assets"


def _ss_key(asset_id: str) -> str:
    """Convert a building asset ID to its _SS_ ForgeHX path key.

    Example: 'W_MultiAge_FOO' -> '/city/buildings/W_SS_MultiAge_FOO.png'
    """
    i = asset_id.index("_")
    return f"/city/buildings/{asset_id[:i]}_SS_{asset_id[i + 1:]}.png"


class BuildingImageManager:
    """Resolves building asset IDs to CDN image URLs via the ForgeHX map."""

    def __init__(self):
        # Loaded lazily on first lookup; get_forgehx_data() is @st.cache_data
        # so this is effectively free after the first call.
        self._forgehx: Dict[str, str] = {}
        self._loaded = False

    def _ensure_loaded(self):
        if not self._loaded:
            self._forgehx = data_loader.get_forgehx_data()
            self._loaded = True

    def get_building_image_url(self, asset_id: str) -> Optional[str]:
        """Return the full CDN URL for a building's screenshot image, or None."""
        if not asset_id:
            return None
        self._ensure_loaded()
        try:
            key = _ss_key(asset_id)
            h = self._forgehx.get(key)
            if h:
                return f"{FORGEHX_IMAGE_BASE}{key[:-4]}-{h}.png"
        except ValueError:
            pass
        return None

    def has_image(self, asset_id: str) -> bool:
        """Return True if a screenshot image exists for this asset ID."""
        if not asset_id:
            return False
        self._ensure_loaded()
        try:
            return _ss_key(asset_id) in self._forgehx
        except ValueError:
            return False

    def get_all_mappings(self) -> Dict[str, str]:
        """Return all asset_id -> image URL mappings."""
        self._ensure_loaded()
        result = {}
        for key, h in self._forgehx.items():
            # Reverse the key back to an asset_id is non-trivial; return URL map keyed by path
            result[key] = f"{FORGEHX_IMAGE_BASE}{key[:-4]}-{h}.png"
        return result

    def get_stats(self) -> Dict[str, int]:
        self._ensure_loaded()
        return {"total_images": len(self._forgehx)}


@st.cache_resource
def get_image_manager() -> BuildingImageManager:
    """Return the singleton BuildingImageManager (cached for the app lifetime)."""
    return BuildingImageManager()


def get_building_image_url(asset_id: str) -> Optional[str]:
    """Convenience wrapper: get image URL for a building asset ID."""
    return get_image_manager().get_building_image_url(asset_id)


def has_building_image(asset_id: str) -> bool:
    """Convenience wrapper: check if a building has an image."""
    return get_image_manager().has_image(asset_id)
