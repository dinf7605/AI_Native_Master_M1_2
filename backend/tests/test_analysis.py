from datetime import date, timedelta

import pytest

from app.services.analysis import build_summary


def make_records(values, start=date(2026, 1, 1)):
    """연속된 날짜에 values를 순서대로 배치한 레코드 목록을 만든다."""
    return [
        {"date": (start + timedelta(days=i)).isoformat(), "value": v}
        for i, v in enumerate(values)
    ]


def test_empty_input_returns_zero_count_summary():
    summary = build_summary([])

    assert summary["count"] == 0
    assert summary["start_date"] is None
    assert summary["end_date"] is None
    assert summary["mean"] is None
    assert summary["min"] is None
    assert summary["max"] is None
    assert summary["latest"] is None
    assert summary["trend"] == {
        "direction": "insufficient_data",
        "change_pct": None,
        "window": None,
    }


def test_unsorted_input_uses_chronological_period_and_latest():
    records = [
        {"date": "2026-01-03", "value": 30.0},
        {"date": "2026-01-01", "value": 10.0},
        {"date": "2026-01-02", "value": 20.0},
    ]

    summary = build_summary(records)

    assert summary["start_date"] == "2026-01-01"
    assert summary["end_date"] == "2026-01-03"
    assert summary["latest"] == {"value": 30.0, "date": "2026-01-03"}


def test_basic_statistics_with_dates():
    records = make_records([1400.123, 1450.5, 1380.0, 1420.0])

    summary = build_summary(records)

    assert summary["count"] == 4
    assert summary["mean"] == pytest.approx(1412.66)
    assert summary["min"] == {"value": 1380.0, "date": "2026-01-03"}
    assert summary["max"] == {"value": 1450.5, "date": "2026-01-02"}


def test_trend_increase_when_recent_window_mean_rises():
    summary = build_summary(make_records([100.0] * 7 + [102.0] * 7))

    assert summary["trend"]["direction"] == "increase"
    assert summary["trend"]["change_pct"] == pytest.approx(2.0)
    assert summary["trend"]["window"] == 7


def test_trend_decrease_when_recent_window_mean_falls():
    summary = build_summary(make_records([100.0] * 7 + [98.0] * 7))

    assert summary["trend"]["direction"] == "decrease"
    assert summary["trend"]["change_pct"] == pytest.approx(-2.0)


def test_trend_flat_when_change_below_threshold():
    summary = build_summary(make_records([100.0] * 7 + [100.3] * 7))

    assert summary["trend"]["direction"] == "flat"
    assert summary["trend"]["change_pct"] == pytest.approx(0.3)


def test_trend_only_uses_last_two_windows():
    # 앞쪽의 큰 값은 추세 계산 구간(마지막 14개) 밖이므로 무시되어야 한다.
    summary = build_summary(make_records([500.0] * 10 + [100.0] * 7 + [102.0] * 7))

    assert summary["trend"]["direction"] == "increase"
    assert summary["trend"]["change_pct"] == pytest.approx(2.0)


def test_trend_window_shrinks_when_few_points():
    summary = build_summary(make_records([100.0, 100.0, 110.0, 110.0]))

    assert summary["trend"]["window"] == 2
    assert summary["trend"]["direction"] == "increase"
    assert summary["trend"]["change_pct"] == pytest.approx(10.0)


def test_single_point_has_insufficient_trend():
    summary = build_summary(make_records([1400.0]))

    assert summary["count"] == 1
    assert summary["latest"] == {"value": 1400.0, "date": "2026-01-01"}
    assert summary["trend"]["direction"] == "insufficient_data"


def test_custom_window_and_threshold():
    records = make_records([100.0] * 3 + [100.8] * 3)

    summary = build_summary(records, window=3, flat_threshold_pct=1.0)

    assert summary["trend"]["window"] == 3
    assert summary["trend"]["direction"] == "flat"
