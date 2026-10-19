from typing import Optional
from datetime import datetime, timezone
import uuid
from sqlmodel import SQLModel, Field

class AttendanceRecord(SQLModel, table=True):
    __tablename__ = "attendance_records"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    drive_id: str = Field(index=True)
    student_id: str = Field(index=True)
    student_name: str
    branch: str
    drive_title: str
    attendance_status: str = Field(default="Not Marked")  # Not Marked, Present, Absent, Excused
    check_in_time: Optional[datetime] = None
    notes: Optional[str] = None
    roster_hash: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
