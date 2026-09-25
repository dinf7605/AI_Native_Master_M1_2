import pytest
from fastapi.testclient import TestClient

from app.config import get_allowed_origins
from app.dependencies import get_data_repository
from main import app
from tests.fakes import InMemoryDataRepository


@pytest.fixture
def repo():
    return InMemoryDataRepository()


@pytest.fixture
def client(repo):
    app.dependency_overrides[get_data_repository] = lambda: repo
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def post(client, day, value, memo=""):
    return client.post("/api/data", json={"date": day, "value": value, "memo": memo})


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_returns_201_with_item(client):
    response = post(client, "2026-09-25", 1370.5, "직접 입력")

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["date"] == "2026-09-25"
    assert body["value"] == 1370.5
    assert body["memo"] == "직접 입력"


def test_create_duplicate_date_returns_409(client):
    post(client, "2026-09-25", 1370.5)

    response = post(client, "2026-09-25", 1380.0)

    assert response.status_code == 409
    assert "2026-09-25" in response.json()["detail"]


def test_create_invalid_payload_returns_422(client):
    response = post(client, "2026-09-25", -5)

    assert response.status_code == 422


def test_list_returns_items_sorted_by_date(client):
    post(client, "2026-09-25", 3.0)
    post(client, "2026-09-23", 1.0)
    post(client, "2026-09-24", 2.0)

    response = client.get("/api/data")

    assert response.status_code == 200
    assert [item["date"] for item in response.json()] == ["2026-09-23", "2026-09-24", "2026-09-25"]


def test_update_replaces_item(client):
    item_id = post(client, "2026-09-25", 1370.5).json()["id"]

    response = client.put(
        f"/api/data/{item_id}", json={"date": "2026-09-25", "value": 1375.0, "memo": "수정"}
    )

    assert response.status_code == 200
    assert response.json() == {"id": item_id, "date": "2026-09-25", "value": 1375.0, "memo": "수정"}


def test_update_missing_item_returns_404(client):
    response = client.put("/api/data/unknown", json={"date": "2026-09-25", "value": 1.0})

    assert response.status_code == 404


def test_update_to_date_of_another_item_returns_409(client):
    post(client, "2026-09-24", 1.0)
    item_id = post(client, "2026-09-25", 2.0).json()["id"]

    response = client.put(f"/api/data/{item_id}", json={"date": "2026-09-24", "value": 2.0})

    assert response.status_code == 409


def test_update_keeping_own_date_is_allowed(client):
    item_id = post(client, "2026-09-25", 2.0).json()["id"]

    response = client.put(f"/api/data/{item_id}", json={"date": "2026-09-25", "value": 3.0})

    assert response.status_code == 200


def test_delete_removes_item(client):
    item_id = post(client, "2026-09-25", 1370.5).json()["id"]

    response = client.delete(f"/api/data/{item_id}")

    assert response.status_code == 200
    assert client.get("/api/data").json() == []


def test_delete_missing_item_returns_404(client):
    assert client.delete("/api/data/unknown").status_code == 404


def test_invalid_id_format_returns_422(client):
    assert client.delete("/api/data/bad.id").status_code == 422


def test_summary_reflects_current_data(client):
    assert client.get("/api/data/summary").json()["count"] == 0

    post(client, "2026-09-23", 100.0)
    post(client, "2026-09-24", 110.0)
    response = client.get("/api/data/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert body["start_date"] == "2026-09-23"
    assert body["mean"] == 105.0
    assert body["latest"] == {"value": 110.0, "date": "2026-09-24"}
    assert body["trend"]["direction"] == "increase"


def test_cors_preflight_allows_configured_origin(client):
    origin = get_allowed_origins()[0]

    response = client.options(
        "/api/data",
        headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
    )

    assert response.headers.get("access-control-allow-origin") == origin


def test_cors_rejects_unknown_origin(client):
    response = client.get("/api/data", headers={"Origin": "https://evil.example.com"})

    assert "access-control-allow-origin" not in response.headers


def test_database_unavailable_returns_503(client):
    def broken_repository():
        from app.errors import DatabaseUnavailableError

        raise DatabaseUnavailableError("Firebase 서비스 계정 설정이 없습니다.")

    app.dependency_overrides[get_data_repository] = broken_repository

    response = client.get("/api/data")

    assert response.status_code == 503
    assert "Firebase" in response.json()["detail"]
