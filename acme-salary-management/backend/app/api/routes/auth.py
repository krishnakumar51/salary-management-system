from fastapi import APIRouter

from app.api.deps import DB, CurrentUser
from app.core.security import create_access_token
from app.schemas.auth import LoginRequest, TokenOut, UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(body: LoginRequest, db: DB):
    user = auth_service.authenticate(db, body.email, body.password)
    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user
