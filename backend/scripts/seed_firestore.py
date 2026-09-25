"""CSV(date,value,memo)를 Firestore `data` 컬렉션에 적재한다.

이미 Firestore에 있는 date는 건너뛰므로 여러 번 실행해도 중복이 생기지 않는다.
각 행은 API와 같은 Pydantic 모델(DataCreate)로 검증한다.

사용법 (backend/ 에서):
    python scripts/seed_firestore.py --dry-run
    python scripts/seed_firestore.py
"""

import argparse
import csv
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from google.api_core.exceptions import GoogleAPIError  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from app.errors import DatabaseUnavailableError  # noqa: E402
from app.firebase import get_firestore_client  # noqa: E402
from app.repositories.data_repository import FirestoreDataRepository  # noqa: E402
from app.schemas.data import DataCreate  # noqa: E402
from app.services.data_service import to_fields  # noqa: E402

DEFAULT_CSV = BACKEND_DIR / "data" / "usdkrw.csv"


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def read_rows(csv_path: Path) -> list[dict]:
    if not csv_path.is_file():
        fail(f"CSV not found: {csv_path}")

    rows: dict[str, dict] = {}
    with csv_path.open(encoding="utf-8", newline="") as f:
        for line_no, row in enumerate(csv.DictReader(f), start=2):
            try:
                fields = to_fields(DataCreate(**row))
            except ValidationError as e:
                fail(f"{csv_path.name} line {line_no}: {e.errors()[0]['msg']}")
            rows.setdefault(fields["date"], fields)
    return list(rows.values())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="적재할 CSV 경로")
    parser.add_argument("--dry-run", action="store_true", help="Firestore에 쓰지 않고 결과만 출력")
    args = parser.parse_args()

    rows = read_rows(args.csv)

    try:
        repo = FirestoreDataRepository(get_firestore_client())
        existing = {item["date"] for item in repo.list_all()}
        new_rows = [fields for fields in rows if fields["date"] not in existing]
        prefix = "[dry-run] would add" if args.dry_run else "added"
        if not args.dry_run:
            repo.create_many(new_rows)
    except DatabaseUnavailableError as e:
        fail(e.message)
    except GoogleAPIError as e:
        fail(f"Firestore request failed: {type(e).__name__}")

    print(f"{prefix} {len(new_rows)}, skipped {len(rows) - len(new_rows)} (already in Firestore)")


if __name__ == "__main__":
    main()
