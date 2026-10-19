import io
import json
import pytest
from datetime import datetime, timezone, timedelta
from sqlmodel import Session, create_engine, SQLModel, select

from app.models.student import Student
from app.models.drive import PlacementDrive
from app.models.eligibility import DriveEligibilityResult
from app.models.approval import Approval
from app.models.upload import UploadJob, UploadReceipt
from app.models.attendance import AttendanceRecord
from app.services.roster_parser import parse_roster_file
from app.services.eligibility_engine import evaluate_student_eligibility, evaluate_roster_for_drive
from app.services.clash_detector import check_time_interval_overlap, detect_clashes_for_drives
from app.services.approval_service import compute_roster_hash, create_pending_approval, verify_approval_validity
from app.services.upload_service import execute_approved_upload
from app.services.mock_destination import mock_destination_service
from app.services.attendance_service import generate_attendance_sheet_for_drive
from app.services.agent_service import AgentOrchestrator

# Setup in-memory SQLite DB for tests
@pytest.fixture(name="db_session")
def fixture_db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="sample_drive")
def fixture_sample_drive(db_session: Session):
    now = datetime.now(timezone.utc)
    drive = PlacementDrive(
        id="drive-test-1",
        employer_name="Apex Global",
        drive_title="Associate SWE Drive",
        min_cgpa=7.0,
        eligible_branches="CSE,IT,ECE",
        max_backlogs=0,
        consent_required=True,
        registration_deadline=now + timedelta(days=2),
        start_time=now + timedelta(days=5, hours=9),
        end_time=now + timedelta(days=5, hours=17),
        venue="Main Auditorium",
        employer_form_url="mock://apex.recruitment/v1/intake",
        status="Active",
        criteria_version=1
    )
    db_session.add(drive)
    db_session.commit()
    db_session.refresh(drive)
    return drive

# 1. Student meets every eligibility criterion
def test_case_01_student_meets_every_criterion(sample_drive):
    stu = Student(student_id="STU01", full_name="Alice A", email="alice@test.edu", branch="CSE", cgpa=8.5, active_backlogs=0, consent_given=True)
    is_eligible, reasons, summary = evaluate_student_eligibility(stu, sample_drive)
    assert is_eligible is True
    assert len(reasons) == 0
    assert "Meets all criteria" in summary

# 2. CGPA is exactly at the minimum threshold
def test_case_02_cgpa_exactly_at_threshold(sample_drive):
    stu = Student(student_id="STU02", full_name="Bob B", email="bob@test.edu", branch="IT", cgpa=7.0, active_backlogs=0, consent_given=True)
    is_eligible, reasons, _ = evaluate_student_eligibility(stu, sample_drive)
    assert is_eligible is True
    assert len(reasons) == 0

# 3. CGPA is below the threshold
def test_case_03_cgpa_below_threshold(sample_drive):
    stu = Student(student_id="STU03", full_name="Charlie C", email="charlie@test.edu", branch="CSE", cgpa=6.99, active_backlogs=0, consent_given=True)
    is_eligible, reasons, _ = evaluate_student_eligibility(stu, sample_drive)
    assert is_eligible is False
    assert any("below minimum required threshold" in r for r in reasons)

# 4. Branch is not eligible
def test_case_04_branch_not_eligible(sample_drive):
    stu = Student(student_id="STU04", full_name="David D", email="david@test.edu", branch="MECH", cgpa=8.5, active_backlogs=0, consent_given=True)
    is_eligible, reasons, _ = evaluate_student_eligibility(stu, sample_drive)
    assert is_eligible is False
    assert any("not in the eligible list" in r for r in reasons)

# 5. Active backlog violates employer criteria
def test_case_05_active_backlog_violates_criteria(sample_drive):
    stu = Student(student_id="STU05", full_name="Eve E", email="eve@test.edu", branch="ECE", cgpa=8.0, active_backlogs=1, consent_given=True)
    is_eligible, reasons, _ = evaluate_student_eligibility(stu, sample_drive)
    assert is_eligible is False
    assert any("active backlogs" in r for r in reasons)

# 6. Consent is missing or false
def test_case_06_consent_missing_or_false(sample_drive):
    stu = Student(student_id="STU06", full_name="Frank F", email="frank@test.edu", branch="CSE", cgpa=8.2, active_backlogs=0, consent_given=False)
    is_eligible, reasons, _ = evaluate_student_eligibility(stu, sample_drive)
    assert is_eligible is False
    assert any("consent is missing or not granted" in r for r in reasons)

# 7. Required student data is missing
def test_case_07_required_student_data_missing(sample_drive):
    stu = Student(student_id="STU07", full_name="Grace G", email="grace@test.edu", branch="", cgpa=None, active_backlogs=0, consent_given=True)
    is_eligible, reasons, summary = evaluate_student_eligibility(stu, sample_drive)
    assert is_eligible is False
    assert "Unresolved" in summary
    assert any("missing" in r for r in reasons)

# 8. Duplicate student IDs appear in an import
def test_case_08_duplicate_student_ids_in_import():
    csv_data = (
        "student_id,full_name,email,branch,cgpa,active_backlogs,consent_given\n"
        "STU100,User 1,u1@test.edu,CSE,8.0,0,true\n"
        "STU100,User 2,u2@test.edu,IT,8.5,0,true\n"
    ).encode("utf-8")
    valid_rows, invalid_rows, summary = parse_roster_file(csv_data, "test.csv")
    assert len(valid_rows) == 1
    assert len(invalid_rows) == 1
    assert any("Duplicate student ID" in err for err in invalid_rows[0]["errors"])

# 9. Invalid CGPA or malformed input is rejected
def test_case_09_invalid_cgpa_rejected():
    csv_data = (
        "student_id,full_name,email,branch,cgpa,active_backlogs,consent_given\n"
        "STU200,User 1,u1@test.edu,CSE,12.5,0,true\n"
        "STU201,User 2,u2@test.edu,IT,not_a_number,0,true\n"
    ).encode("utf-8")
    valid_rows, invalid_rows, _ = parse_roster_file(csv_data, "test.csv")
    assert len(valid_rows) == 0
    assert len(invalid_rows) == 2
    assert any("out of valid range" in err for err in invalid_rows[0]["errors"])
    assert any("Malformed CGPA" in err for err in invalid_rows[1]["errors"])

# 10. Overlapping drives are detected correctly
def test_case_10_overlapping_drives_detected():
    now = datetime.now(timezone.utc)
    d1 = PlacementDrive(id="d1", employer_name="A", drive_title="T1", min_cgpa=6.0, eligible_branches="CSE", registration_deadline=now, start_time=now + timedelta(hours=10), end_time=now + timedelta(hours=15))
    d2 = PlacementDrive(id="d2", employer_name="B", drive_title="T2", min_cgpa=6.0, eligible_branches="CSE", registration_deadline=now, start_time=now + timedelta(hours=12), end_time=now + timedelta(hours=18))
    clashes = detect_clashes_for_drives([d1, d2])
    assert len(clashes) == 1
    assert clashes[0].clash_type == "SCHEDULE_OVERLAP"

# 11. Non-overlapping drives are not flagged
def test_case_11_non_overlapping_drives_not_flagged():
    now = datetime.now(timezone.utc)
    # Consecutive drives: end of d1 == start of d2 (boundary case)
    d1 = PlacementDrive(id="d1", employer_name="A", drive_title="T1", min_cgpa=6.0, eligible_branches="CSE", registration_deadline=now, start_time=now + timedelta(hours=9), end_time=now + timedelta(hours=12))
    d2 = PlacementDrive(id="d2", employer_name="B", drive_title="T2", min_cgpa=6.0, eligible_branches="CSE", registration_deadline=now, start_time=now + timedelta(hours=12), end_time=now + timedelta(hours=15))
    clashes = detect_clashes_for_drives([d1, d2])
    assert len(clashes) == 0

# 12. Approval is required before upload
def test_case_12_approval_required_before_upload(db_session, sample_drive):
    unapproved = Approval(
        drive_id=sample_drive.id,
        roster_hash="dummy_hash",
        criteria_version=sample_drive.criteria_version,
        eligible_count=1,
        approved_student_ids_json=json.dumps(["STU01"]),
        destination_url="mock://apex/intake",
        approver_name="Officer",
        approver_email="officer@test.edu",
        status="PENDING" # Not approved yet!
    )
    db_session.add(unapproved)
    db_session.commit()

    with pytest.raises(PermissionError) as exc_info:
        execute_approved_upload(db_session, sample_drive.id, unapproved.id)
    assert "Approval is not in APPROVED state" in str(exc_info.value)

# 13. Approval is invalidated after the prepared roster changes
def test_case_13_approval_invalidated_after_roster_change(db_session, sample_drive):
    stu_list = ["STU01", "STU02"]
    approval = create_pending_approval(db_session, sample_drive, stu_list, sample_drive.employer_form_url, "Officer", "officer@test.edu")
    approval.status = "APPROVED"
    db_session.add(approval)
    db_session.commit()

    # Now roster changes (e.g. only STU01 is eligible now)
    changed_roster = ["STU01"]
    is_valid, msg = verify_approval_validity(db_session, approval, sample_drive, changed_roster)
    assert is_valid is False
    assert "Approval invalidated" in msg
    assert approval.status == "INVALIDATED"

# 14. A valid approval permits the authorized upload workflow
def test_case_14_valid_approval_permits_upload(db_session, sample_drive):
    mock_destination_service.clear()
    stu_list = ["STU01", "STU02"]
    approval = create_pending_approval(db_session, sample_drive, stu_list, sample_drive.employer_form_url, "Officer", "officer@test.edu")
    approval.status = "APPROVED"
    db_session.add(approval)
    db_session.commit()

    job, receipt = execute_approved_upload(db_session, sample_drive.id, approval.id)
    assert job.status == "VERIFIED"
    assert receipt is not None
    assert receipt.verification_status == "VERIFIED"

# 15. Upload succeeds and all IDs reconcile
def test_case_15_upload_succeeds_and_all_ids_reconcile(db_session, sample_drive):
    mock_destination_service.clear()
    stu_list = ["STU10", "STU20", "STU30"]
    approval = create_pending_approval(db_session, sample_drive, stu_list, sample_drive.employer_form_url, "Officer", "officer@test.edu")
    approval.status = "APPROVED"
    db_session.add(approval)
    db_session.commit()

    job, receipt = execute_approved_upload(db_session, sample_drive.id, approval.id)
    assert receipt.verification_status == "VERIFIED"
    assert receipt.expected_count == 3
    assert receipt.actual_destination_count == 3
    assert receipt.matched_count == 3
    assert len(json.loads(receipt.missing_ids_json)) == 0
    assert len(json.loads(receipt.unexpected_ids_json)) == 0

# 16. Uploaded count is wrong
def test_case_16_uploaded_count_wrong_detected(db_session, sample_drive):
    mock_destination_service.clear()
    stu_list = ["STU01", "STU02", "STU03"]
    approval = create_pending_approval(db_session, sample_drive, stu_list, sample_drive.employer_form_url, "Officer", "officer@test.edu")
    approval.status = "APPROVED"
    db_session.add(approval)
    db_session.commit()

    # Simulate wrong count at destination
    job, receipt = execute_approved_upload(db_session, sample_drive.id, approval.id, simulation_mode="WRONG_COUNT")
    assert job.status == "MISMATCH"
    assert receipt.verification_status == "MISMATCH"
    assert "Count mismatch" in receipt.reconciliation_details

# 17. A student ID is missing from the destination
def test_case_17_missing_student_id_detected(db_session, sample_drive):
    mock_destination_service.clear()
    stu_list = ["STU01", "STU02"]
    approval = create_pending_approval(db_session, sample_drive, stu_list, sample_drive.employer_form_url, "Officer", "officer@test.edu")
    approval.status = "APPROVED"
    db_session.add(approval)
    db_session.commit()

    job, receipt = execute_approved_upload(db_session, sample_drive.id, approval.id, simulation_mode="MISSING_ID")
    assert receipt.verification_status == "MISMATCH"
    missing = json.loads(receipt.missing_ids_json)
    assert len(missing) > 0
    assert "missing IDs" in receipt.reconciliation_details

# 18. An unexpected student ID appears at the destination
def test_case_18_unexpected_student_id_detected(db_session, sample_drive):
    mock_destination_service.clear()
    stu_list = ["STU01", "STU02"]
    approval = create_pending_approval(db_session, sample_drive, stu_list, sample_drive.employer_form_url, "Officer", "officer@test.edu")
    approval.status = "APPROVED"
    db_session.add(approval)
    db_session.commit()

    job, receipt = execute_approved_upload(db_session, sample_drive.id, approval.id, simulation_mode="UNEXPECTED_ID")
    assert receipt.verification_status == "MISMATCH"
    unexpected = json.loads(receipt.unexpected_ids_json)
    assert "STU_ROGUE_999" in unexpected

# 19. Duplicate uploaded IDs are detected
def test_case_19_duplicate_ids_detected(db_session, sample_drive):
    mock_destination_service.clear()
    stu_list = ["STU01", "STU02"]
    approval = create_pending_approval(db_session, sample_drive, stu_list, sample_drive.employer_form_url, "Officer", "officer@test.edu")
    approval.status = "APPROVED"
    db_session.add(approval)
    db_session.commit()

    job, receipt = execute_approved_upload(db_session, sample_drive.id, approval.id, simulation_mode="DUPLICATE_ID")
    assert receipt.verification_status == "MISMATCH"
    dups = json.loads(receipt.duplicate_ids_json)
    assert len(dups) > 0

# 20. Destination failure does not produce a false success
def test_case_20_destination_failure_handled(db_session, sample_drive):
    mock_destination_service.clear()
    stu_list = ["STU01"]
    approval = create_pending_approval(db_session, sample_drive, stu_list, sample_drive.employer_form_url, "Officer", "officer@test.edu")
    approval.status = "APPROVED"
    db_session.add(approval)
    db_session.commit()

    job, receipt = execute_approved_upload(db_session, sample_drive.id, approval.id, simulation_mode="FAILURE")
    assert job.status == "Failed"
    assert receipt.verification_status == "FAILED"
    assert "HTTP 500" in receipt.reconciliation_details

# 21. Retry after an uncertain result does not silently duplicate the upload
def test_case_21_idempotent_retry_prevents_duplicate(db_session, sample_drive):
    mock_destination_service.clear()
    stu_list = ["STU01"]
    approval = create_pending_approval(db_session, sample_drive, stu_list, sample_drive.employer_form_url, "Officer", "officer@test.edu")
    approval.status = "APPROVED"
    db_session.add(approval)
    db_session.commit()

    key = "IDEMP-TEST-KEY-123"
    job1, receipt1 = execute_approved_upload(db_session, sample_drive.id, approval.id, idempotency_key=key)
    # Retry with same idempotency key
    job2, receipt2 = execute_approved_upload(db_session, sample_drive.id, approval.id, idempotency_key=key)

    assert job1.id == job2.id
    assert receipt1.id == receipt2.id

# 22. Attendance export contains the correct approved students
def test_case_22_attendance_export_contains_approved_students(db_session, sample_drive):
    stu1 = Student(student_id="STU01", full_name="Alice A", email="alice@test.edu", branch="CSE", cgpa=9.0, active_backlogs=0, consent_given=True)
    stu2 = Student(student_id="STU02", full_name="Bob B", email="bob@test.edu", branch="IT", cgpa=8.0, active_backlogs=0, consent_given=True)
    db_session.add(stu1)
    db_session.add(stu2)
    db_session.commit()

    approval = create_pending_approval(db_session, sample_drive, ["STU01", "STU02"], sample_drive.employer_form_url, "Officer", "officer@test.edu")
    approval.status = "APPROVED"
    db_session.add(approval)
    db_session.commit()

    records, csv_str, xlsx_bytes = generate_attendance_sheet_for_drive(db_session, sample_drive.id, approval.id)
    assert len(records) == 2
    assert "STU01" in csv_str
    assert "STU02" in csv_str
    assert "Not Marked" in csv_str
    assert len(xlsx_bytes) > 0

# 23. Unauthorized state-changing requests are rejected
def test_case_23_unauthorized_state_change_rejected(db_session, sample_drive):
    # If drive criteria version has changed, an approval cannot authorize upload
    approval = create_pending_approval(db_session, sample_drive, ["STU01"], sample_drive.employer_form_url, "Officer", "officer@test.edu")
    approval.status = "APPROVED"
    db_session.add(approval)
    db_session.commit()

    # Criteria changes
    sample_drive.criteria_version = 2
    db_session.add(sample_drive)
    db_session.commit()

    with pytest.raises(PermissionError) as exc_info:
        execute_approved_upload(db_session, sample_drive.id, approval.id)
    assert "criteria was updated" in str(exc_info.value)

# 24. The application operates without LLM credentials in fallback mode
def test_case_24_fallback_mode_operational(db_session, sample_drive):
    stu = Student(student_id="STU104", full_name="Ananya Verma", email="ananya@test.edu", branch="ECE", cgpa=6.4, active_backlogs=1, consent_given=True)
    db_session.add(stu)
    db_session.commit()

    orchestrator = AgentOrchestrator(db_session)
    execution = orchestrator.run_agent("Explain why student STU104 was excluded.", drive_id_context=sample_drive.id)
    assert execution.status == "COMPLETED"
    assert "STU104" in execution.summary
    assert "EXCLUDED" in execution.summary
    assert execution.provider_used == "deterministic"
    assert execution.tool_calls_count > 0
