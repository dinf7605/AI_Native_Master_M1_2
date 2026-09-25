"""Firestore 클라이언트 제공. firebase_admin 앱은 프로세스당 한 번만 초기화한다."""

import firebase_admin
from firebase_admin import credentials, firestore

from app.config import load_firebase_credentials
from app.errors import DatabaseUnavailableError


def get_firestore_client():
    try:
        firebase_admin.get_app()
    except ValueError:
        try:
            cred = credentials.Certificate(load_firebase_credentials())
        except (ValueError, OSError) as e:
            raise DatabaseUnavailableError("서비스 계정 키 형식이 올바르지 않습니다.") from e
        firebase_admin.initialize_app(cred)
    return firestore.client()
