import io
import os
import json
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel

import app.models  # Ensure all SQLModel tables are registered in metadata
from app.main import app as fastapi_app
from app.database import get_session
from app.models.drive import PlacementDrive
from app.services.mock_destination import mock_destination_service

@pytest.fixture(name="client")
def fixture_client():
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(test_engine)

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    fastapi_app.dependency_overrides[get_session] = override_get_session
    mock_destination_service.clear()
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()

def test_full_e2e_placementos_workflow(client: TestClient):
    """
    Validates the exact 10-step end-to-end workflow specified in the hackathon prompt:
    1. Import & validate synthetic student CSV
    2. Configure employer criteria
    3. Evaluate eligibility deterministically
    4. Display eligible/excluded counts & explainable reasons
    5. Detect overlapping drive schedules
    6. Prepare immutable versioned roster with SHA-256 fingerprint
    7. Require explicit human approval (reject unapproved upload attempts)
    8. Submit approved roster to mock destination
    9. Read back destination records & reconcile IDs and count
    10. Generate upload receipt and attendance sheet
    """
    # Step 1: Import synthetic student CSV
    csv_content = (
        "student_id,full_name,email,branch,cgpa,active_backlogs,consent_given\n"
        "STU101,Aarav Sharma,aarav@campus.edu,CSE,9.20,0,TRUE\n"
        "STU102,Diya Patel,diya@campus.edu,CSE,8.50,0,TRUE\n"
        "STU103,Rohan Gupta,rohan@campus.edu,IT,7.80,0,TRUE\n"
        "STU104,Ananya Verma,ananya@campus.edu,ECE,6.40,1,TRUE\n"
        "STU105,Kabir Mehta,kabir@campus.edu,MECH,7.10,0,TRUE\n"
        "STU106,Ishita Rao,ishita@campus.edu,CSE,6.00,0,TRUE\n"
        "STU107,Siddharth Jain,siddharth@campus.edu,IT,5.80,2,TRUE\n"
        "STU108,Neha Nambiar,neha@campus.edu,CSE,8.90,0,FALSE\n"
    ).encode("utf-8")

    import_resp = client.post(
        "/api/students/import",
        files={"file": ("synthetic_roster.csv", io.BytesIO(csv_content), "text/csv")}
    )
    assert import_resp.status_code == 200
    summary = import_resp.json()["summary"]
    assert summary["total_rows"] == 8
    assert summary["valid_rows_count"] == 8

    # Step 2: Configure 2 Drives with overlapping schedules for clash detection
    now = datetime.now(timezone.utc)
    drive1_resp = client.post("/api/drives", json={
        "employer_name": "Google Cloud",
        "drive_title": "Software Engineering Campus Drive",
        "min_cgpa": 7.5,
        "eligible_branches": "CSE,IT",
        "max_backlogs": 0,
        "consent_required": True,
        "registration_deadline": (now + timedelta(days=2)).isoformat(),
        "start_time": (now + timedelta(days=5, hours=9)).isoformat(),
        "end_time": (now + timedelta(days=5, hours=17)).isoformat(),
        "venue": "Main Auditorium",
        "employer_form_url": "mock://google.careers/campus/intake/2026",
        "status": "Active"
    })
    assert drive1_resp.status_code == 200
    drive1_id = drive1_resp.json()["id"]

    drive2_resp = client.post("/api/drives", json={
        "employer_name": "Microsoft",
        "drive_title": "Cloud Systems Engineer Drive",
        "min_cgpa": 7.0,
        "eligible_branches": "CSE,IT,ECE",
        "max_backlogs": 1,
        "consent_required": True,
        "registration_deadline": (now + timedelta(days=3)).isoformat(),
        "start_time": (now + timedelta(days=5, hours=14)).isoformat(),  # Overlaps with drive1
        "end_time": (now + timedelta(days=5, hours=20)).isoformat(),
        "venue": "Tech Lab 2",
        "employer_form_url": "mock://microsoft.careers/v1/intake",
        "status": "Active"
    })
    assert drive2_resp.status_code == 200
    drive2_id = drive2_resp.json()["id"]

    # Step 3 & 4: Evaluate students using deterministic Python rules & display counts/reasons
    eval_resp = client.post(f"/api/drives/{drive1_id}/evaluate")
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["total_evaluated"] == 8
    # Eligible should be STU101 (9.2), STU102 (8.5), STU103 (7.8) = 3 students
    # STU104: CGPA 6.4 < 7.5, 1 backlog > 0, ECE not in CSE,IT
    # STU105: MECH not in CSE,IT
    # STU106: CGPA 6.0 < 7.5
    # STU107: CGPA 5.8 < 7.5, backlogs 2 > 0
    # STU108: consent is FALSE
    assert eval_data["eligible_count"] == 3
    assert eval_data["excluded_count"] == 5

    # Check explainable reasons endpoint
    elig_list = client.get(f"/api/drives/{drive1_id}/eligibility").json()
    assert len(elig_list["students"]) == 8
    stu104 = next(s for s in elig_list["students"] if s["student_id"] == "STU104")
    assert stu104["is_eligible"] is False
    assert len(stu104["failure_reasons"]) >= 2

    # Step 5: Detect schedule clashes
    clashes_resp = client.get("/api/drives/clashes/all").json()
    assert clashes_resp["clashes_detected_count"] >= 1
    assert any("Google Cloud" in c["drive1_title"] or "Google Cloud" in c["drive2_title"] for c in clashes_resp["clashes"])

    # Step 6: Prepare immutable versioned upload roster with SHA-256 fingerprint
    prep_resp = client.post("/api/approvals", json={
        "drive_id": drive1_id,
        "approver_name": "Dean of Engineering",
        "approver_email": "dean@campus.edu"
    })
    assert prep_resp.status_code == 200
    appr_id = prep_resp.json()["approval_id"]
    roster_hash = prep_resp.json()["roster_hash"]
    assert len(roster_hash) == 64  # SHA-256 hex string

    # Step 7: Require explicit human approval before any upload
    # Attempting to upload while status is PENDING must be blocked (HTTP 403)
    blocked_upload = client.post("/api/uploads", json={
        "drive_id": drive1_id,
        "approval_id": appr_id
    })
    assert blocked_upload.status_code == 403
    assert "Approval is not in APPROVED state" in blocked_upload.json()["detail"]

    # Explicit human sign-off
    decision_resp = client.post(f"/api/approvals/{appr_id}/action", json={
        "decision": "APPROVE",
        "approver_name": "Dean of Engineering",
        "approver_email": "dean@campus.edu"
    })
    assert decision_resp.status_code == 200
    assert decision_resp.json()["new_status"] == "APPROVED"

    # Step 8 & 9: Submit to mock destination and read-back reconcile
    upload_resp = client.post("/api/uploads", json={
        "drive_id": drive1_id,
        "approval_id": appr_id
    })
    assert upload_resp.status_code == 200
    receipt = upload_resp.json()["receipt"]
    assert receipt["verification_status"] == "VERIFIED"
    assert receipt["expected_count"] == 3
    assert receipt["actual_destination_count"] == 3
    assert receipt["matched_count"] == 3
    assert receipt["missing_ids"] == []
    assert receipt["unexpected_ids"] == []

    # Step 10: Generate real upload receipt and attendance sheet
    # Download receipt JSON
    receipt_dl = client.get(f"/api/uploads/{upload_resp.json()['upload_job_id']}/receipt/download")
    assert receipt_dl.status_code == 200
    assert "RCPT-EMP-" in receipt_dl.text

    # Generate attendance sheet
    att_gen = client.post(f"/api/drives/{drive1_id}/attendance/generate?approval_id={appr_id}")
    assert att_gen.status_code == 200
    assert att_gen.json()["generated_count"] == 3

    # Export attendance CSV
    att_csv = client.get(f"/api/drives/{drive1_id}/attendance/export?format=csv")
    assert att_csv.status_code == 200
    assert "STU101" in att_csv.text
    assert "Not Marked" in att_csv.text

    # Export attendance XLSX
    att_xlsx = client.get(f"/api/drives/{drive1_id}/attendance/export?format=xlsx")
    assert att_xlsx.status_code == 200
    assert len(att_xlsx.content) > 1000
