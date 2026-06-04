from app.utils.datetime import clean_text, parse_seace_datetime


def test_parse_seace_datetime_with_peru_timezone() -> None:
    parsed = parse_seace_datetime("04/05/2026 16:55:00")

    assert parsed is not None
    assert parsed.year == 2026
    assert parsed.month == 5
    assert parsed.day == 4
    assert parsed.hour == 16
    assert parsed.tzinfo is not None


def test_parse_seace_datetime_returns_none_for_malformed_value() -> None:
    assert parse_seace_datetime("not-a-date") is None


def test_clean_text_normalizes_whitespace_and_null_bytes() -> None:
    assert clean_text("  CONTRATACIÓN\x00   DEL   SERVICIO  ") == "CONTRATACIÓN DEL SERVICIO"
