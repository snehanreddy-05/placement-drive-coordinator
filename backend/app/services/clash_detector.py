import json
from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone
from app.models.drive import PlacementDrive
from app.models.clash import DriveClash

def check_time_interval_overlap(start1: datetime, end1: datetime, start2: datetime, end2: datetime) -> Tuple[bool, datetime, datetime]:
    """
    Checks if two time intervals overlap strictly: max(s1, s2) < min(e1, e2).
    Boundary case: if end1 == start2, there is NO overlap.
    Returns (overlaps, overlap_start, overlap_end).
    """
    # Normalize timezones to UTC for comparison
    s1 = start1.astimezone(timezone.utc) if start1.tzinfo else start1.replace(tzinfo=timezone.utc)
    e1 = end1.astimezone(timezone.utc) if end1.tzinfo else end1.replace(tzinfo=timezone.utc)
    s2 = start2.astimezone(timezone.utc) if start2.tzinfo else start2.replace(tzinfo=timezone.utc)
    e2 = end2.astimezone(timezone.utc) if end2.tzinfo else end2.replace(tzinfo=timezone.utc)

    overlap_start = max(s1, s2)
    overlap_end = min(e1, e2)

    if overlap_start < overlap_end:
        return True, overlap_start, overlap_end
    return False, overlap_start, overlap_end

def detect_clashes_for_drives(
    drives: List[PlacementDrive],
    student_drive_map: Dict[str, List[str]] = None
) -> List[DriveClash]:
    """
    Detects pairwise schedule overlaps across drives.
    If student_drive_map is provided (mapping drive_id -> list of eligible/participating student_ids),
    calculates common affected students.
    """
    clashes: List[DriveClash] = []
    n = len(drives)

    for i in range(n):
        for j in range(i + 1, n):
            d1 = drives[i]
            d2 = drives[j]

            overlaps, ov_start, ov_end = check_time_interval_overlap(
                d1.start_time, d1.end_time, d2.start_time, d2.end_time
            )

            if overlaps:
                affected_students = []
                if student_drive_map and d1.id in student_drive_map and d2.id in student_drive_map:
                    s1_set = set(student_drive_map[d1.id])
                    s2_set = set(student_drive_map[d2.id])
                    affected_students = sorted(list(s1_set.intersection(s2_set)))

                clash = DriveClash(
                    drive1_id=d1.id,
                    drive2_id=d2.id,
                    drive1_title=f"{d1.employer_name} - {d1.drive_title}",
                    drive2_title=f"{d2.employer_name} - {d2.drive_title}",
                    clash_type="STUDENT_OVERLAP" if affected_students else "SCHEDULE_OVERLAP",
                    start_time_overlap=ov_start,
                    end_time_overlap=ov_end,
                    affected_students_count=len(affected_students),
                    affected_students_json=json.dumps(affected_students)
                )
                clashes.append(clash)

    return clashes
