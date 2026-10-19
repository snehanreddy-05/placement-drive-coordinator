from typing import Optional
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field

class StudentBase(SQLModel):
    student_id: str = Field(index=True, unique=True, primary_key=True)
    full_name: str
    email: str
    branch: str
    cgpa: float
    active_backlogs: int = Field(default=0)
    consent_given: bool = Field(default=False)
    is_sample: bool = Field(default=False)

class Student(StudentBase, table=True):
    __tablename__ = "students"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StudentCreate(StudentBase):
    pass

class StudentRead(StudentBase):
    created_at: datetime
    updated_at: datetime

class RosterImportRecord(SQLModel, table=True):
    __tablename__ = "roster_imports"
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    error_summary: Optional[str] = None
    imported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
