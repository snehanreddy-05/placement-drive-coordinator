import json
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.database import get_session
from app.models.drive import PlacementDrive
from app.models.approval import Approval, ApprovalCreate, ApprovalDecision
from app.models.eligibility import DriveEligibilityResult
from app.models.audit import AuditEvent
from app.services.approval_service import create_pending_approval, verify_approval_validity

router = APIRouter(prefix="/approvals", tags=["Approval Center"])

@router.get("")
def list_approvals(
    drive_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    session: Session = Depends(get_session)
):
    query = select(Approval)
    if drive_id:
        query = query.where(Approval.drive_id == drive_id)
    if status:
        query = query.where(Approval.status == status)
    query = query.order_by(Approval.created_at.desc())
    approvals = session.exec(query).all()

    items = []
    for a in approvals:
        drive = session.get(PlacementDrive, a.drive_id)
        items.append({
            "id": a.id,
            "drive_id": a.drive_id,
            "drive_title": f"{drive.employer_name} - {drive.drive_title}" if drive else "Unknown Drive",
            "employer_name": drive.employer_name if drive else "Unknown",
            "roster_hash": a.roster_hash,
            "criteria_version": a.criteria_version,
            "eligible_count": a.eligible_count,
            "destination_url": a.destination_url,
            "approver_name": a.approver_name,
            "approver_email": a.approver_email,
            "status": a.status,
            "rejection_reason": a.rejection_reason,
            "created_at": a.created_at.isoformat(),
            "approved_at": a.approved_at.isoformat() if a.approved_at else None
        })
    return items

@router.post("")
def prepare_approval_request(
    data: ApprovalCreate,
    session: Session = Depends(get_session)
):
    drive = session.get(PlacementDrive, data.drive_id)
    if not drive:
        raise HTTPException(status_code=404, detail=f"Drive {data.drive_id} not found.")

    results = session.exec(
        select(DriveEligibilityResult).where(
            DriveEligibilityResult.drive_id == drive.id,
            DriveEligibilityResult.is_eligible == True
        )
    ).all()

    if not results:
        raise HTTPException(status_code=400, detail="Cannot prepare approval: Drive has 0 evaluated eligible students. Run evaluation first.")

    eligible_ids = [r.student_id for r in results]
    destination = data.destination_url or drive.employer_form_url or "mock://employer.recruitment/v1/intake"

    approval = create_pending_approval(
        session=session,
        drive=drive,
        eligible_student_ids=eligible_ids,
        destination_url=destination,
        approver_name=data.approver_name,
        approver_email=data.approver_email
    )

    return {
        "status": "success",
        "approval_id": approval.id,
        "roster_hash": approval.roster_hash,
        "eligible_count": approval.eligible_count,
        "destination_url": approval.destination_url
    }

@router.get("/{approval_id}")
def get_approval_detail(approval_id: str, session: Session = Depends(get_session)):
    approval = session.get(Approval, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail=f"Approval {approval_id} not found.")

    drive = session.get(PlacementDrive, approval.drive_id)
    approved_student_ids = json.loads(approval.approved_student_ids_json)

    # Check validity in real-time
    current_results = session.exec(
        select(DriveEligibilityResult.student_id).where(
            DriveEligibilityResult.drive_id == approval.drive_id,
            DriveEligibilityResult.is_eligible == True
        )
    ).all()
    is_valid, validation_msg = verify_approval_validity(session, approval, drive, list(current_results)) if drive else (False, "Drive deleted")

    return {
        "approval": {
            "id": approval.id,
            "drive_id": approval.drive_id,
            "drive_title": f"{drive.employer_name} - {drive.drive_title}" if drive else "",
            "employer_name": drive.employer_name if drive else "",
            "roster_hash": approval.roster_hash,
            "criteria_version": approval.criteria_version,
            "eligible_count": approval.eligible_count,
            "student_ids": approved_student_ids,
            "destination_url": approval.destination_url,
            "approver_name": approval.approver_name,
            "approver_email": approval.approver_email,
            "status": approval.status,
            "is_valid": is_valid,
            "validity_message": validation_msg,
            "rejection_reason": approval.rejection_reason,
            "created_at": approval.created_at.isoformat(),
            "approved_at": approval.approved_at.isoformat() if approval.approved_at else None
        }
    }

@router.post("/{approval_id}/action")
def decide_approval(
    approval_id: str,
    decision_data: ApprovalDecision,
    session: Session = Depends(get_session)
):
    approval = session.get(Approval, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail=f"Approval {approval_id} not found.")

    drive = session.get(PlacementDrive, approval.drive_id)
    if not drive:
        raise HTTPException(status_code=404, detail="Associated drive not found.")

    if decision_data.decision.upper() == "APPROVE":
        approval.status = "APPROVED"
        approval.approver_name = decision_data.approver_name
        approval.approver_email = decision_data.approver_email
        approval.approved_at = datetime.now(timezone.utc)
        action_verb = "APPROVED"
        details = f"Roster of {approval.eligible_count} students approved by {decision_data.approver_name} ({decision_data.approver_email})."
    elif decision_data.decision.upper() == "REJECT":
        approval.status = "REJECTED"
        approval.rejection_reason = decision_data.rejection_reason or "Rejected by placement officer."
        action_verb = "REJECTED"
        details = f"Roster rejected by {decision_data.approver_name}. Reason: {approval.rejection_reason}"
    else:
        raise HTTPException(status_code=400, detail="Decision must be either 'APPROVE' or 'REJECT'.")

    session.add(approval)
    session.commit()
    session.refresh(approval)

    audit = AuditEvent(
        event_type=f"APPROVAL_{action_verb}",
        entity_type="Approval",
        entity_id=approval.id,
        actor=decision_data.approver_email,
        action_details=details,
        metadata_json=json.dumps({"roster_hash": approval.roster_hash, "decision": decision_data.decision})
    )
    session.add(audit)
    session.commit()

    return {
        "status": "success",
        "approval_id": approval.id,
        "new_status": approval.status,
        "message": details
    }
