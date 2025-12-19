from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from repository.models import AuthSession, Task, User
from repository.security import TOKEN_TTL_SECONDS, hash_token


async def create_user(session: AsyncSession, login: str, password_hash: str) -> User:
    user = User(login=login, password_hash=password_hash)
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(user)
    return user


async def get_user_by_login(session: AsyncSession, login: str) -> User | None:
    result = await session.execute(select(User).where(User.login == login))
    return result.scalar_one_or_none()


async def create_session(session: AsyncSession, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=TOKEN_TTL_SECONDS)
    auth_session = AuthSession(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(auth_session)
    await session.commit()
    return token


async def revoke_session(session: AsyncSession, token: str) -> None:
    token_hash = hash_token(token)
    await session.execute(
        delete(AuthSession).where(AuthSession.token_hash == token_hash)
    )
    await session.commit()


async def get_user_by_token(session: AsyncSession, token: str) -> User | None:
    token_hash = hash_token(token)
    stmt = (
        select(User)
        .join(AuthSession, AuthSession.user_id == User.id)
        .where(AuthSession.token_hash == token_hash)
        .where(AuthSession.expires_at > func.now())
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_tasks(session: AsyncSession, user_id: int) -> list[Task]:
    result = await session.execute(
        select(Task).where(Task.user_id == user_id).order_by(Task.id)
    )
    return list(result.scalars().all())
