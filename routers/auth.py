from fastapi import APIRouter, HTTPException, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

import models
from database import get_db
from dependencies import get_current_user
from schemas import UserCreate, UserResponse, TokenResponse, DeleteAccountRequest
from rate_limit import limit_login, limit_signup, check_rate_limit
from sessions import create_session, rotate_refresh_token, revoke_session
from web_config import REFRESH_COOKIE, set_refresh_cookie, clear_refresh_cookie, check_auth_origin
from security import (
    hash_password,
    verify_password,
    DUMMY_PASSWORD_HASH
)

router = APIRouter(tags=["auth"])


@router.post(
    "/signup",
    response_model=UserResponse,
    dependencies=[Depends(limit_signup)]
)
def usercreate(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    existing_user = db.query(models.User).filter(
        models.User.gmail == user.gmail
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Unable to create account"
        )

    new_user = models.User(
        username=user.username,
        gmail=user.gmail,
        hashed_password=hash_password(user.password)
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Unable to create account"
        )

    return new_user


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(limit_login), Depends(check_auth_origin)]
)
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )

    if (
        len(form_data.password) > 128
        or len(form_data.username) > 150
    ):
        raise credentials_exception

    user = db.query(models.User).filter(
        models.User.gmail == form_data.username
    ).first()

    stored_hash = (
        user.hashed_password
        if user
        else DUMMY_PASSWORD_HASH
    )

    valid_password = verify_password(
        form_data.password,
        stored_hash
    )

    if not user or not valid_password:
        raise credentials_exception

    tokens, refresh, seconds = create_session(db, user.id)
    set_refresh_cookie(response, refresh, seconds)
    return tokens


def limit_refresh(request: Request):
    check_rate_limit(request, action="refresh", limit=30, window=60)


@router.post("/refresh", response_model=TokenResponse,
             dependencies=[Depends(limit_refresh), Depends(check_auth_origin)])
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(REFRESH_COOKIE)
    if not token or len(token) > 256:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    tokens, new_refresh, seconds = rotate_refresh_token(db, token)
    set_refresh_cookie(response, new_refresh, seconds)
    return tokens


@router.post("/logout", dependencies=[Depends(check_auth_origin)])
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(REFRESH_COOKIE)
    if token and len(token) <= 256:
        revoke_session(db, token)
    clear_refresh_cookie(response)
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserResponse)
def getme(
    current_user: models.User = Depends(get_current_user)
):
    return current_user


def limit_account_delete(request: Request):
    check_rate_limit(request, action="delete-account", limit=5, window=60)


@router.delete("/me", dependencies=[Depends(limit_account_delete)])
def delete_my_account(
    confirmation: DeleteAccountRequest,
    response: Response,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(confirmation.password, current_user.hashed_password):
        raise HTTPException(status_code=403, detail="Invalid password")
    db.delete(current_user)
    db.commit()
    clear_refresh_cookie(response)

    return {"detail": "Account deleted"}
