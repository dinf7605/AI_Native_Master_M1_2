from app.prompts import build_system_prompt
from app.services.analysis import build_summary

SUMMARY = {
    "count": 146,
    "start_date": "2026-03-02",
    "end_date": "2026-09-24",
    "mean": 1466.6,
    "min": {"value": 1336.2, "date": "2026-09-09"},
    "max": {"value": 1558.09, "date": "2026-07-01"},
    "latest": {"value": 1368.6, "date": "2026-09-24"},
    "trend": {"direction": "increase", "change_pct": 1.94, "window": 7},
}


def test_prompt_contains_every_summary_figure():
    prompt = build_system_prompt(SUMMARY)

    for expected in [
        "2026-03-02 ~ 2026-09-24",
        "146개",
        "1,466.60",
        "1,336.20",
        "2026-09-09",
        "1,558.09",
        "2026-07-01",
        "1,368.60",
        "증가",
        "+1.94%",
        "최근 7개",
    ]:
        assert expected in prompt


def test_prompt_contains_guardrail_rules():
    prompt = build_system_prompt(SUMMARY)

    assert "추측하지" in prompt
    assert "투자" in prompt
    assert "한국어" in prompt


def test_prompt_translates_trend_directions():
    for direction, label in [("decrease", "감소"), ("flat", "유지")]:
        summary = {**SUMMARY, "trend": {"direction": direction, "change_pct": -0.2, "window": 7}}

        assert label in build_system_prompt(summary)


def test_prompt_handles_empty_data():
    prompt = build_system_prompt(build_summary([]))

    assert "저장된 데이터가 없습니다" in prompt
    assert "None" not in prompt


def test_prompt_handles_insufficient_trend():
    prompt = build_system_prompt(build_summary([{"date": "2026-09-24", "value": 1368.6}]))

    assert "판단할 수 없음" in prompt
    assert "None" not in prompt
