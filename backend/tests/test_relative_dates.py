from datetime import date

from app.calle_adapter import resolve_relative_weekdays


def test_friday_is_resolved_to_concrete_date():
    assert resolve_relative_weekdays("Move it to Friday afternoon", date(2026, 9, 13)) == "Move it to Friday 18 September 2026 afternoon"


def test_explicit_weekday_date_is_not_duplicated():
    text = "Move it to Friday 18 September 2026 afternoon"
    assert resolve_relative_weekdays(text, date(2026, 9, 13)) == text


def test_same_day_weekday_resolves_to_next_week():
    assert resolve_relative_weekdays("Friday afternoon", date(2026, 9, 18)) == "Friday 25 September 2026 afternoon"
