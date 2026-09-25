"""도메인 예외. main.py의 예외 핸들러가 status_code에 맞는 HTTP 응답으로 변환한다."""


class AppError(Exception):
    """사용자에게 그대로 보여줄 수 있는 메시지를 가진 예외의 기반 클래스."""

    status_code = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = 404


class DuplicateDateError(AppError):
    status_code = 409


class ConversationLimitError(AppError):
    status_code = 409


class LLMRequestError(AppError):
    """AI(GPT) 호출이 실패했거나 빈 응답을 받았다."""

    status_code = 502


class DatabaseUnavailableError(AppError):
    status_code = 503


class LLMUnavailableError(AppError):
    """AI 호출 설정(키 등)이 없거나 잘못되었다."""

    status_code = 503
