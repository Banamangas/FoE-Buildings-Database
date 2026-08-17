from foe_buildings.ui.tooltip import format_range, format_time, percent_suffix


def test_format_time_seconds():
    assert format_time(45) == "45s"


def test_format_time_minutes():
    assert format_time(125) == "2m 5s"


def test_format_time_hours():
    assert format_time(3665) == "1h 1m 5s"


def test_format_time_days():
    assert format_time(90061) == "1d 1h 1m 1s"


def test_format_time_zero():
    assert format_time(0) == "0s"


def test_format_range_equal():
    assert format_range(10, 10) == "10"


def test_format_range_different():
    assert format_range(10, 20) == "10 - 20"


def test_percent_suffix_normal():
    assert percent_suffix("att_boost_attacker") == "%"


def test_percent_suffix_special():
    assert percent_suffix("guild_raids_action_points_collection") == ""
