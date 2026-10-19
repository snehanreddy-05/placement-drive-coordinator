from typing import Optional
from datetime import datetime, timezone
import uuid
from sqlmodel import SQLModel, Field

class Approval(SQLModel, table=True):
    __tablename__ = "approvals"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    drive_id: str = Field(index=True)
    roster_hash: str = Field(index=True)  # SHA-256 of sorted student IDs & criteria
    criteria_version: int = Field(default=1)
    eligible_count: int
    approved_student_ids_json: str  # JSON array of approved student IDs in deterministic order
    destination_url: str
    approver_name: str
    approver_email: str
    status: str = Field(default="PENDING")  # PENDING, APPROVED, REJECTED, INVALIDATED
    rejection_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    approved_at: Optional[datetime] = None

class ApprovalCreate(SQLModel):
    drive_id: str
    approver_name: str
    approver_email: str
    destination_url: Optional[str] = None

class ApprovalDecision(SQLModel):
    decision: str  # "APPROVE" or "REJECT"
    approver_name: str
    approver_email: str
    rejection_reason: Optional[str] = None
