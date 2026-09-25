import threading
import time
from concurrent.futures import ThreadPoolExecutor

import firebase_admin

import app.firebase as firebase_module


def test_concurrent_first_requests_initialize_firebase_once(monkeypatch):
    """콜드스타트 직후 요청 여러 개가 동시에 들어와도 초기화는 한 번만 일어나야 한다."""
    state = {"initialized": False, "init_calls": 0}
    guard = threading.Lock()

    def fake_get_app():
        if not state["initialized"]:
            raise ValueError("The default Firebase app does not exist.")

    def fake_initialize_app(cred):
        time.sleep(0.05)  # 실제 초기화처럼 시간이 걸리는 동안 다른 스레드가 끼어들 여지를 만든다
        with guard:
            state["init_calls"] += 1
            if state["initialized"]:
                raise ValueError("The default Firebase app already exists.")
            state["initialized"] = True

    monkeypatch.setattr(firebase_admin, "get_app", fake_get_app)
    monkeypatch.setattr(firebase_module.firebase_admin, "initialize_app", fake_initialize_app)
    monkeypatch.setattr(firebase_module, "load_firebase_credentials", lambda: {})
    monkeypatch.setattr(firebase_module.credentials, "Certificate", lambda _: object())
    monkeypatch.setattr(firebase_module.firestore, "client", lambda: "client")

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: firebase_module.get_firestore_client(), range(8)))

    assert results == ["client"] * 8
    assert state["init_calls"] == 1
