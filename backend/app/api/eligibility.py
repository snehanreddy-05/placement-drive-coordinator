import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session, select
import pandas as pd
from app.database import get_session
from app.models.drive import PlacementDrive
from app.models.student import Student
from app.models.eligibility import DriveEligibilityResult
from app.models.audit import AuditEvent
from app.services.eligibility_engine import evaluate_roster_for_drive, RULES_ENGINE_VERSION

router = APIRouter(tags=["Eligibility"])

@router.post("/drives/{drive_id}/evaluate")
def evaluate_drive_eligibility(drive_id: str, session: Session = Depends(get_session)):
    drive = session.get(PlacementDrive, drive_id)
    if not drive:
        raise HTTPException(status_code=404, detail=f"Placement drive {drive_id} not found.")

    students = session.exec(select(Student)).all()
    if not students:
        raise HTTPException(status_code=400, detail="Student roster is empty. Import or seed students before evaluating eligibility.")

    results = evaluate_roster_for_drive(students, drive)

    # Clean existing results for this drive
    existing = session.exec(select(DriveEligibilityResult).where(DriveEligibilityResult.drive_id == drive.id)).all()
    for ex in existing:
        session.delete(ex)
    session.commit()

    for r in results:
        session.add(r)
    session.commit()

    eligible_count = sum(1 for r in results if r.is_eligible)
    excluded_count = len(results) - eligible_count

    audit = AuditEvent(
        event_type="ELIGIBILITY_EVALUATION",
        entity_type="DriveEligibilityResult",
        entity_id=drive.id,
        actor="placement-officer",
        action_details=f"Evaluated {len(results)} students for drive '{drive.employer_name}': {eligible_count} eligible, {excluded_count} excluded.",
        metadata_json=json.dumps({"eligible_count": eligible_count, "excluded_count": excluded_count, "rules_version": RULES_ENGINE_VERSION})
    )
    session.add(audit)
    session.commit()

    return {
        "status": "success",
        "drive_id": drive.id,
        "employer_name": drive.employer_name,
        "total_evaluated": len(results),
        "eligible_count": eligible_count,
        "excluded_count": excluded_count,
        "rules_version": RULES_ENGINE_VERSION
    }

@router.get("/drives/{drive_id}/eligibility")
def get_drive_eligibility(
    drive_id: str,
    status: Optional[str] = Query(None, description="FILTER: 'eligible' or 'excluded'"),
    search: Optional[str] = Query(None),
    session: Session = Depends(get_session)
):
    drive = session.get(PlacementDrive, drive_id)
    if not drive:
        raise HTTPException(status_code=404, detail=f"Placement drive {drive_id} not found.")

    query = select(DriveEligibilityResult).where(DriveEligibilityResult.drive_id == drive.id)
    if status == "eligible":
        query = query.where(DriveEligibilityResult.is_eligible == True)
    elif status == "excluded":
        query = query.where(DriveEligibilityResult.is_eligible == False)

    results = session.exec(query).all()

    # Join with student data
    student_ids = [r.student_id for r in results]
    students = session.exec(select(Student).where(Student.student_id.in_(student_ids))).all()
    stu_dict = {s.student_id: s for s in students}

    items = []
    for r in results:
        stu = stu_dict.get(r.student_id)
        if search:
            q = search.lower()
            name = stu.full_name.lower() if stu else ""
            sid = r.student_id.lower()
            if q not in name and q not in sid:
                continue

        items.append({
            "student_id": r.student_id,
            "full_name": stu.full_name if stu else "Unknown",
            "email": stu.email if stu else "",
            "branch": stu.branch if stu else "",
            "cgpa": stu.cgpa if stu else None,
            "active_backlogs": stu.active_backlogs if stu else 0,
            "consent_given": stu.consent_given if stu else False,
            "is_eligible": r.is_eligible,
            "reason": r.reason,
            "failure_reasons": json.loads(r.failure_reasons_json),
            "rules_version": r.rules_version,
            "evaluated_at": r.evaluated_at.isoformat()
        })

    return {
        "drive": {
            "id": drive.id,
            "employer_name": drive.employer_name,
            "drive_title": drive.drive_title,
            "min_cgpa": drive.min_cgpa,
            "eligible_branches": drive.eligible_branches,
            "max_backlogs": drive.max_backlogs,
            "consent_required": drive.consent_required,
            "criteria_version": drive.criteria_version
        },
        "total_count": len(items),
        "students": items
    }

@router.get("/drives/{drive_id}/eligibility/export")
def export_eligibility_report(
    drive_id: str,
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    session: Session = Depends(get_session)
):
    drive = session.get(PlacementDrive, drive_id)
    if not drive:
        raise HTTPException(status_code=404, detail=f"Drive {drive_id} not found.")

    results = session.exec(select(DriveEligibilityResult).where(DriveEligibilityResult.drive_id == drive.id)).all()
    student_ids = [r.student_id for r in results]
    students = session.exec(select(Student).where(Student.student_id.in_(student_ids))).all()
    stu_dict = {s.student_id: s for s in students}

    rows = []
    for r in results:
        s = stu_dict.get(r.student_id)
        rows.append({
            "Student ID": r.student_id,
            "Name": s.full_name if s else "",
            "Email": s.email if s else "",
            "Branch": s.branch if s else "",
            "CGPA": s.cgpa if s else "",
            "Backlogs": s.active_backlogs if s else 0,
            "Consent": "YES" if (s and s.consent_given) else "NO",
            "Eligibility Status": "ELIGIBLE" if r.is_eligible else "EXCLUDED",
            "Primary Decision Reason": r.reason,
            "Applied Rules Version": r.rules_version,
            "Evaluated At": r.evaluated_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    df = pd.DataFrame(rows)
    if format == "csv":
        csv_data = df.to_csv(index=False).encode("utf-8")
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=eligibility_report_{drive.employer_name}.csv"}
        )
    else:
        import io
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Eligibility Analysis")
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=eligibility_report_{drive.employer_name}.xlsx"}
        )
