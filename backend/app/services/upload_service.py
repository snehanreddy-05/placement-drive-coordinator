import json
import uuid
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
from sqlmodel import Session, select
from app.models.drive import PlacementDrive
from app.models.approval import Approval
from app.models.upload import UploadJob, UploadReceipt
from app.models.audit import AuditEvent
from app.services.mock_destination import mock_destination_service
from app.services.approval_service import verify_approval_validity

def execute_approved_upload(
    session: Session,
    drive_id: str,
    approval_id: str,
    idempotency_key: Optional[str] = None,
    simulation_mode: Optional[str] = None
) -> Tuple[UploadJob, Optional[UploadReceipt]]:
    """
    Submits an approved roster to the employer destination and immediately performs
    read-back reconciliation to determine if status is VERIFIED or MISMATCH.
    """
    drive = session.get(PlacementDrive, drive_id)
    if not drive:
        raise ValueError(f"Drive {drive_id} not found.")

    approval = session.get(Approval, approval_id)
    if not approval:
        raise ValueError(f"Approval {approval_id} not found.")

    # 1. Mandatory Safety Gate: Ensure approval is valid and not bypassed
    approved_ids: List[str] = json.loads(approval.approved_student_ids_json)
    is_valid, reason = verify_approval_validity(session, approval, drive, approved_ids)
    if not is_valid:
        raise PermissionError(f"Upload blocked by safety gate: {reason}")

    # Generate idempotency key if not passed
    idemp_key = idempotency_key or f"IDEMP-{drive_id}-{approval.roster_hash[:12]}"

    # Check existing upload with same idempotency key
    existing_job = session.exec(select(UploadJob).where(UploadJob.idempotency_key == idemp_key)).first()
    if existing_job:
        receipt = session.exec(select(UploadReceipt).where(UploadReceipt.upload_job_id == existing_job.id)).first()
        return existing_job, receipt

    # Create UploadJob
    job = UploadJob(
        drive_id=drive.id,
        approval_id=approval.id,
        destination_url=approval.destination_url,
        expected_count=len(approved_ids),
        idempotency_key=idemp_key,
        status="Pending"
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    # 2. Transmit to Destination
    try:
        submission_resp = mock_destination_service.submit_roster(
            drive_id=drive.id,
            student_ids=approved_ids,
            destination_url=approval.destination_url,
            idempotency_key=idemp_key,
            simulation_override=simulation_mode
        )
        job.status = "Submitted"
        job.submitted_count = submission_resp["submitted_count"]
        job.submitted_ids_json = json.dumps(approved_ids)
        job.submitted_at = datetime.now(timezone.utc)
        session.add(job)
        session.commit()
    except Exception as e:
        job.status = "Failed"
        job.error_message = str(e)
        session.add(job)
        session.commit()

        # Create failed receipt
        failed_receipt = UploadReceipt(
            upload_job_id=job.id,
            drive_id=drive.id,
            receipt_reference=f"FAIL-{uuid.uuid4().hex[:8].upper()}",
            destination=approval.destination_url,
            verification_status="FAILED",
            expected_count=len(approved_ids),
            actual_destination_count=0,
            matched_count=0,
            reconciliation_details=f"Destination submission failed with error: {str(e)}"
        )
        session.add(failed_receipt)
        session.commit()
        return job, failed_receipt

    # 3. Read back actual destination state
    dest_data = mock_destination_service.read_back_records(drive.id)
    if not dest_data:
        job.status = "Failed"
        receipt = UploadReceipt(
            upload_job_id=job.id,
            drive_id=drive.id,
            receipt_reference=submission_resp.get("receipt_reference", "UNKNOWN"),
            destination=approval.destination_url,
            verification_status="UNVERIFIED",
            expected_count=len(approved_ids),
            actual_destination_count=0,
            matched_count=0,
            reconciliation_details="Read-back inspection failed: Destination records could not be verified."
        )
        session.add(job)
        session.add(receipt)
        session.commit()
        return job, receipt

    actual_ids: List[str] = dest_data.get("stored_ids", [])
    expected_set = set(approved_ids)
    actual_set = set(actual_ids)

    # 4. Reconciliation
    missing_ids = sorted(list(expected_set - actual_set))
    unexpected_ids = sorted(list(actual_set - expected_set))
    duplicate_ids = []
    seen = set()
    for s in actual_ids:
        if s in seen and s not in duplicate_ids:
            duplicate_ids.append(s)
        seen.add(s)

    matched_count = len(expected_set.intersection(actual_set))
    actual_count = len(actual_ids)
    expected_count = len(approved_ids)

    is_verified = (
        actual_count == expected_count and
        len(missing_ids) == 0 and
        len(unexpected_ids) == 0 and
        len(duplicate_ids) == 0
    )

    verification_status = "VERIFIED" if is_verified else "MISMATCH"
    job.status = verification_status

    details_parts = []
    if is_verified:
        details_parts.append(f"100% Reconciliation match: All {matched_count} student records verified at destination.")
    else:
        if actual_count != expected_count:
            details_parts.append(f"Count mismatch: Expected {expected_count}, got {actual_count}.")
        if missing_ids:
            details_parts.append(f"{len(missing_ids)} missing IDs: {', '.join(missing_ids[:5])}.")
        if unexpected_ids:
            details_parts.append(f"{len(unexpected_ids)} unexpected IDs: {', '.join(unexpected_ids[:5])}.")
        if duplicate_ids:
            details_parts.append(f"{len(duplicate_ids)} duplicate IDs: {', '.join(duplicate_ids[:5])}.")

    receipt = UploadReceipt(
        upload_job_id=job.id,
        drive_id=drive.id,
        receipt_reference=dest_data.get("receipt_reference", f"RCPT-{uuid.uuid4().hex[:8].upper()}"),
        destination=approval.destination_url,
        verification_status=verification_status,
        expected_count=expected_count,
        actual_destination_count=actual_count,
        matched_count=matched_count,
        missing_ids_json=json.dumps(missing_ids),
        unexpected_ids_json=json.dumps(unexpected_ids),
        duplicate_ids_json=json.dumps(duplicate_ids),
        reconciliation_details=" ".join(details_parts)
    )

    session.add(job)
    session.add(receipt)
    session.commit()
    session.refresh(job)
    session.refresh(receipt)

    # Log audit event
    audit = AuditEvent(
        event_type="UPLOAD_VERIFIED" if is_verified else "UPLOAD_MISMATCH",
        entity_type="UploadJob",
        entity_id=job.id,
        actor=approval.approver_email,
        action_details=f"Upload {job.id} for drive '{drive.employer_name}' finished with status {verification_status}. {receipt.reconciliation_details}",
        metadata_json=json.dumps({"receipt_ref": receipt.receipt_reference, "verification_status": verification_status})
    )
    session.add(audit)
    session.commit()

    return job, receipt
