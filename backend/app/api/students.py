import io
import json
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, Response
from sqlmodel import Session, select
import pandas as pd
from app.database import get_session
from app.models.student import Student, StudentCreate, StudentRead, RosterImportRecord
from app.models.eligibility import DriveEligibilityResult
from app.models.audit import AuditEvent
from app.services.roster_parser import parse_roster_file

router = APIRouter(prefix="/students", tags=["Students"])

@router.post("/import")
async def import_student_roster(
    file: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    contents = await file.read()
    try:
        valid_rows, invalid_rows, summary = parse_roster_file(contents, file.filename or "roster.csv")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    # Check for existing student ID duplicates in DB
    existing_students = session.exec(select(Student.student_id)).all()
    existing_set = set(existing_students)

    imported_count = 0
    skipped_existing = 0

    for row in valid_rows:
        stu_id = row["student_id"]
        if stu_id in existing_set:
            # Update existing
            existing_obj = session.get(Student, stu_id)
            if existing_obj:
                existing_obj.full_name = row["full_name"]
                existing_obj.email = row["email"]
                existing_obj.branch = row["branch"]
                existing_obj.cgpa = row["cgpa"]
                existing_obj.active_backlogs = row["active_backlogs"]
                existing_obj.consent_given = row["consent_given"]
                existing_obj.updated_at = datetime.now(timezone.utc)
                session.add(existing_obj)
                skipped_existing += 1
        else:
            new_student = Student(**row)
            session.add(new_student)
            existing_set.add(stu_id)
            imported_count += 1

    # Save import history record
    import_rec = RosterImportRecord(
        filename=file.filename or "upload.csv",
        total_rows=summary["total_rows"],
        valid_rows=summary["valid_rows_count"],
        invalid_rows=summary["invalid_rows_count"],
        error_summary=json.dumps([{"row": ir["row_number"], "errors": ir["errors"]} for ir in invalid_rows[:10]])
    )
    session.add(import_rec)

    # Log audit event
    audit = AuditEvent(
        event_type="ROSTER_IMPORT",
        entity_type="StudentRoster",
        entity_id=file.filename or "roster.csv",
        actor="placement-officer",
        action_details=f"Imported roster file '{file.filename}': {imported_count} new, {skipped_existing} updated, {len(invalid_rows)} rejected rows.",
        metadata_json=json.dumps(summary)
    )
    session.add(audit)
    session.commit()

    return {
        "status": "success",
        "summary": summary,
        "imported_new": imported_count,
        "updated_existing": skipped_existing,
        "invalid_rows": invalid_rows
    }

@router.get("/template/download")
def download_sample_template():
    df = pd.DataFrame([
        {
            "student_id": "STU101",
            "full_name": "Aarav Sharma",
            "email": "aarav.sharma@college.edu",
            "branch": "CSE",
            "cgpa": 8.75,
            "active_backlogs": 0,
            "consent_given": "TRUE"
        },
        {
            "student_id": "STU102",
            "full_name": "Diya Patel",
            "email": "diya.patel@college.edu",
            "branch": "IT",
            "cgpa": 7.40,
            "active_backlogs": 1,
            "consent_given": "TRUE"
        },
        {
            "student_id": "STU103",
            "full_name": "Rohan Gupta",
            "email": "rohan.gupta@college.edu",
            "branch": "ECE",
            "cgpa": 6.85,
            "active_backlogs": 0,
            "consent_given": "FALSE"
        }
    ])
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=placement_roster_template.csv"}
    )

@router.post("/seed-demo")
def seed_demo_students(session: Session = Depends(get_session)):
    demo_students = [
        {"student_id": "STU101", "full_name": "Aarav Sharma", "email": "aarav.sharma@campus.edu", "branch": "CSE", "cgpa": 9.20, "active_backlogs": 0, "consent_given": True, "is_sample": True},
        {"student_id": "STU102", "full_name": "Diya Patel", "email": "diya.patel@campus.edu", "branch": "CSE", "cgpa": 8.50, "active_backlogs": 0, "consent_given": True, "is_sample": True},
        {"student_id": "STU103", "full_name": "Rohan Gupta", "email": "rohan.gupta@campus.edu", "branch": "IT", "cgpa": 7.80, "active_backlogs": 0, "consent_given": True, "is_sample": True},
        {"student_id": "STU104", "full_name": "Ananya Verma", "email": "ananya.verma@campus.edu", "branch": "ECE", "cgpa": 6.40, "active_backlogs": 1, "consent_given": True, "is_sample": True},
        {"student_id": "STU105", "full_name": "Kabir Mehta", "email": "kabir.mehta@campus.edu", "branch": "MECH", "cgpa": 7.10, "active_backlogs": 0, "consent_given": True, "is_sample": True},
        {"student_id": "STU106", "full_name": "Ishita Rao", "email": "ishita.rao@campus.edu", "branch": "CSE", "cgpa": 6.00, "active_backlogs": 0, "consent_given": True, "is_sample": True},
        {"student_id": "STU107", "full_name": "Siddharth Jain", "email": "siddharth.jain@campus.edu", "branch": "IT", "cgpa": 5.80, "active_backlogs": 2, "consent_given": True, "is_sample": True},
        {"student_id": "STU108", "full_name": "Neha Nambiar", "email": "neha.nambiar@campus.edu", "branch": "CSE", "cgpa": 8.90, "active_backlogs": 0, "consent_given": False, "is_sample": True},
        {"student_id": "STU109", "full_name": "Arjun Menon", "email": "arjun.menon@campus.edu", "branch": "ECE", "cgpa": 8.10, "active_backlogs": 0, "consent_given": True, "is_sample": True},
        {"student_id": "STU110", "full_name": "Pooja Reddy", "email": "pooja.reddy@campus.edu", "branch": "CSE", "cgpa": 7.50, "active_backlogs": 0, "consent_given": True, "is_sample": True},
        {"student_id": "STU111", "full_name": "Vikram Sen", "email": "vikram.sen@campus.edu", "branch": "IT", "cgpa": 6.95, "active_backlogs": 0, "consent_given": True, "is_sample": True},
        {"student_id": "STU112", "full_name": "Sneha Kulkarni", "email": "sneha.kulkarni@campus.edu", "branch": "ECE", "cgpa": 7.30, "active_backlogs": 1, "consent_given": True, "is_sample": True},
        {"student_id": "STU113", "full_name": "Karthik Iyer", "email": "karthik.iyer@campus.edu", "branch": "MECH", "cgpa": 8.40, "active_backlogs": 0, "consent_given": False, "is_sample": True},
        {"student_id": "STU114", "full_name": "Tanya Saxena", "email": "tanya.saxena@campus.edu", "branch": "CSE", "cgpa": 9.60, "active_backlogs": 0, "consent_given": True, "is_sample": True},
        {"student_id": "STU115", "full_name": "Aditya Joshi", "email": "aditya.joshi@campus.edu", "branch": "IT", "cgpa": 6.20, "active_backlogs": 0, "consent_given": True, "is_sample": True}
    ]

    added = 0
    for data in demo_students:
        existing = session.get(Student, data["student_id"])
        if not existing:
            stu = Student(**data)
            session.add(stu)
            added += 1

    session.commit()
    return {"status": "success", "seeded_count": added, "message": f"Seeded {added} synthetic student records."}

@router.get("", response_model=List[StudentRead])
def get_students(
    search: Optional[str] = Query(None),
    branch: Optional[str] = Query(None),
    consent: Optional[bool] = Query(None),
    offset: int = 0,
    limit: int = 50,
    session: Session = Depends(get_session)
):
    query = select(Student)
    if branch:
        query = query.where(Student.branch == branch.upper())
    if consent is not None:
        query = query.where(Student.consent_given == consent)
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Student.student_id.ilike(search_pattern)) |
            (Student.full_name.ilike(search_pattern)) |
            (Student.email.ilike(search_pattern))
        )
    query = query.order_by(Student.student_id).offset(offset).limit(limit)
    return session.exec(query).all()

@router.get("/{student_id}")
def get_student_detail(student_id: str, session: Session = Depends(get_session)):
    student = session.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found.")

    eligibility_history = session.exec(
        select(DriveEligibilityResult).where(DriveEligibilityResult.student_id == student_id)
    ).all()

    return {
        "student": student,
        "eligibility_history": [
            {
                "drive_id": e.drive_id,
                "is_eligible": e.is_eligible,
                "reason": e.reason,
                "failure_reasons": json.loads(e.failure_reasons_json),
                "evaluated_at": e.evaluated_at.isoformat()
            } for e in eligibility_history
        ]
    }
