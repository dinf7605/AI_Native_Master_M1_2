"""환경 변수 설정. 애플리케이션은 환경 변수를 이 모듈을 통해서만 읽는다.

로컬에서는 backend/.env를 읽고, 배포(Render)에서는 플랫폼 환경 변수를 그대로 쓴다.
키 값 자체는 로그나 오류 메시지에 절대 포함하지 않는다.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.errors import DatabaseUnavailableError, LLMUnavailableError

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

DEFAULT_ALLOWED_ORIGINS = "http://localhost:5500,http://127.0.0.1:5500"
DEFAULT_OPENAI_MODEL = "gpt-5.4"
DEFAULT_MAX_COMPLETION_TOKENS = 700


@dataclass(frozen=True)
class OpenAISettings:
    api_key: str = field(repr=False)  # repr/로그에 키가 찍히지 않도록 제외
    base_url: str | None
    model: str
    max_completion_tokens: int


def get_allowed_origins() -> list[str]:
    """ALLOWED_ORIGINS(쉼표 구분)를 CORS 허용 origin 목록으로 변환한다."""
    raw = os.getenv("ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS)
    return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]


def load_firebase_credentials() -> dict[str, Any] | str:
    """서비스 계정 인증 정보를 반환한다.

    FIREBASE_SERVICE_ACCOUNT_JSON(JSON 문자열, 배포용)을 우선 사용하고,
    없으면 FIREBASE_SERVICE_ACCOUNT_PATH(키 파일 경로, 로컬용)를 사용한다.
    """
    raw_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    if raw_json:
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError:
            raise DatabaseUnavailableError(
                "FIREBASE_SERVICE_ACCOUNT_JSON 값이 올바른 JSON이 아닙니다."
            ) from None

    raw_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "").strip()
    if raw_path:
        path = Path(raw_path)
        if not path.is_absolute():
            path = BACKEND_DIR / path
        if not path.is_file():
            raise DatabaseUnavailableError(f"서비스 계정 키 파일을 찾을 수 없습니다: {raw_path}")
        return str(path)

    raise DatabaseUnavailableError(
        "Firebase 서비스 계정 설정이 없습니다. "
        "FIREBASE_SERVICE_ACCOUNT_JSON 또는 FIREBASE_SERVICE_ACCOUNT_PATH를 설정하세요."
    )


def get_openai_settings() -> OpenAISettings:
    """OpenAI(호환) API 설정. OPENAI_BASE_URL을 비우면 OpenAI 공식 API를 쓴다."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise LLMUnavailableError("OPENAI_API_KEY가 설정되지 않았습니다.")

    raw_max = os.getenv("OPENAI_MAX_COMPLETION_TOKENS", "").strip()
    try:
        max_completion_tokens = int(raw_max) if raw_max else DEFAULT_MAX_COMPLETION_TOKENS
    except ValueError:
        max_completion_tokens = 0
    if max_completion_tokens <= 0:
        raise LLMUnavailableError("OPENAI_MAX_COMPLETION_TOKENS는 양의 정수여야 합니다.")

    return OpenAISettings(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL", "").strip() or None,
        model=os.getenv("OPENAI_MODEL", "").strip() or DEFAULT_OPENAI_MODEL,
        max_completion_tokens=max_completion_tokens,
    )
