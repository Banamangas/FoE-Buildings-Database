from unittest.mock import patch

from foe_buildings.data import loader


def test_load_building_entity_lookup_returns_dict():
    with patch.object(loader, "_make_request") as mock_make_request:
        mock_make_request.return_value = {"B1": {"name": "Building One"}}
        result = loader.load_building_entity_lookup()
        assert result == {"B1": {"name": "Building One"}}
        mock_make_request.assert_called_once_with(
            "/data/download/building_entity_lookup.json",
            fatal=False,
            timeout=loader._ENTITY_LOOKUP_TIMEOUT,
        )


def test_clear_cache_invalidates_building_entity_lookup():
    with patch.object(loader.load_building_entity_lookup, "clear") as mock_clear:
        loader.clear_cache()
        mock_clear.assert_called_once_with()
