"""시계열 데이터 요약 계산.

`/api/data/summary` 응답과 채팅 시스템 프롬프트 주입이 공통으로 사용하는 순수 함수다.
Firestore/OpenAI에 의존하지 않으므로 네트워크 없이 테스트할 수 있다.
"""

from collections.abc import Iterable, Mapping
from statistics import fmean
from typing import Any

DEFAULT_WINDOW = 7
DEFAULT_FLAT_THRESHOLD_PCT = 0.5

INSUFFICIENT_TREND = {"direction": "insufficient_data", "change_pct": None, "window": None}


def build_summary(
    records: Iterable[Mapping[str, Any]],
    window: int = DEFAULT_WINDOW,
    flat_threshold_pct: float = DEFAULT_FLAT_THRESHOLD_PCT,
) -> dict[str, Any]:
    """(date, value) 레코드 목록으로 기간·개수·기본 통계·최근 추세를 계산한다.

    추세는 최근 `window`개 평균을 그 직전 `window`개 평균과 비교한 변화율(%)로 판정하며,
    |변화율| < `flat_threshold_pct` 이면 "flat"이다. 데이터가 2*window보다 적으면
    window를 count // 2로 줄여 계산한다.
    """
    ordered = sorted(records, key=lambda r: r["date"])

    if not ordered:
        return {
            "count": 0,
            "start_date": None,
            "end_date": None,
            "mean": None,
            "min": None,
            "max": None,
            "latest": None,
            "trend": dict(INSUFFICIENT_TREND),
        }

    values = [float(r["value"]) for r in ordered]

    return {
        "count": len(ordered),
        "start_date": ordered[0]["date"],
        "end_date": ordered[-1]["date"],
        "mean": round(fmean(values), 2),
        "min": _point(min(ordered, key=lambda r: float(r["value"]))),
        "max": _point(max(ordered, key=lambda r: float(r["value"]))),
        "latest": _point(ordered[-1]),
        "trend": _trend(values, window, flat_threshold_pct),
    }


def _point(record: Mapping[str, Any]) -> dict[str, Any]:
    return {"value": round(float(record["value"]), 2), "date": record["date"]}


def _trend(values: list[float], window: int, flat_threshold_pct: float) -> dict[str, Any]:
    effective = min(window, len(values) // 2)
    if effective < 1:
        return dict(INSUFFICIENT_TREND)

    previous_mean = fmean(values[-2 * effective : -effective])
    recent_mean = fmean(values[-effective:])
    if previous_mean == 0:
        return dict(INSUFFICIENT_TREND)

    change_pct = (recent_mean - previous_mean) / abs(previous_mean) * 100

    if abs(change_pct) < flat_threshold_pct:
        direction = "flat"
    elif change_pct > 0:
        direction = "increase"
    else:
        direction = "decrease"

    return {"direction": direction, "change_pct": round(change_pct, 2), "window": effective}
