from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"code": exc.code, "message": exc.message, "request_id": getattr(request.state, "request_id", None)})


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Never return provider errors, request bodies, tokens, or tracebacks to clients.
    import logging

    logging.getLogger("agrivision").exception("Unhandled request failure request_id=%s", getattr(request.state, "request_id", "unknown"))
    return JSONResponse(status_code=500, content={"code": "internal_error", "message": "An unexpected error occurred.", "request_id": getattr(request.state, "request_id", None)})
