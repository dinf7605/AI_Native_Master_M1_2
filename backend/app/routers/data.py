"""`/api/data` 엔드포인트. HTTP 입출력만 담당하고 규칙은 DataService에 위임한다."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies import get_data_service
from app.schemas.common import DocumentId, MessageResponse
from app.schemas.data import DataCreate, DataItem, SummaryResponse
from app.services.data_service import DataService

router = APIRouter(prefix="/api/data", tags=["data"])

Service = Annotated[DataService, Depends(get_data_service)]


@router.get(
    "/summary",
    response_model=SummaryResponse,
    summary="데이터 요약 (프롬프트 주입용)",
    description="저장된 전체 데이터의 기간, 개수, 평균/최소/최대, 최신값, 최근 추세를 반환한다. "
    "AI 채팅의 시스템 프롬프트에 이 요약이 주입된다.",
)
def get_summary(service: Service):
    return service.get_summary()


@router.get("", response_model=list[DataItem], summary="데이터 목록 조회", description="날짜 오름차순.")
def list_data(service: Service):
    return service.list_items()


@router.post(
    "",
    response_model=DataItem,
    status_code=status.HTTP_201_CREATED,
    summary="새 데이터 추가",
    description="같은 날짜의 데이터가 이미 있으면 409를 반환한다.",
)
def create_data(payload: DataCreate, service: Service):
    return service.create_item(payload)


@router.put(
    "/{item_id}",
    response_model=DataItem,
    summary="데이터 수정",
    description="date, value, memo 전체를 교체한다. 없는 ID는 404, 다른 데이터와 날짜가 겹치면 409.",
)
def update_data(item_id: DocumentId, payload: DataCreate, service: Service):
    return service.update_item(item_id, payload)


@router.delete("/{item_id}", response_model=MessageResponse, summary="데이터 삭제")
def delete_data(item_id: DocumentId, service: Service):
    service.delete_item(item_id)
    return {"message": "삭제되었습니다."}
