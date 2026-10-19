from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlmodel import Session, select
from app.database import get_session
from app.models.student import Student
from app.models.drive import PlacementDrive
from app.models.eligibility import DriveEligibilityResult
from app.models.approval import Approval
from app.models.upload import UploadJob, UploadReceipt
from app.models.agent import AgentExecution

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/summary")
def get_dashboard_summary(
    drive_id: Optional[str] = Query(None, description="Filter eligibility metrics for a specific drive"),
    session: Session = Depends(get_session)
):
    total_students = len(session.exec(select(Student)).all())
    active_drives = len(session.exec(select(PlacementDrive).where(PlacementDrive.status == "Active")).all())
    total_drives = len(session.exec(select(PlacementDrive)).all())
    pending_approvals = len(session.exec(select(Approval).where(Approval.status == "PENDING")).all())
    verified_uploads = len(session.exec(select(UploadReceipt).where(UploadReceipt.verification_status == "VERIFIED")).all())

    # Eligibility metrics
    selected_drive_id = drive_id
    if not selected_drive_id:
        latest_drive = session.exec(select(PlacementDrive).order_by(PlacementDrive.created_at.desc())).first()
        if latest_drive:
            selected_drive_id = latest_drive.id

    eligible_count = 0
    excluded_count = 0
    selected_drive_title = None

    if selected_drive_id:
        drive_obj = session.get(PlacementDrive, selected_drive_id)
        if drive_obj:
            selected_drive_title = f"{drive_obj.employer_name} - {drive_obj.drive_title}"
            results = session.exec(select(DriveEligibilityResult).where(DriveEligibilityResult.drive_id == selected_drive_id)).all()
            eligible_count = sum(1 for r in results if r.is_eligible)
            excluded_count = len(results) - eligible_count

    # Recent activity
    recent_drives = session.exec(select(PlacementDrive).order_by(PlacementDrive.created_at.desc()).limit(5)).all()
    recent_uploads = session.exec(select(UploadReceipt).order_by(UploadReceipt.verified_at.desc()).limit(5)).all()
    recent_agent_runs = session.exec(select(AgentExecution).order_by(AgentExecution.created_at.desc()).limit(5)).all()

    return {
        "metrics": {
            "total_students": total_students,
            "active_drives": active_drives,
            "total_drives": total_drives,
            "selected_drive_id": selected_drive_id,
            "selected_drive_title": selected_drive_title,
            "eligible_students": eligible_count,
            "excluded_students": excluded_count,
            "pending_approvals": pending_approvals,
            "verified_uploads": verified_uploads
        },
        "recent_drives": [
            {
                "id": d.id,
                "employer_name": d.employer_name,
                "drive_title": d.drive_title,
                "min_cgpa": d.min_cgpa,
                "status": d.status,
                "start_time": d.start_time.isoformat()
            } for d in recent_drives
        ],
        "recent_uploads": [
            {
                "id": u.id,
                "drive_id": u.drive_id,
                "receipt_reference": u.receipt_reference,
                "verification_status": u.verification_status,
                "expected_count": u.expected_count,
                "actual_destination_count": u.actual_destination_count,
                "reconciliation_details": u.reconciliation_details,
                "verified_at": u.verified_at.isoformat()
            } for u in recent_uploads
        ],
        "recent_agent_executions": [
            {
                "id": a.id,
                "prompt": a.prompt,
                "status": a.status,
                "summary": a.summary,
                "tools_used": a.tool_calls_count,
                "created_at": a.created_at.isoformat()
            } for a in recent_agent_runs
        ]
    }
