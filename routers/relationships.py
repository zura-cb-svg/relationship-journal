from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

import models
from schemas import RelationshipCreate, RelationshipUpdate, RelationshipResponse
from database import get_db
from dependencies import get_current_user, get_owned_relationship

router = APIRouter(tags=["relationships"])


@router.post("/relationships", response_model=RelationshipResponse, status_code=201)
def create_relationship(
    relationship: RelationshipCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    new_relationship = models.Relationship(
        his_name=relationship.his_name,
        years_together=relationship.years_together,
        problem=relationship.problem,
        status=relationship.status,
        owner_id=current_user.id
    )

    db.add(new_relationship)
    db.commit()
    db.refresh(new_relationship)
    return new_relationship


@router.get("/relationships", response_model=list[RelationshipResponse])
def get_relationship(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None, max_length=100),
    search: str | None = Query(default=None, min_length=1, max_length=150),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.Relationship).filter(
        models.Relationship.owner_id == current_user.id
    )

    if status is not None:
        query = query.filter(models.Relationship.status == status)

    if search is not None:
        query = query.filter(or_(
            models.Relationship.his_name.icontains(search, autoescape=True),
            models.Relationship.problem.icontains(search, autoescape=True)
        ))

    return (
        query
        .order_by(models.Relationship.id.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/relationships/{id}", response_model=RelationshipResponse)
def get_id_relationship(
    relationship: models.Relationship = Depends(get_owned_relationship)
):
    return relationship


@router.put("/relationships/{id}", response_model=RelationshipResponse)
def update(
    update_data: RelationshipUpdate,
    db: Session = Depends(get_db),
    relationship: models.Relationship = Depends(get_owned_relationship)
):
    relationship.his_name = update_data.his_name
    relationship.years_together = update_data.years_together
    relationship.problem = update_data.problem
    relationship.status = update_data.status

    db.commit()
    db.refresh(relationship)
    return relationship


@router.delete("/relationships/{id}")
def delete_relationship(
    db: Session = Depends(get_db),
    relationship: models.Relationship = Depends(get_owned_relationship)
):
    db.delete(relationship)
    db.commit()
    return {"detail": "Relationship deleted"}
