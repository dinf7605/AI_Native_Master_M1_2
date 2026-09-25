"""OpenAI 호환 Chat Completions 호출. 게이트웨이 오류는 도메인 예외(LLMRequestError)로 바꾼다."""

import logging
from functools import lru_cache
from typing import Protocol

import openai
from openai import OpenAI

from app.config import OpenAISettings
from app.errors import LLMRequestError

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 60


class LLMClient(Protocol):
    model: str

    def complete(self, messages: list[dict[str, str]]) -> str: ...


class OpenAIChatClient:
    def __init__(self, settings: OpenAISettings) -> None:
        self.model = settings.model
        self._max_completion_tokens = settings.max_completion_tokens
        self._client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            max_retries=1,
        )

    def complete(self, messages: list[dict[str, str]]) -> str:
        try:
            # gpt-5 계열은 max_tokens 대신 max_completion_tokens를 쓴다.
            # 코디세이 게이트웨이는 reasoning_effort를 지원하지 않으므로 넘기지 않는다.
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=self._max_completion_tokens,
            )
        except openai.APIError as e:
            # 요청 정보(키 포함 가능)는 남기지 않고 오류 종류와 상태코드만 기록한다.
            logger.warning(
                "LLM request failed: %s (status=%s)", type(e).__name__, getattr(e, "status_code", None)
            )
            raise LLMRequestError("AI 응답을 받지 못했습니다. 잠시 후 다시 시도하세요.") from e

        content = response.choices[0].message.content if response.choices else None
        if not content or not content.strip():
            raise LLMRequestError("AI가 빈 응답을 반환했습니다. 다시 시도하세요.")
        return content.strip()


@lru_cache(maxsize=4)
def create_llm_client(settings: OpenAISettings) -> OpenAIChatClient:
    """설정이 같으면 클라이언트(HTTP 연결 풀)를 재사용한다."""
    return OpenAIChatClient(settings)
