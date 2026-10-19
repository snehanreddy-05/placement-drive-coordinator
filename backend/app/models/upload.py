from typing import Optional
from datetime import datetime, timezone
import uuid
from sqlmodel import SQLModel, Field

class UploadJob(SQLModel, table=True):
    __tablename__ = "upload_jobs"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    drive_id: str = Field(index=True)
    approval_id: str = Field(index=True)
    destination_url: str
    status: str = Field(default="Pending")  # Pending, Submitted, Verified, Mismatch, Failed
    expected_count: int
    submitted_count: int = Field(default=0)
    submitted_ids_json: str = Field(default="[]")
    idempotency_key: str = Field(index=True, unique=True)
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_at: Optional[datetime] = None

class UploadReceipt(SQLModel, table=True):
    __tablename__ = "upload_receipts"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    upload_job_id: str = Field(index=True)
    drive_id: str = Field(index=True)
    receipt_reference: str = Field(unique=True, index=True)
    destination: str
    verification_status: str = Field(default="Pending")  # VERIFIED, MISMATCH, UNVERIFIED, FAILED
    expected_count: int
    actual_destination_count: int
    matched_count: int
    missing_ids_json: str = Field(default="[]")
    unexpected_ids_json: str = Field(default="[]")
    duplicate_ids_json: str = Field(default="[]")
    reconciliation_details: str
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
