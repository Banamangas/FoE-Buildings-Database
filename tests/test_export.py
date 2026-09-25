import pandas as pd

from foe_buildings.ui.export import to_csv_bytes, to_xlsx_bytes


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


def test_xlsx_keeps_numbers_numeric():
    from io import BytesIO

    import openpyxl

    sheet = openpyxl.load_workbook(BytesIO(to_xlsx_bytes(_df()))).active
    assert [c.value for c in sheet[1]] == ["name", "Weighted Efficiency"]
    assert sheet["B2"].value == 1234.5
    assert sheet["B2"].data_type == "n"
