from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.data import DataCreate


def test_valid_payload_is_parsed_and_memo_trimmed():
    payload = DataCreate(date="2026-09-25", value=1370.5, memo="  메모  ")

    assert payload.date == date(2026, 9, 25)
    assert payload.value == 1370.5
    assert payload.memo == "메모"


def test_memo_defaults_to_empty_string():
    assert DataCreate(date="2026-09-25", value=1370.5).memo == ""


@pytest.mark.parametrize("bad_date", ["2026-13-01", "25-09-2026", "yesterday", ""])
def test_invalid_date_is_rejected(bad_date):
    with pytest.raises(ValidationError):
        DataCreate(date=bad_date, value=1370.5)


@pytest.mark.parametrize("bad_value", [0, -1.5, "abc", float("nan"), float("inf")])
def test_non_positive_or_non_finite_value_is_rejected(bad_value):
    with pytest.raises(ValidationError):
        DataCreate(date="2026-09-25", value=bad_value)


def test_memo_longer_than_200_chars_is_rejected():
    with pytest.raises(ValidationError):
        DataCreate(date="2026-09-25", value=1370.5, memo="가" * 201)


def test_unknown_field_is_rejected():
    with pytest.raises(ValidationError):
        DataCreate(date="2026-09-25", value=1370.5, currency="USD")


def test_missing_required_fields_are_rejected():
    with pytest.raises(ValidationError):
        DataCreate(memo="값 없음")
