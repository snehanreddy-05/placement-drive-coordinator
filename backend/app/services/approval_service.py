import hashlib
import json
from typing import List, Optional, Tuple
from datetime import datetime, timezone
from sqlmodel import Session, select
from app.models.drive import PlacementDrive
from app.models.eligibility import DriveEligibilityResult
from app.models.approval import Approval
from app.models.audit import AuditEvent

def compute_roster_hash(drive_id: str, criteria_version: int, student_ids: List[str], destination_url: str) -> str:
    """
    Computes a cryptographic SHA-256 fingerprint binding drive ID, criteria version,
    strictly sorted student IDs, and authorized destination URL.
    """
    sorted_ids = sorted([str(s).strip().upper() for s in student_ids])
    payload = f"{drive_id}|v{criteria_version}|{','.join(sorted_ids)}|{destination_url.strip()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def create_pending_approval(
    session: Session,
    drive: PlacementDrive,
    eligible_student_ids: List[str],
    destination_url: str,
    approver_name: str,
    approver_email: str
) -> Approval:
    sorted_ids = sorted([str(s).strip().upper() for s in eligible_student_ids])
    roster_hash = compute_roster_hash(drive.id, drive.criteria_version, sorted_ids, destination_url)

    approval = Approval(
        drive_id=drive.id,
        roster_hash=roster_hash,
        criteria_version=drive.criteria_version,
        eligible_count=len(sorted_ids),
        approved_student_ids_json=json.dumps(sorted_ids),
        destination_url=destination_url,
        approver_name=approver_name,
        approver_email=approver_email,
        status="PENDING"
    )
    session.add(approval)
    session.commit()
    session.refresh(approval)

    audit = AuditEvent(
        event_type="APPROVAL_REQUESTED",
        entity_type="Approval",
        entity_id=approval.id,
        actor=approver_email,
        action_details=f"Prepared roster of {len(sorted_ids)} students for drive '{drive.employer_name} - {drive.drive_title}' requiring human approval.",
        metadata_json=json.dumps({"drive_id": drive.id, "roster_hash": roster_hash})
    )
    session.add(audit)
    session.commit()

    return approval

def verify_approval_validity(session: Session, approval: Approval, drive: PlacementDrive, current_eligible_ids: List[str]) -> Tuple[bool, str]:
    """
    Validates that an approval hasn't been invalidated by changes to criteria or roster.
    """
    if approval.status != "APPROVED":
        return False, f"Approval is not in APPROVED state (current state: {approval.status})."

    # Criteria version mismatch
    if approval.criteria_version != drive.criteria_version:
        approval.status = "INVALIDATED"
        session.add(approval)
        session.commit()
        return False, f"Drive criteria was updated from v{approval.criteria_version} to v{drive.criteria_version}. Approval invalidated."

    # Roster hash mismatch
    current_hash = compute_roster_hash(drive.id, drive.criteria_version, current_eligible_ids, approval.destination_url)
    if current_hash != approval.roster_hash:
        approval.status = "INVALIDATED"
        session.add(approval)
        session.commit()
        return False, "Eligible student roster changed since approval was granted. Cryptographic hash mismatch. Approval invalidated."

    return True, "Approval is valid and cryptographically bound to current roster and criteria."
