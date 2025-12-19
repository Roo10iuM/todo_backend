import os
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import router
from repository.database import dispose_engine
from logging_config import setup_logging

setup_logging()

app = FastAPI(title="todo backend")


def _get_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return ["http://localhost:5173", "http://127.0.0.1:5173"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

def _sanitize_errors(errors: list[dict]) -> list[dict]:
    sanitized = []
    for error in errors:
        sanitized.append(
            {
                "loc": error.get("loc"),
                "msg": error.get("msg"),
                "type": error.get("type"),
            }
        )
    return sanitized


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    sanitized = _sanitize_errors(exc.errors())
    logging.getLogger("app.validation").error(
        "validation error",
        extra={
            "event": "validation_error",
            "path": request.url.path,
            "errors": sanitized,
        },
    )
    return JSONResponse(status_code=422, content={"detail": sanitized})


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await dispose_engine()
