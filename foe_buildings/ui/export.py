import pandas as pd

# (field separator, decimal separator) per UI language. Excel parses CSVs with
# the OS locale's list/decimal separators, so they must be paired: a ";" file
# with "." decimals makes European Excel read 12.5 as text or 1.234 as 1234.
_CSV_FORMATS = {
    "fr": (";", ","),
}
_DEFAULT_CSV_FORMAT = (",", ".")


def to_csv_bytes(df: pd.DataFrame, lang_code: str) -> bytes:
    """Serialise ``df`` to an Excel-friendly UTF-8 (with BOM) CSV for ``lang_code``."""
    sep, decimal = _CSV_FORMATS.get(lang_code, _DEFAULT_CSV_FORMAT)
    return df.to_csv(index=False, sep=sep, decimal=decimal).encode("utf-8-sig")
