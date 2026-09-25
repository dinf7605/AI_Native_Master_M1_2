"""Firestore 클라이언트 제공. firebase_admin 앱은 프로세스당 한 번만 초기화한다.

FastAPI는 동기 엔드포인트를 스레드 풀에서 실행하므로, 콜드스타트 직후 요청 여러 개가
동시에 들어오면 초기화가 겹칠 수 있다. 락으로 한 스레드만 초기화하게 한다.
"""

import threading

import firebase_admin
from firebase_admin import credentials, firestore

from app.config import load_firebase_credentials
from app.errors import DatabaseUnavailableError

_init_lock = threading.Lock()


def _is_initialized() -> bool:
    try:
        firebase_admin.get_app()
        return True
    except ValueError:
        return False


def get_firestore_client():
    if not _is_initialized():
        with _init_lock:
            if not _is_initialized():  # 락을 기다리는 동안 다른 스레드가 초기화했을 수 있다
                try:
                    cred = credentials.Certificate(load_firebase_credentials())
                except (ValueError, OSError) as e:
                    raise DatabaseUnavailableError("서비스 계정 키 형식이 올바르지 않습니다.") from e
                firebase_admin.initialize_app(cred)
    return firestore.client()
