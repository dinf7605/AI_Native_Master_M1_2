"""`/api/data` 요청/응답 모델. 요청 검증 규칙은 모두 여기에서 선언한다."""

from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DataCreate(BaseModel):
    """POST/PUT 요청 본문. PUT은 전체 교체이므로 같은 모델을 쓴다."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={"examples": [{"date": "2026-09-25", "value": 1370.5, "memo": "직접 입력"}]},
    )

    date: Date = Field(description="날짜 (YYYY-MM-DD). 날짜당 1건만 저장할 수 있다.")
    value: float = Field(gt=0, allow_inf_nan=False, description="USD/KRW 환율 (0보다 큰 수)")
    memo: str = Field(default="", max_length=200, description="메모 (최대 200자)")


class DataItem(BaseModel):
    id: str = Field(description="Firestore 문서 ID")
    date: Date
    value: float
    memo: str


class SummaryPoint(BaseModel):
    value: float
    date: Date


class Trend(BaseModel):
    direction: Literal["increase", "decrease", "flat", "insufficient_data"] = Field(
        description="최근 window개 평균을 직전 window개 평균과 비교한 추세"
    )
    change_pct: float | None = Field(description="직전 구간 대비 변화율(%)")
    window: int | None = Field(description="비교에 사용한 데이터 포인트 개수")


class SummaryResponse(BaseModel):
    count: int
    start_date: Date | None
    end_date: Date | None
    mean: float | None
    min: SummaryPoint | None
    max: SummaryPoint | None
    latest: SummaryPoint | None
    trend: Trend


class MessageResponse(BaseModel):
    message: str
