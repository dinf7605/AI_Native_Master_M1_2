"""여러 라우터가 함께 쓰는 응답 모델과 경로 파라미터."""

from typing import Annotated

from fastapi import Path
from pydantic import BaseModel

DocumentId = Annotated[
    str, Path(pattern=r"^[A-Za-z0-9_-]{1,128}$", description="Firestore 문서 ID (목록 조회 응답의 id)")
]


class MessageResponse(BaseModel):
    message: str
