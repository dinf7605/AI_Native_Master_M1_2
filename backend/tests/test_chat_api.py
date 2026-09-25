from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_conversation_repository, get_data_repository, get_llm_client
from app.errors import LLMRequestError
from main import app
from tests.fakes import FakeLLMClient, InMemoryConversationRepository, InMemoryDataRepository


@pytest.fixture
def data_repo():
    repo = InMemoryDataRepository()
    for day, value in [("2026-09-22", 1356.15), ("2026-09-23", 1365.35), ("2026-09-24", 1368.6)]:
        repo.create({"date": day, "value": value, "memo": ""})
    return repo


@pytest.fixture
def conversation_repo():
    return InMemoryConversationRepository()


@pytest.fixture
def llm():
    return FakeLLMClient()


@pytest.fixture
def client(data_repo, conversation_repo, llm):
    app.dependency_overrides[get_data_repository] = lambda: data_repo
    app.dependency_overrides[get_conversation_repository] = lambda: conversation_repo
    app.dependency_overrides[get_llm_client] = lambda: llm
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def ask(client, message, conversation_id=None):
    body = {"message": message}
    if conversation_id:
        body["conversation_id"] = conversation_id
    return client.post("/api/chat", json=body)


def seed_conversation(repo, message_count):
    messages = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"메시지 {i}"}
        for i in range(message_count)
    ]
    stamp = datetime(2026, 9, 24, tzinfo=timezone.utc)
    return repo.create(
        {"title": "기존 대화", "messages": messages, "message_count": message_count,
         "created_at": stamp, "updated_at": stamp}
    )["id"]


def test_new_chat_returns_reply_and_saves_conversation(client, conversation_repo, llm):
    response = ask(client, "최근 환율 추세가 어때?")

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == llm.reply
    assert body["model"] == "fake-model"
    assert body["title"] == "최근 환율 추세가 어때?"
    assert body["summary"]["count"] == 3

    saved = conversation_repo.get(body["conversation_id"])
    assert saved["messages"] == [
        {"role": "user", "content": "최근 환율 추세가 어때?"},
        {"role": "assistant", "content": llm.reply},
    ]
    assert saved["message_count"] == 2


def test_summary_is_injected_into_system_prompt(client, llm):
    ask(client, "평균이 얼마야?")

    messages = llm.calls[0]
    assert messages[0]["role"] == "system"
    assert "1,363.37" in messages[0]["content"]  # 3개 값의 평균
    assert "2026-09-22 ~ 2026-09-24" in messages[0]["content"]
    assert messages[-1] == {"role": "user", "content": "평균이 얼마야?"}


def test_follow_up_sends_history_and_appends_to_conversation(client, conversation_repo, llm):
    conversation_id = ask(client, "첫 질문").json()["conversation_id"]

    response = ask(client, "이어서 질문", conversation_id)

    assert response.status_code == 200
    assert response.json()["conversation_id"] == conversation_id
    assert [m["content"] for m in llm.calls[1][1:]] == ["첫 질문", llm.reply, "이어서 질문"]
    saved = conversation_repo.get(conversation_id)
    assert saved["message_count"] == 4
    assert saved["messages"][-2] == {"role": "user", "content": "이어서 질문"}


def test_history_sent_to_llm_is_limited_to_last_10_messages(client, conversation_repo, llm):
    conversation_id = seed_conversation(conversation_repo, 20)

    ask(client, "새 질문", conversation_id)

    sent = llm.calls[0]
    assert len(sent) == 1 + 10 + 1
    assert sent[1]["content"] == "메시지 10"


def test_unknown_conversation_returns_404_without_calling_llm(client, llm):
    response = ask(client, "질문", "unknown")

    assert response.status_code == 404
    assert llm.calls == []


def test_full_conversation_returns_409_without_calling_llm(client, conversation_repo, llm):
    conversation_id = seed_conversation(conversation_repo, 49)

    response = ask(client, "질문", conversation_id)

    assert response.status_code == 409
    assert llm.calls == []
    assert conversation_repo.get(conversation_id)["message_count"] == 49


@pytest.mark.parametrize(
    "body",
    [
        {"message": "   "},
        {"message": "가" * 1001},
        {"message": "질문", "conversation_id": "bad.id"},
        {"message": "질문", "model": "gpt-5.5"},
        {},
    ],
    ids=["blank", "too-long", "bad-conversation-id", "unknown-field", "missing-message"],
)
def test_invalid_request_returns_422(client, llm, body):
    assert client.post("/api/chat", json=body).status_code == 422
    assert llm.calls == []


def test_llm_failure_returns_502_and_saves_nothing(client, conversation_repo, llm):
    llm.error = LLMRequestError("AI 응답을 받지 못했습니다.")

    response = ask(client, "질문")

    assert response.status_code == 502
    assert conversation_repo.list_summaries() == []


def test_missing_openai_key_returns_503(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    del app.dependency_overrides[get_llm_client]

    response = ask(client, "질문")

    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]
