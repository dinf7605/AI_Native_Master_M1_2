"""FastAPI 앱 진입점.

실행 (backend/ 에서): uvicorn main:app --reload
API 문서: http://127.0.0.1:8000/docs
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from google.api_core.exceptions import GoogleAPIError

from app.config import get_allowed_origins
from app.errors import AppError
from app.routers import chat, conversations, data

logger = logging.getLogger(__name__)

app = FastAPI(
    title="USD/KRW 환율 데이터 AI 채팅 API",
    description="환율 시계열 데이터 CRUD, 데이터 요약, 요약을 주입한 AI 채팅, 대화 기록 API.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(GoogleAPIError)
async def handle_database_error(request: Request, exc: GoogleAPIError) -> JSONResponse:
    logger.exception("Firestore request failed")
    return JSONResponse(
        status_code=503,
        content={"detail": "데이터베이스 요청에 실패했습니다. 잠시 후 다시 시도하세요."},
    )


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["system"], summary="헬스체크", description="DB에 접근하지 않는다. 서버 깨우기용.")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(data.router)
app.include_router(conversations.router)
app.include_router(chat.router)
