import io
import json
from typing import List, Tuple
from datetime import datetime, timezone
import pandas as pd
from sqlmodel import Session, select
from app.models.drive import PlacementDrive
from app.models.student import Student
from app.models.approval import Approval
from app.models.attendance import AttendanceRecord
from app.models.audit import AuditEvent

def generate_attendance_sheet_for_drive(
    session: Session,
    drive_id: str,
    approval_id: str
) -> Tuple[List[AttendanceRecord], str, bytes]:
    """
    Generates attendance records for the approved roster, defaulting status to 'Not Marked'.
    Returns (records, csv_content, xlsx_bytes).
    """
    drive = session.get(PlacementDrive, drive_id)
    if not drive:
        raise ValueError(f"Drive {drive_id} not found.")

    approval = session.get(Approval, approval_id)
    if not approval or approval.status != "APPROVED":
        raise ValueError(f"Valid approval required to generate official attendance sheet.")

    approved_student_ids: List[str] = json.loads(approval.approved_student_ids_json)
    
    # Query student details
    students_query = session.exec(select(Student).where(Student.student_id.in_(approved_student_ids))).all()
    students_by_id = {s.student_id: s for s in students_query}

    records: List[AttendanceRecord] = []
    rows = []

    # Clean existing attendance records for this drive and roster hash to avoid duplicates
    existing_records = session.exec(
        select(AttendanceRecord).where(
            AttendanceRecord.drive_id == drive.id,
            AttendanceRecord.roster_hash == approval.roster_hash
        )
    ).all()
    for er in existing_records:
        session.delete(er)
    session.commit()

    now_utc = datetime.now(timezone.utc)
    for stu_id in approved_student_ids:
        stu = students_by_id.get(stu_id)
        name = stu.full_name if stu else "Unknown"
        branch = stu.branch if stu else "N/A"

        rec = AttendanceRecord(
            drive_id=drive.id,
            student_id=stu_id,
            student_name=name,
            branch=branch,
            drive_title=f"{drive.employer_name} - {drive.drive_title}",
            attendance_status="Not Marked",
            notes="",
            roster_hash=approval.roster_hash,
            generated_at=now_utc
        )
        records.append(rec)
        session.add(rec)

        rows.append({
            "Student ID": stu_id,
            "Student Name": name,
            "Branch": branch,
            "Drive Title": f"{drive.employer_name} - {drive.drive_title}",
            "Attendance Status": "Not Marked",
            "Check-in Time": "",
            "Notes": "",
            "Roster Hash": approval.roster_hash[:16],
            "Generated At (UTC)": now_utc.strftime("%Y-%m-%d %H:%M:%S")
        })

    session.commit()

    # Generate CSV & XLSX
    df = pd.DataFrame(rows)
    csv_content = df.to_csv(index=False)
    
    xlsx_buffer = io.BytesIO()
    with pd.ExcelWriter(xlsx_buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Attendance Sheet")
    xlsx_bytes = xlsx_buffer.getvalue()

    # Audit log
    audit = AuditEvent(
        event_type="ATTENDANCE_GENERATED",
        entity_type="AttendanceRecord",
        entity_id=drive.id,
        actor="system",
        action_details=f"Generated attendance sheet with {len(records)} students for drive '{drive.employer_name}'.",
        metadata_json=json.dumps({"drive_id": drive.id, "roster_hash": approval.roster_hash})
    )
    session.add(audit)
    session.commit()

    return records, csv_content, xlsx_bytes
