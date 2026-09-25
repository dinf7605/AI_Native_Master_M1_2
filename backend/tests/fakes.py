"""테스트용 인메모리 repository. Firestore 구현과 같은 메서드를 제공한다."""

from copy import deepcopy
from typing import Any


class InMemoryDataRepository:
    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}
        self._next_id = 1

    def list_all(self) -> list[dict[str, Any]]:
        return sorted((dict(item) for item in self._items.values()), key=lambda r: r["date"])

    def get(self, item_id: str) -> dict[str, Any] | None:
        item = self._items.get(item_id)
        return dict(item) if item else None

    def find_by_date(self, day: str) -> list[dict[str, Any]]:
        return [dict(item) for item in self._items.values() if item["date"] == day]

    def create(self, fields: dict[str, Any]) -> dict[str, Any]:
        item_id = f"id{self._next_id}"
        self._next_id += 1
        self._items[item_id] = {"id": item_id, **fields}
        return dict(self._items[item_id])

    def create_many(self, rows: list[dict[str, Any]]) -> int:
        for fields in rows:
            self.create(fields)
        return len(rows)

    def update(self, item_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        self._items[item_id] = {"id": item_id, **fields}
        return dict(self._items[item_id])

    def delete(self, item_id: str) -> None:
        self._items.pop(item_id, None)


class InMemoryConversationRepository:
    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}
        self._next_id = 1

    def list_summaries(self) -> list[dict[str, Any]]:
        summaries = (
            {key: value for key, value in item.items() if key != "messages"}
            for item in self._items.values()
        )
        return sorted(summaries, key=lambda r: r["updated_at"], reverse=True)

    def get(self, conversation_id: str) -> dict[str, Any] | None:
        item = self._items.get(conversation_id)
        return deepcopy(item) if item else None

    def create(self, fields: dict[str, Any]) -> dict[str, Any]:
        conversation_id = f"conv{self._next_id}"
        self._next_id += 1
        self._items[conversation_id] = {"id": conversation_id, **deepcopy(fields)}
        return deepcopy(self._items[conversation_id])

    def update(self, conversation_id: str, fields: dict[str, Any]) -> None:
        self._items[conversation_id].update(deepcopy(fields))

    def delete(self, conversation_id: str) -> None:
        self._items.pop(conversation_id, None)


class FakeLLMClient:
    """실제 GPT를 호출하지 않는 LLM. 받은 messages를 calls에 기록한다."""

    model = "fake-model"

    def __init__(self, reply: str = "요약에 따르면 최근 추세는 증가입니다.", error: Exception | None = None):
        self.reply = reply
        self.error = error
        self.calls: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.calls.append(deepcopy(messages))
        if self.error:
            raise self.error
        return self.reply
