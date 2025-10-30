from __future__ import annotations

import os
import secrets

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field


class AdminCredentials(BaseModel):
    """요청으로 전달되는 관리자 인증 정보."""

    username: str = Field(..., description="관리자 계정 아이디")
    password: str = Field(..., description="관리자 계정 비밀번호")


router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/token")
async def issue_admin_token(credentials: AdminCredentials) -> dict[str, str]:
    """Validate admin credentials and issue a session token."""
    expected_username = os.getenv("ADMIN_USERNAME")
    expected_password = os.getenv("ADMIN_PASSWORD")

    if credentials.username != expected_username or credentials.password != expected_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrator credentials.",
        )

    token = secrets.token_hex(16)
    return {"admin": credentials.username, "token": token}

