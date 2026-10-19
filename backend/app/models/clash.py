from typing import Optional
from datetime import datetime, timezone
import uuid
from sqlmodel import SQLModel, Field

class DriveClash(SQLModel, table=True):
    __tablename__ = "drive_clashes"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    drive1_id: str = Field(index=True)
    drive2_id: str = Field(index=True)
    drive1_title: str
    drive2_title: str
    clash_type: str = Field(default="SCHEDULE_OVERLAP") # SCHEDULE_OVERLAP, STUDENT_OVERLAP
    start_time_overlap: datetime
    end_time_overlap: datetime
    affected_students_count: int = Field(default=0)
    affected_students_json: str = Field(default="[]")
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
