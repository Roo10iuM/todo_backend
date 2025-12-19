import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import AuthResponse, LoginRequest, RegisterRequest, RegisterResponse, TaskOut, UserOut
from repository.models import (
    User,
)
from repository.database import get_session
from repository.crud import (
    create_session,
    create_user,
    get_user_by_login,
    get_user_by_token,
    list_tasks as list_tasks_query,
    revoke_session,
)
from repository.security import TOKEN_TTL_SECONDS, hash_password, normalize_login, verify_password

router = APIRouter()
logger = logging.getLogger("app.auth")

AUTH_COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "auth_token")
AUTH_COOKIE_SAMESITE = os.getenv("AUTH_COOKIE_SAMESITE", "lax").lower()
AUTH_COOKIE_DOMAIN = os.getenv("AUTH_COOKIE_DOMAIN") or None

if AUTH_COOKIE_SAMESITE not in {"lax", "strict", "none"}:
    AUTH_COOKIE_SAMESITE = "lax"


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


AUTH_COOKIE_SECURE = _parse_bool(os.getenv("AUTH_COOKIE_SECURE", "false"))


def _extract_token(request: Request, required: bool = True) -> str | None:
    auth_header = request.headers.get("Authorization")
    if auth_header:
        scheme, _, token = auth_header.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header",
            )
        return token
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if token:
        return token
    if required:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )
    return None


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    token = _extract_token(request, required=True)
    user = await get_user_by_token(session, token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user


@router.post("/api/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> RegisterResponse:
    login = normalize_login(payload.login)
    if not login:
        logger.error(
            "register missing login",
            extra={"event": "register_invalid", "reason": "missing_login"},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Login is required",
        )
    password_hash = hash_password(payload.password)
    try:
        user = await create_user(session, login, password_hash)
    except IntegrityError:
        logger.error(
            "register conflict",
            extra={"event": "register_conflict", "login": login},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Login already exists",
        ) from None
    logger.info(
        "register success",
        extra={"event": "register_success", "login": login, "user_id": user.id},
    )
    return RegisterResponse(message="user создан")


@router.post("/api/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    login_value = normalize_login(payload.login)
    user = await get_user_by_login(session, login_value)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login or password",
        )
    token = await create_session(session, user.id)
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite=AUTH_COOKIE_SAMESITE,
        max_age=TOKEN_TTL_SECONDS,
        path="/",
        domain=AUTH_COOKIE_DOMAIN,
    )
    return AuthResponse(user=UserOut(id=user.id, login=user.login))


@router.get("/api/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(id=current_user.id, login=current_user.login)


@router.post("/api/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> None:
    token = _extract_token(request, required=False)
    if token:
        await revoke_session(session, token)
    response.delete_cookie(key=AUTH_COOKIE_NAME, path="/", domain=AUTH_COOKIE_DOMAIN)


@router.get("/api/tasks", response_model=list[TaskOut])
async def list_tasks(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[TaskOut]:
    tasks = await list_tasks_query(session, current_user.id)
    return [
        TaskOut(id=task.id, title=task.title, is_done=task.is_done) for task in tasks
    ]
