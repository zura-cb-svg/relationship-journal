from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
import models
from database import get_db
from dependencies import get_owned_journal_entry, get_owned_relationship
from schemas import JournalEntryCreate, JournalEntryResponse, JournalEntryUpdate

router = APIRouter(tags=["journal_entries"])


@router.post("/relationships/{id}/entries", response_model=JournalEntryResponse, status_code=201)
def create_journal_entry(
    entry: JournalEntryCreate,
    db: Session = Depends(get_db),
    relationship: models.Relationship = Depends(get_owned_relationship)
):
    new_entry = models.JournalEntry(
        title=entry.title,
        content=entry.content,
        relationship_id=relationship.id
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry


@router.get("/relationships/{id}/entries", response_model=list[JournalEntryResponse])
def get_journal_entries(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, min_length=1, max_length=150),
    db: Session = Depends(get_db),
    relationship: models.Relationship = Depends(get_owned_relationship)
):
    query = db.query(models.JournalEntry).filter(
        models.JournalEntry.relationship_id == relationship.id
    )
    if search is not None:
        query = query.filter(or_(
            models.JournalEntry.title.icontains(search, autoescape=True),
            models.JournalEntry.content.icontains(search, autoescape=True)
        ))
    return (
        query.order_by(models.JournalEntry.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/relationships/{id}/entries/{entry_id}", response_model=JournalEntryResponse)
def get_single_entry(
    entry: models.JournalEntry = Depends(get_owned_journal_entry)
):
    return entry


@router.put("/relationships/{id}/entries/{entry_id}", response_model=JournalEntryResponse)
def update_journal_entry(
    update: JournalEntryUpdate,
    db: Session = Depends(get_db),
    entry: models.JournalEntry = Depends(get_owned_journal_entry)
):
    entry.title = update.title
    entry.content = update.content
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/relationships/{id}/entries/{entry_id}")
def delete_journal_entry(
    db: Session = Depends(get_db),
    entry: models.JournalEntry = Depends(get_owned_journal_entry)
):
    db.delete(entry)
    db.commit()
    return {"detail": "Journal entry deleted"}
