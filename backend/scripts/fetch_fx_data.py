"""Frankfurter API(ECB 기준환율)에서 USD/KRW 일별 환율을 받아 CSV로 저장한다.

API 키가 필요 없고 표준 라이브러리만 사용한다. 영업일(ECB 고시일) 데이터만 존재하며
주말·공휴일은 보간하지 않는다.

사용법 (backend/ 에서):
    python scripts/fetch_fx_data.py
    python scripts/fetch_fx_data.py --start 2026-03-02 --end 2026-09-24 --summary
"""

import argparse
import csv
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

API_URL = "https://api.frankfurter.dev/v1/{start}..{end}?base=USD&symbols=KRW"
MEMO = "ECB reference rate (Frankfurter)"
MIN_POINTS = 100
DEFAULT_START = "2026-03-02"
DEFAULT_END = "2026-09-24"
DEFAULT_OUTPUT = BACKEND_DIR / "data" / "usdkrw.csv"


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def fetch_rates(start: str, end: str) -> list[dict]:
    url = API_URL.format(start=start, end=end)
    request = urllib.request.Request(url, headers={"User-Agent": "fx-data-ai-chat/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as e:
        fail(f"API returned HTTP {e.code} for {url}")
    except (urllib.error.URLError, TimeoutError) as e:
        fail(f"could not reach {url}: {e}")
    except json.JSONDecodeError:
        fail(f"API response from {url} is not valid JSON")

    rates = payload.get("rates") or {}
    records = [
        {"date": day, "value": daily["KRW"], "memo": MEMO}
        for day, daily in sorted(rates.items())
        if "KRW" in daily
    ]
    if not records:
        fail(f"API returned no KRW rates for {start}..{end}")
    return records


def write_csv(records: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "value", "memo"])
        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", default=DEFAULT_START, help="시작일 YYYY-MM-DD")
    parser.add_argument("--end", default=DEFAULT_END, help="종료일 YYYY-MM-DD")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="CSV 저장 경로")
    parser.add_argument("--summary", action="store_true", help="저장 후 요약 정보 출력")
    args = parser.parse_args()

    records = fetch_rates(args.start, args.end)
    if len(records) < MIN_POINTS:
        fail(f"only {len(records)} points for {args.start}..{args.end}; need >= {MIN_POINTS}")

    write_csv(records, args.output)
    print(f"saved {len(records)} rows to {args.output}")

    if args.summary:
        from app.services.analysis import build_summary

        print(json.dumps(build_summary(records), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
