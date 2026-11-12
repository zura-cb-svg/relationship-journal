from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import jwt
import models

from database import get_db
from security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")

        if not subject:
            raise credentials_exception

        user_id = int(subject)
        session_id = payload.get("sid")
        if not isinstance(session_id, str) or str(UUID(session_id)) != session_id:
            raise credentials_exception
        if not 0 < user_id <= 2147483647:
            raise credentials_exception

    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise credentials_exception

    user = db.query(models.User).filter(
        models.User.id == user_id
    ).first()

    if not user:
        raise credentials_exception

    active_session = db.query(models.AuthSession.id).filter(
        models.AuthSession.id == session_id,
        models.AuthSession.user_id == user_id,
        models.AuthSession.revoked_at.is_(None),
        models.AuthSession.expires_at > datetime.now(timezone.utc)
    ).first()
    if active_session is None:
        raise credentials_exception

    return user


def get_owned_relationship(
    id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    relationship = db.query(models.Relationship).filter(
        models.Relationship.id == id,
        models.Relationship.owner_id == current_user.id
    ).first()

    if not relationship:
        raise HTTPException(
            status_code=404,
            detail="Relationship not found"
        )

    return relationship


def get_owned_journal_entry(
    id: int,
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    entry = (
        db.query(models.JournalEntry)
        .join(
            models.Relationship,
            models.JournalEntry.relationship_id == models.Relationship.id
        )
        .filter(
            models.Relationship.owner_id == current_user.id,
            models.Relationship.id == id,
            models.JournalEntry.id == entry_id
        )
        .first()
    )

    if not entry:
        raise HTTPException(
            status_code=404,
            detail="Journal entry not found"
        )

    return entry
