import re

from pydantic import BaseModel, Field, field_validator

LOGIN_PATTERN = re.compile(r"^[A-Za-z0-9._-]{3,32}$")


class RegisterRequest(BaseModel):
    login: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("login")
    @classmethod
    def validate_login(cls, value: str) -> str:
        trimmed = value.strip()
        if not LOGIN_PATTERN.fullmatch(trimmed):
            raise ValueError(
                "Login must be 3-32 chars: Latin letters, digits, or ._-"
            )
        return trimmed

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        missing = []
        if not re.search(r"[A-Z]", value):
            missing.append("one uppercase letter")
        if not re.search(r"[a-z]", value):
            missing.append("one lowercase letter")
        if not re.search(r"\d", value):
            missing.append("one digit")
        if not re.search(r"[^A-Za-z0-9]", value):
            missing.append("one special character")
        if missing:
            raise ValueError("Password must include at least " + ", ".join(missing))
        return value


class LoginRequest(BaseModel):
    login: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("login")
    @classmethod
    def validate_login(cls, value: str) -> str:
        trimmed = value.strip()
        if not LOGIN_PATTERN.fullmatch(trimmed):
            raise ValueError(
                "Login must be 3-32 chars: Latin letters, digits, or ._-"
            )
        return trimmed


class UserOut(BaseModel):
    id: int
    login: str


class AuthResponse(BaseModel):
    user: UserOut


class RegisterResponse(BaseModel):
    message: str


class TaskOut(BaseModel):
    id: int
    title: str
    is_done: bool
