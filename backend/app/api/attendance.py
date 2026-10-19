from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session, select
from app.database import get_session
from app.models.drive import PlacementDrive
from app.models.approval import Approval
from app.models.attendance import AttendanceRecord
from app.services.attendance_service import generate_attendance_sheet_for_drive

router = APIRouter(tags=["Attendance"])

class AttendanceUpdateRequest(BaseModel):
    attendance_status: str # "Present", "Absent", "Excused", "Not Marked"
    notes: Optional[str] = None

@router.get("/drives/{drive_id}/attendance")
def get_drive_attendance(drive_id: str, session: Session = Depends(get_session)):
    drive = session.get(PlacementDrive, drive_id)
    if not drive:
        raise HTTPException(status_code=404, detail=f"Drive {drive_id} not found.")

    records = session.exec(
        select(AttendanceRecord).where(AttendanceRecord.drive_id == drive_id).order_by(AttendanceRecord.student_id)
    ).all()

    return {
        "drive_id": drive_id,
        "employer_name": drive.employer_name,
        "total_records": len(records),
        "present_count": sum(1 for r in records if r.attendance_status == "Present"),
        "absent_count": sum(1 for r in records if r.attendance_status == "Absent"),
        "not_marked_count": sum(1 for r in records if r.attendance_status == "Not Marked"),
        "records": [
            {
                "id": r.id,
                "student_id": r.student_id,
                "student_name": r.student_name,
                "branch": r.branch,
                "status": r.attendance_status,
                "check_in_time": r.check_in_time.isoformat() if r.check_in_time else None,
                "notes": r.notes,
                "roster_hash": r.roster_hash,
                "generated_at": r.generated_at.isoformat()
            } for r in records
        ]
    }

@router.post("/drives/{drive_id}/attendance/generate")
def create_drive_attendance(
    drive_id: str,
    approval_id: Optional[str] = Query(None),
    session: Session = Depends(get_session)
):
    drive = session.get(PlacementDrive, drive_id)
    if not drive:
        raise HTTPException(status_code=404, detail=f"Drive {drive_id} not found.")

    # Find valid approval if not provided
    appr = None
    if approval_id:
        appr = session.get(Approval, approval_id)
    else:
        appr = session.exec(
            select(Approval).where(Approval.drive_id == drive_id, Approval.status == "APPROVED").order_by(Approval.created_at.desc())
        ).first()

    if not appr:
        raise HTTPException(status_code=400, detail="Cannot generate attendance: An APPROVED roster is required before generating attendance.")

    records, csv_str, _ = generate_attendance_sheet_for_drive(session, drive_id, appr.id)
    return {
        "status": "success",
        "generated_count": len(records),
        "roster_hash": appr.roster_hash,
        "message": f"Successfully generated attendance roster of {len(records)} students."
    }

@router.get("/drives/{drive_id}/attendance/export")
def export_drive_attendance(
    drive_id: str,
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    session: Session = Depends(get_session)
):
    drive = session.get(PlacementDrive, drive_id)
    if not drive:
        raise HTTPException(status_code=404, detail=f"Drive {drive_id} not found.")

    records = session.exec(
        select(AttendanceRecord).where(AttendanceRecord.drive_id == drive_id).order_by(AttendanceRecord.student_id)
    ).all()

    if not records:
        # Check if an approval exists to auto-generate
        appr = session.exec(
            select(Approval).where(Approval.drive_id == drive_id, Approval.status == "APPROVED").order_by(Approval.created_at.desc())
        ).first()
        if appr:
            records, _, _ = generate_attendance_sheet_for_drive(session, drive_id, appr.id)
        else:
            raise HTTPException(status_code=400, detail="No attendance records found and no approved roster available.")

    import pandas as pd
    rows = [
        {
            "Student ID": r.student_id,
            "Student Name": r.student_name,
            "Branch": r.branch,
            "Drive Title": r.drive_title,
            "Attendance Status": r.attendance_status,
            "Check-in Time": r.check_in_time.strftime("%Y-%m-%d %H:%M:%S") if r.check_in_time else "",
            "Notes": r.notes or "",
            "Roster Fingerprint": r.roster_hash[:16],
            "Generated At": r.generated_at.strftime("%Y-%m-%d %H:%M:%S")
        } for r in records
    ]
    df = pd.DataFrame(rows)

    if format == "csv":
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        return Response(
            content=csv_bytes,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=attendance_{drive.employer_name}.csv"}
        )
    else:
        import io
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Attendance Sheet")
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=attendance_{drive.employer_name}.xlsx"}
        )

@router.patch("/attendance/{record_id}")
def update_attendance_status(
    record_id: str,
    update_data: AttendanceUpdateRequest,
    session: Session = Depends(get_session)
):
    rec = session.get(AttendanceRecord, record_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Attendance record {record_id} not found.")

    rec.attendance_status = update_data.attendance_status
    if update_data.notes is not None:
        rec.notes = update_data.notes
    if update_data.attendance_status == "Present" and not rec.check_in_time:
        rec.check_in_time = datetime.now(timezone.utc)

    session.add(rec)
    session.commit()
    session.refresh(rec)

    return {
        "status": "success",
        "record_id": rec.id,
        "new_attendance_status": rec.attendance_status,
        "check_in_time": rec.check_in_time.isoformat() if rec.check_in_time else None
    }
