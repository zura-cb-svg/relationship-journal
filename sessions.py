import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

import models
from security import create_access_token

SESSION_EXPIRE_DAYS = 7

def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

def issue_tokens(db: Session, auth_session: models.AuthSession):
    refresh = secrets.token_urlsafe(32)
    db.add(models.RefreshToken(
        session_id=auth_session.id,
        token_hash=hash_refresh_token(refresh)
    ))
    access = create_access_token({
        'sub': str(auth_session.user_id), 'sid': auth_session.id
    })
    seconds = max(1, int((auth_session.expires_at - datetime.now(timezone.utc)).total_seconds()))
    return {'access_token': access, 'token_type': 'bearer'}, refresh, seconds

def create_session(db: Session, user_id: int):
    auth_session = models.AuthSession(
        id=str(uuid4()), user_id=user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRE_DAYS)
    )
    db.add(auth_session)
    db.flush()
    result = issue_tokens(db, auth_session)
    db.commit()
    return result

def lock_token_session(db: Session, token: str):
    session_id = db.query(models.RefreshToken.session_id).filter(
        models.RefreshToken.token_hash == hash_refresh_token(token)
    ).scalar()
    if session_id is None:
        return None
    return db.query(models.AuthSession).filter(
        models.AuthSession.id == session_id
    ).populate_existing().with_for_update().first()

def rotate_refresh_token(db: Session, token: str):
    invalid = HTTPException(status_code=401, detail='Invalid refresh token')
    auth_session = lock_token_session(db, token)
    now = datetime.now(timezone.utc)
    if not auth_session or auth_session.revoked_at is not None or auth_session.expires_at <= now:
        raise invalid
    stored = db.query(models.RefreshToken).filter(
        models.RefreshToken.token_hash == hash_refresh_token(token),
        models.RefreshToken.session_id == auth_session.id
    ).populate_existing().first()
    if stored is None:
        raise invalid
    if stored.used_at is not None:
        auth_session.revoked_at = now
        db.commit()
        raise invalid
    stored.used_at = now
    result = issue_tokens(db, auth_session)
    db.commit()
    return result

def revoke_session(db: Session, token: str):
    auth_session = lock_token_session(db, token)
    if auth_session and auth_session.revoked_at is None:
        auth_session.revoked_at = datetime.now(timezone.utc)
    db.commit()
