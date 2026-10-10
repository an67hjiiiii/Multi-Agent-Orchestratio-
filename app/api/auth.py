from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.auth.store import AuthStore, DuplicateUserError


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str | None = None
    username: str | None = None
    display_name: str | None = Field(default=None, max_length=128)
    password: str = Field(min_length=8, max_length=1024)


router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_auth_store(request: Request) -> AuthStore:
    return request.app.state.auth_store


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, request: Request) -> dict[str, object]:
    store = get_auth_store(request)
    try:
        user = store.register(
            email=body.email,
            username=body.username,
            display_name=body.display_name,
            password=body.password,
        )
    except DuplicateUserError as exc:
        raise HTTPException(status_code=409, detail="Account already exists") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"user": user}
