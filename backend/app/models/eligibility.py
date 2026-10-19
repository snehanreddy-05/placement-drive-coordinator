from typing import Optional
from datetime import datetime, timezone
import uuid
from sqlmodel import SQLModel, Field

class DriveEligibilityResult(SQLModel, table=True):
    __tablename__ = "drive_eligibility_results"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    drive_id: str = Field(index=True)
    student_id: str = Field(index=True)
    is_eligible: bool = Field(index=True)
    reason: str  # Human readable summary
    failure_reasons_json: str = Field(default="[]")  # JSON array of reasons
    rules_version: str = Field(default="v1.0.0")
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EligibilitySummary(SQLModel):
    drive_id: str
    total_evaluated: int
    eligible_count: int
    excluded_count: int
    rules_version: str
    evaluated_at: datetime
