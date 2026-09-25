"""여러 라우터가 함께 쓰는 응답 모델과 경로 파라미터."""

from typing import Annotated

from fastapi import Path
from pydantic import BaseModel

DOCUMENT_ID_PATTERN = r"^[A-Za-z0-9_-]{1,128}$"

DocumentId = Annotated[
    str, Path(pattern=DOCUMENT_ID_PATTERN, description="Firestore 문서 ID (목록 조회 응답의 id)")
]


class MessageResponse(BaseModel):
    message: str
