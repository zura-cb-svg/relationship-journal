from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

import models
from database import get_db
from dependencies import get_current_user
from schemas import UserResponse, RelationshipResponse, JournalEntryResponse

router = APIRouter(tags=['dashboard'])
EXPORT_LIMIT = 1000

class DashboardResponse(BaseModel):
    relationships: int
    journal_entries: int
    by_status: dict[str, int]

class ExportResponse(BaseModel):
    user: UserResponse
    relationships: list[RelationshipResponse]
    journal_entries: list[JournalEntryResponse]

@router.get('/dashboard', response_model=DashboardResponse)
def dashboard(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    grouped = db.query(models.Relationship.status, func.count(models.Relationship.id)).filter(
        models.Relationship.owner_id == user.id
    ).group_by(models.Relationship.status).all()
    by_status = {status: count for status, count in grouped}
    entries = db.query(func.count(models.JournalEntry.id)).join(
        models.Relationship, models.Relationship.id == models.JournalEntry.relationship_id
    ).filter(models.Relationship.owner_id == user.id).scalar()
    return {'relationships': sum(by_status.values()), 'journal_entries': entries, 'by_status': by_status}

@router.get('/me/export', response_model=ExportResponse)
def export_data(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    relationships = db.query(models.Relationship).filter(
        models.Relationship.owner_id == user.id
    ).order_by(models.Relationship.id).limit(EXPORT_LIMIT + 1).all()
    entries = db.query(models.JournalEntry).join(
        models.Relationship, models.Relationship.id == models.JournalEntry.relationship_id
    ).filter(models.Relationship.owner_id == user.id).order_by(models.JournalEntry.id).limit(EXPORT_LIMIT + 1).all()
    if len(relationships) > EXPORT_LIMIT or len(entries) > EXPORT_LIMIT:
        raise HTTPException(status_code=413, detail='Export too large; use paginated endpoints')
    return {'user': user, 'relationships': relationships, 'journal_entries': entries}
