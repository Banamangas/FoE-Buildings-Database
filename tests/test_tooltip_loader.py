from unittest.mock import patch

from foe_buildings.data import loader


def test_load_forgehx_asset_map_keeps_all_asset_paths():
    payload = {
        "/shared/icons/money.png": "money-hash",
        "/shared/icons/icon_unique_building.png": "trait-hash",
        "/city/buildings/W_SS_Test.png": "building-hash",
    }
    with patch.object(loader, "_make_request", return_value=payload) as request:
        result = loader.load_forgehx_asset_map.__wrapped__()

    assert result == payload
    request.assert_called_once_with("/data/forgehx", fatal=False)


def test_load_forgehx_asset_map_rejects_non_mapping_payload():
    with patch.object(loader, "_make_request", return_value=["bad"]):
        assert loader.load_forgehx_asset_map.__wrapped__() == {}


def test_get_forgehx_data_remains_building_only():
    payload = {
        "/shared/icons/money.png": "money-hash",
        "/city/buildings/W_SS_Test.png": "building-hash",
        "/city/buildings/textures/W_Test.png": "texture-hash",
    }
    with patch.object(loader, "load_forgehx_asset_map", return_value=payload):
        result = loader.get_forgehx_data.__wrapped__()

    assert result == {"/city/buildings/W_SS_Test.png": "building-hash"}


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


def test_load_building_entity_lookup_normalizes_entity_list():
    entity = {"id": "B1", "name": "Building One"}
    with patch.object(loader, "_make_request") as mock_make_request:
        mock_make_request.return_value = [entity]

        result = loader.load_building_entity_lookup.__wrapped__()

    assert result == {"B1": entity}


def test_load_building_entity_lookup_strips_entity_identifier_prefix():
    entity = {"identifier": "building_entity_B1", "components": {}}
    with patch.object(loader, "_make_request") as mock_make_request:
        mock_make_request.return_value = [entity]

        result = loader.load_building_entity_lookup.__wrapped__()

    assert result == {"B1": entity}


def test_clear_cache_invalidates_building_entity_lookup():
    with patch.object(loader.load_building_entity_lookup, "clear") as mock_clear:
        loader.clear_cache()
        mock_clear.assert_called_once_with()


def test_clear_cache_invalidates_full_forgehx_map():
    with patch.object(loader.load_forgehx_asset_map, "clear") as clear:
        loader.clear_cache()
    clear.assert_called_once_with()
