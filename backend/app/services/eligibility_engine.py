import json
from typing import List, Dict, Any, Tuple
from app.models.student import Student
from app.models.drive import PlacementDrive
from app.models.eligibility import DriveEligibilityResult

RULES_ENGINE_VERSION = "2026.1-deterministic"

def evaluate_student_eligibility(student: Student, drive: PlacementDrive) -> Tuple[bool, List[str], str]:
    """
    Evaluates a single student against a placement drive's criteria using strict deterministic rules.
    Returns (is_eligible, failure_reasons, summary_reason).
    """
    failure_reasons: List[str] = []

    # 1. Missing data checks - never treat missing data as satisfying a criterion
    if student.cgpa is None:
        failure_reasons.append("CGPA data is missing.")
    if not student.branch or student.branch.strip() == "":
        failure_reasons.append("Branch data is missing.")
    if student.active_backlogs is None:
        failure_reasons.append("Active backlogs data is missing.")

    if failure_reasons:
        return False, failure_reasons, "Unresolved: " + "; ".join(failure_reasons)

    # 2. CGPA threshold evaluation (explicit boundary: cgpa >= min_cgpa is eligible)
    if student.cgpa < drive.min_cgpa:
        failure_reasons.append(
            f"CGPA {student.cgpa:.2f} is below minimum required threshold of {drive.min_cgpa:.2f}."
        )

    # 3. Branch eligibility (case-insensitive normalized set)
    eligible_branches_set = {b.strip().upper() for b in drive.eligible_branches.split(",") if b.strip()}
    student_branch_norm = student.branch.strip().upper()
    if student_branch_norm not in eligible_branches_set:
        failure_reasons.append(
            f"Branch '{student.branch}' is not in the eligible list: {', '.join(sorted(eligible_branches_set))}."
        )

    # 4. Backlog policy (explicit boundary: student.active_backlogs <= drive.max_backlogs)
    if student.active_backlogs > drive.max_backlogs:
        if drive.max_backlogs == 0:
            failure_reasons.append(
                f"Student has {student.active_backlogs} active backlogs (drive policy requires 0 active backlogs)."
            )
        else:
            failure_reasons.append(
                f"Student has {student.active_backlogs} active backlogs (maximum permitted is {drive.max_backlogs})."
            )

    # 5. Consent requirement
    if drive.consent_required and not student.consent_given:
        failure_reasons.append("Student placement consent is missing or not granted for this drive.")

    # Outcome
    if not failure_reasons:
        return True, [], "Meets all criteria: CGPA, branch, backlog limits, and consent verified."
    else:
        return False, failure_reasons, "Excluded: " + "; ".join(failure_reasons)

def evaluate_roster_for_drive(students: List[Student], drive: PlacementDrive) -> List[DriveEligibilityResult]:
    """
    Evaluates an entire student roster against a drive and constructs DriveEligibilityResult records.
    """
    results: List[DriveEligibilityResult] = []
    for student in students:
        is_eligible, failure_reasons, summary_reason = evaluate_student_eligibility(student, drive)
        results.append(
            DriveEligibilityResult(
                drive_id=drive.id,
                student_id=student.student_id,
                is_eligible=is_eligible,
                reason=summary_reason,
                failure_reasons_json=json.dumps(failure_reasons),
                rules_version=RULES_ENGINE_VERSION
            )
        )
    return results
