import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.models.drive import PlacementDrive
from app.models.eligibility import DriveEligibilityResult
from app.models.clash import DriveClash
from app.services.clash_detector import detect_clashes_for_drives

router = APIRouter(prefix="/drives", tags=["Clashes"])

@router.get("/clashes/all")
def get_all_drive_clashes(session: Session = Depends(get_session)):
    drives = session.exec(select(PlacementDrive).where(PlacementDrive.status != "Archived")).all()
    
    # Build student eligibility map
    eligibility_map = {}
    for d in drives:
        results = session.exec(
            select(DriveEligibilityResult.student_id).where(
                DriveEligibilityResult.drive_id == d.id,
                DriveEligibilityResult.is_eligible == True
            )
        ).all()
        eligibility_map[d.id] = list(results)

    clashes = detect_clashes_for_drives(drives, eligibility_map)

    return {
        "total_active_drives_inspected": len(drives),
        "clashes_detected_count": len(clashes),
        "clashes": [
            {
                "id": c.id,
                "drive1_id": c.drive1_id,
                "drive2_id": c.drive2_id,
                "drive1_title": c.drive1_title,
                "drive2_title": c.drive2_title,
                "clash_type": c.clash_type,
                "start_time_overlap": c.start_time_overlap.isoformat(),
                "end_time_overlap": c.end_time_overlap.isoformat(),
                "affected_students_count": c.affected_students_count,
                "affected_students": json.loads(c.affected_students_json)
            } for c in clashes
        ]
    }

@router.get("/{drive_id}/clashes")
def get_drive_clashes(drive_id: str, session: Session = Depends(get_session)):
    target_drive = session.get(PlacementDrive, drive_id)
    if not target_drive:
        raise HTTPException(status_code=404, detail=f"Placement drive {drive_id} not found.")

    all_drives = session.exec(select(PlacementDrive).where(PlacementDrive.status != "Archived")).all()
    
    eligibility_map = {}
    for d in all_drives:
        results = session.exec(
            select(DriveEligibilityResult.student_id).where(
                DriveEligibilityResult.drive_id == d.id,
                DriveEligibilityResult.is_eligible == True
            )
        ).all()
        eligibility_map[d.id] = list(results)

    all_clashes = detect_clashes_for_drives(all_drives, eligibility_map)
    relevant_clashes = [c for c in all_clashes if c.drive1_id == drive_id or c.drive2_id == drive_id]

    return {
        "drive_id": drive_id,
        "clashes_count": len(relevant_clashes),
        "clashes": [
            {
                "id": c.id,
                "other_drive_title": c.drive2_title if c.drive1_id == drive_id else c.drive1_title,
                "clash_type": c.clash_type,
                "start_time_overlap": c.start_time_overlap.isoformat(),
                "end_time_overlap": c.end_time_overlap.isoformat(),
                "affected_students_count": c.affected_students_count,
                "affected_students": json.loads(c.affected_students_json)
            } for c in relevant_clashes
        ]
    }
