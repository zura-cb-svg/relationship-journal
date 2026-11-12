from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    EmailStr,
    TypeAdapter,
    field_validator
)


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=150)
    gmail: str = Field(max_length=150)
    password: str = Field(min_length=15, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()

        if len(value) < 3:
            raise ValueError("Username is too short")

        return value

    @field_validator("gmail")
    @classmethod
    def validate_email(cls, value: str) -> str:
        TypeAdapter(EmailStr).validate_python(value)
        return value


class UserLogin(BaseModel):
    gmail: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"]


class UserResponse(BaseModel):
    id: int
    username: str
    gmail: str

    model_config = ConfigDict(from_attributes=True)


class RelationshipCreate(BaseModel):
    his_name: str = Field(min_length=1, max_length=150)
    years_together: int = Field(ge=0)
    problem: str = Field(min_length=1, max_length=5000)
    status: str = Field(min_length=1, max_length=100)

    model_config = ConfigDict(str_strip_whitespace=True)


class RelationshipUpdate(RelationshipCreate):
    pass


class RelationshipResponse(BaseModel):
    id: int
    his_name: str
    years_together: int = Field(ge=0)
    problem: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class JournalEntryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    content: str = Field(min_length=1, max_length=20000)

    model_config = ConfigDict(str_strip_whitespace=True)


class JournalEntryUpdate(JournalEntryCreate):
    pass


class JournalEntryResponse(BaseModel):
    id: int
    relationship_id: int
    title: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DeleteAccountRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)
