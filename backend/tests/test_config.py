import pytest

from app.config import DEFAULT_ALLOWED_ORIGINS, get_allowed_origins, load_firebase_credentials
from app.errors import DatabaseUnavailableError


@pytest.fixture
def no_firebase_env(monkeypatch):
    monkeypatch.delenv("FIREBASE_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.delenv("FIREBASE_SERVICE_ACCOUNT_PATH", raising=False)


def test_allowed_origins_are_trimmed_and_empty_entries_dropped(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", " https://a.vercel.app , ,https://b.example.com/ ")

    assert get_allowed_origins() == ["https://a.vercel.app", "https://b.example.com"]


def test_allowed_origins_default_when_unset(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)

    assert get_allowed_origins() == DEFAULT_ALLOWED_ORIGINS.split(",")


def test_json_credentials_take_priority_over_path(monkeypatch, no_firebase_env, tmp_path):
    key_file = tmp_path / "key.json"
    key_file.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("FIREBASE_SERVICE_ACCOUNT_JSON", '{"type": "service_account"}')
    monkeypatch.setenv("FIREBASE_SERVICE_ACCOUNT_PATH", str(key_file))

    assert load_firebase_credentials() == {"type": "service_account"}


def test_invalid_json_credentials_raise(monkeypatch, no_firebase_env):
    monkeypatch.setenv("FIREBASE_SERVICE_ACCOUNT_JSON", "{not json")

    with pytest.raises(DatabaseUnavailableError):
        load_firebase_credentials()


def test_path_credentials_return_existing_file(monkeypatch, no_firebase_env, tmp_path):
    key_file = tmp_path / "key.json"
    key_file.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("FIREBASE_SERVICE_ACCOUNT_PATH", str(key_file))

    assert load_firebase_credentials() == str(key_file)


def test_missing_key_file_raises(monkeypatch, no_firebase_env):
    monkeypatch.setenv("FIREBASE_SERVICE_ACCOUNT_PATH", "does-not-exist.json")

    with pytest.raises(DatabaseUnavailableError):
        load_firebase_credentials()


def test_no_credentials_configured_raises(no_firebase_env):
    with pytest.raises(DatabaseUnavailableError):
        load_firebase_credentials()
