from typing import Optional
from datetime import datetime, timezone
import uuid
from sqlmodel import SQLModel, Field

class AuditEvent(SQLModel, table=True):
    __tablename__ = "audit_events"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    event_type: str = Field(index=True) # ROSTER_IMPORT, ELIGIBILITY_EVAL, APPROVAL_GRANTED, APPROVAL_REJECTED, APPROVAL_INVALIDATED, UPLOAD_SUBMITTED, UPLOAD_VERIFIED, ATTENDANCE_GENERATED
    entity_type: str # Student, PlacementDrive, Approval, UploadJob, etc.
    entity_id: str
    actor: str = Field(default="system")
    action_details: str
    metadata_json: Optional[str] = Field(default="{}")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
