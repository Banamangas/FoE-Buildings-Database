import pandas as pd

from foe_buildings.ui.export import to_csv_bytes


def _df():
    return pd.DataFrame({"name": ["A"], "Weighted Efficiency": [1234.5]})


def test_french_csv_uses_semicolon_and_decimal_comma():
    text = to_csv_bytes(_df(), "fr").decode("utf-8-sig")
    assert text.splitlines() == ["name;Weighted Efficiency", "A;1234,5"]


def test_english_csv_uses_comma_and_decimal_point():
    text = to_csv_bytes(_df(), "en").decode("utf-8-sig")
    assert text.splitlines() == ["name,Weighted Efficiency", "A,1234.5"]


def test_csv_starts_with_utf8_bom_for_excel():
    assert to_csv_bytes(_df(), "en").startswith(b"\xef\xbb\xbf")
