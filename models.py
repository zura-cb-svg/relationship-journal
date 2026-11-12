from sqlalchemy import Column, Integer, String, ForeignKey, CheckConstraint, Text, DateTime, func
from sqlalchemy.orm import  relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(150),nullable=False)
    gmail = Column(String(150), unique=True,nullable=False)
    hashed_password = Column(String(200),nullable=False)
    relationships = relationship(
        "Relationship",
         back_populates="owner",
         cascade="all, delete-orphan"
    )


class Relationship(Base):
    __tablename__ = "relationships"

    id = Column(Integer, primary_key=True)
    his_name = Column(String(150),nullable=False)
    years_together = Column(Integer,nullable=False)
    problem = Column(String,nullable=False)
    status = Column(String,nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"),nullable=False, index=True)
    owner = relationship("User", back_populates="relationships")
    __table_args__ = (
        CheckConstraint("years_together >=0", name="ck_relationships_years_together_nonnegative"),
    )
    journal_entries = relationship(
        "JournalEntry",
         back_populates="parent_relationship",
         cascade="all, delete-orphan"
    )


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True)
    relationship_id = Column(Integer, ForeignKey("relationships.id"), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True),server_default=func.now(), nullable=False)

    parent_relationship = relationship(
        "Relationship", 
        back_populates="journal_entries"
    )

class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id = Column(String(36), primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False
    )
    revoked_at = Column(
        DateTime(timezone=True),
        nullable=True
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True)
    session_id = Column(
        String(36),
        ForeignKey("auth_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    token_hash = Column(
        String(64),
        nullable=False,
        unique=True
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    used_at = Column(
        DateTime(timezone=True),
        nullable=True
    )