import pytest

from app.config import (
    DEFAULT_ALLOWED_ORIGINS,
    DEFAULT_MAX_COMPLETION_TOKENS,
    DEFAULT_OPENAI_MODEL,
    get_allowed_origins,
    get_openai_settings,
    load_firebase_credentials,
)
from app.errors import DatabaseUnavailableError, LLMUnavailableError


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


@pytest.fixture
def openai_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    for name in ("OPENAI_BASE_URL", "OPENAI_MODEL", "OPENAI_MAX_COMPLETION_TOKENS"):
        monkeypatch.delenv(name, raising=False)


def test_openai_settings_defaults(openai_env):
    settings = get_openai_settings()

    assert settings.api_key == "test-key"
    assert settings.base_url is None
    assert settings.model == DEFAULT_OPENAI_MODEL
    assert settings.max_completion_tokens == DEFAULT_MAX_COMPLETION_TOKENS


def test_openai_settings_from_env(openai_env, monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", " https://copa.codyssey.kr/v1 ")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.5")
    monkeypatch.setenv("OPENAI_MAX_COMPLETION_TOKENS", "300")

    settings = get_openai_settings()

    assert settings.base_url == "https://copa.codyssey.kr/v1"
    assert settings.model == "gpt-5.5"
    assert settings.max_completion_tokens == 300


def test_missing_openai_key_raises(openai_env, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY")

    with pytest.raises(LLMUnavailableError):
        get_openai_settings()


@pytest.mark.parametrize("raw", ["abc", "0", "-5"])
def test_invalid_max_completion_tokens_raises(openai_env, monkeypatch, raw):
    monkeypatch.setenv("OPENAI_MAX_COMPLETION_TOKENS", raw)

    with pytest.raises(LLMUnavailableError):
        get_openai_settings()
