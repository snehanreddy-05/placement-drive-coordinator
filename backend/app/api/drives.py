from typing import List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.database import get_session
from app.models.drive import PlacementDrive, PlacementDriveCreate, PlacementDriveUpdate, PlacementDriveRead
from app.models.audit import AuditEvent

router = APIRouter(prefix="/drives", tags=["Placement Drives"])

@router.get("", response_model=List[PlacementDriveRead])
def list_drives(
    status: Optional[str] = Query(None),
    session: Session = Depends(get_session)
):
    query = select(PlacementDrive)
    if status:
        query = query.where(PlacementDrive.status == status)
    query = query.order_by(PlacementDrive.start_time)
    drives = session.exec(query).all()

    # If no drives exist, auto-seed 2 representative demo drives
    if not drives:
        now = datetime.now(timezone.utc)
        d1 = PlacementDrive(
            employer_name="Google Cloud",
            drive_title="Software Engineering Drive 2026",
            min_cgpa=7.5,
            eligible_branches="CSE,IT,ECE",
            max_backlogs=0,
            consent_required=True,
            registration_deadline=now + timedelta(days=5),
            start_time=now + timedelta(days=10, hours=9),
            end_time=now + timedelta(days=10, hours=17),
            venue="Auditorium Block A & Online Portal",
            employer_form_url="mock://google.careers/campus/intake/2026",
            status="Active",
            criteria_version=1
        )
        d2 = PlacementDrive(
            employer_name="Microsoft",
            drive_title="Cloud & Systems Engineer Drive",
            min_cgpa=7.0,
            eligible_branches="CSE,IT,ECE,MECH",
            max_backlogs=1,
            consent_required=True,
            registration_deadline=now + timedelta(days=7),
            start_time=now + timedelta(days=10, hours=14), # Overlaps with d1 intentionally for clash test
            end_time=now + timedelta(days=10, hours=20),
            venue="Tech Center Lab 2",
            employer_form_url="mock://microsoft.recruitment/v1/intake",
            status="Active",
            criteria_version=1
        )
        session.add(d1)
        session.add(d2)
        session.commit()
        session.refresh(d1)
        session.refresh(d2)
        return [d1, d2]

    return drives

@router.post("", response_model=PlacementDriveRead)
def create_drive(drive_in: PlacementDriveCreate, session: Session = Depends(get_session)):
    # Validate schedule interval
    if drive_in.start_time >= drive_in.end_time:
        raise HTTPException(status_code=400, detail="Drive start time must be before end time.")
    if drive_in.registration_deadline > drive_in.start_time:
        raise HTTPException(status_code=400, detail="Registration deadline must be before or at drive start time.")

    drive = PlacementDrive(**drive_in.model_dump())
    session.add(drive)
    session.commit()
    session.refresh(drive)

    audit = AuditEvent(
        event_type="DRIVE_CREATED",
        entity_type="PlacementDrive",
        entity_id=drive.id,
        actor="placement-officer",
        action_details=f"Created placement drive '{drive.employer_name} - {drive.drive_title}' with min CGPA {drive.min_cgpa}."
    )
    session.add(audit)
    session.commit()

    return drive

@router.get("/{drive_id}", response_model=PlacementDriveRead)
def get_drive(drive_id: str, session: Session = Depends(get_session)):
    drive = session.get(PlacementDrive, drive_id)
    if not drive:
        raise HTTPException(status_code=404, detail=f"Placement drive {drive_id} not found.")
    return drive

@router.patch("/{drive_id}", response_model=PlacementDriveRead)
def update_drive(drive_id: str, drive_update: PlacementDriveUpdate, session: Session = Depends(get_session)):
    drive = session.get(PlacementDrive, drive_id)
    if not drive:
        raise HTTPException(status_code=404, detail=f"Placement drive {drive_id} not found.")

    update_dict = drive_update.model_dump(exclude_unset=True)

    # Criteria changes trigger criteria_version bump, invalidating prior approvals
    criteria_fields = ["min_cgpa", "eligible_branches", "max_backlogs", "consent_required"]
    has_criteria_change = any(field in update_dict for field in criteria_fields)

    for key, value in update_dict.items():
        setattr(drive, key, value)

    if has_criteria_change:
        drive.criteria_version += 1

    drive.updated_at = datetime.now(timezone.utc)
    session.add(drive)
    session.commit()
    session.refresh(drive)

    audit = AuditEvent(
        event_type="DRIVE_UPDATED",
        entity_type="PlacementDrive",
        entity_id=drive.id,
        actor="placement-officer",
        action_details=f"Updated drive '{drive.employer_name}'. Criteria version now v{drive.criteria_version}."
    )
    session.add(audit)
    session.commit()

    return drive
