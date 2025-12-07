import reflex as rx
from typing import Optional
from datetime import datetime
import sqlmodel
import enum


class RelationshipType(str, enum.Enum):
    EMPLOYMENT = "employment"
    SOCIAL = "social"
    BUSINESS = "business"


class RelationshipTerm(str, enum.Enum):
    WORKS_FOR = "works_for"
    INVESTED_IN = "invested_in"
    COMPETITOR = "competitor"
    COLLEAGUE = "colleague"
    FRIEND = "friend"
    ENEMY = "enemy"


class Account(sqlmodel.SQLModel, table=True):
    """Represents a company or organization node."""

    id: Optional[int] = sqlmodel.Field(default=None, primary_key=True)
    name: str
    ticker: str
    dynamics_account_id: str = ""
    created_at: datetime = sqlmodel.Field(default_factory=datetime.now)
    updated_at: datetime = sqlmodel.Field(default_factory=datetime.now)
    last_modified_by: str = sqlmodel.Field(default="System User")
    contacts: list["Contact"] = sqlmodel.Relationship(back_populates="account")


class Contact(sqlmodel.SQLModel, table=True):
    """Represents a person node."""

    id: Optional[int] = sqlmodel.Field(default=None, primary_key=True)
    first_name: str
    last_name: str
    job_title: str
    dynamics_contact_id: str = ""
    created_at: datetime = sqlmodel.Field(default_factory=datetime.now)
    updated_at: datetime = sqlmodel.Field(default_factory=datetime.now)
    last_modified_by: str = sqlmodel.Field(default="System User")
    account_id: Optional[int] = sqlmodel.Field(default=None, foreign_key="account.id")
    account: Optional[Account] = sqlmodel.Relationship(back_populates="contacts")


class Relationship(sqlmodel.SQLModel, table=True):
    """Tracks relationships between entities (Person-Person, Company-Company, Person-Company)."""

    id: Optional[int] = sqlmodel.Field(default=None, primary_key=True)
    score: int = 0
    created_at: datetime = sqlmodel.Field(default_factory=datetime.now)
    last_updated: datetime = sqlmodel.Field(default_factory=datetime.now)
    last_modified_by: str = sqlmodel.Field(default="System User")
    relationship_type: RelationshipType = sqlmodel.Field(
        default=RelationshipType.EMPLOYMENT
    )
    is_active: bool = sqlmodel.Field(default=True)
    is_directed: bool = sqlmodel.Field(default=True)
    term: RelationshipTerm = sqlmodel.Field(default=RelationshipTerm.WORKS_FOR)
    source_type: str = "person"
    source_id: int
    target_type: str = "company"
    target_id: int
    logs: list["RelationshipLog"] = sqlmodel.Relationship(back_populates="relationship")


class RelationshipLog(sqlmodel.SQLModel, table=True):
    """Tracks history of relationship score changes."""

    id: Optional[int] = sqlmodel.Field(default=None, primary_key=True)
    previous_score: int
    new_score: int
    previous_term: Optional[str] = None
    new_term: Optional[str] = None
    action: str = "score_change"
    changed_at: datetime = sqlmodel.Field(default_factory=datetime.now)
    note: Optional[str] = None
    relationship_id: int = sqlmodel.Field(foreign_key="relationship.id")
    relationship: Optional[Relationship] = sqlmodel.Relationship(back_populates="logs")