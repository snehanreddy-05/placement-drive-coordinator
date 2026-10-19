from typing import Optional, List
from datetime import datetime, timezone
import uuid
from sqlmodel import SQLModel, Field

class PlacementDriveBase(SQLModel):
    employer_name: str
    drive_title: str
    min_cgpa: float = Field(default=6.0, ge=0.0, le=10.0)
    eligible_branches: str = Field(default="CSE,IT,ECE")  # Comma separated
    max_backlogs: int = Field(default=0, ge=0)
    consent_required: bool = Field(default=True)
    registration_deadline: datetime
    start_time: datetime
    end_time: datetime
    timezone: str = Field(default="Asia/Kolkata")
    venue: str = Field(default="Campus Auditorium / Virtual")
    employer_form_url: Optional[str] = Field(default="mock://employer.recruitment/v1/intake")
    status: str = Field(default="Active")  # Draft, Active, Completed, Archived
    criteria_version: int = Field(default=1)

class PlacementDrive(PlacementDriveBase, table=True):
    __tablename__ = "placement_drives"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PlacementDriveCreate(PlacementDriveBase):
    pass

class PlacementDriveUpdate(SQLModel):
    employer_name: Optional[str] = None
    drive_title: Optional[str] = None
    min_cgpa: Optional[float] = None
    eligible_branches: Optional[str] = None
    max_backlogs: Optional[int] = None
    consent_required: Optional[bool] = None
    registration_deadline: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    timezone: Optional[str] = None
    venue: Optional[str] = None
    employer_form_url: Optional[str] = None
    status: Optional[str] = None

class PlacementDriveRead(PlacementDriveBase):
    id: str
    created_at: datetime
    updated_at: datetime
