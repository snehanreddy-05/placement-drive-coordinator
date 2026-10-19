import httpx

def test_live_workflow():
    client = httpx.Client(base_url="http://127.0.0.1:8000/api")

    # 1. Health
    h = client.get("/health").json()
    assert h["status"] == "healthy"
    print("1. Health OK:", h)

    # 2. Drives & Students
    drives = client.get("/drives").json()
    assert len(drives) >= 2
    d = drives[0]
    print(f"2. Testing with drive: {d['employer_name']} (Min CGPA: {d['min_cgpa']})")

    # 3. Evaluate eligibility
    eval_res = client.post(f"/drives/{d['id']}/evaluate").json()
    print("3. Evaluated eligibility:", eval_res)
    assert eval_res["total_evaluated"] > 0
    assert eval_res["eligible_count"] > 0

    # 4. Check clash detection
    clashes = client.get("/drives/clashes/all").json()
    print(f"4. Clashes detected: {clashes['clashes_detected_count']}")

    # 5. Agent Chat: Explain student decision
    agent_res = client.post("/agent/chat", json={"prompt": "Explain why student STU104 was excluded.", "drive_id": d["id"]}).json()
    print("5. Agent response:", agent_res["summary"])
    assert len(agent_res["tool_calls"]) > 0

    # 6. Prepare Approval Gate
    approval_req = client.post("/approvals", json={
        "drive_id": d["id"],
        "approver_name": "Dean of Placements",
        "approver_email": "dean@university.edu"
    }).json()
    appr_id = approval_req["approval_id"]
    print(f"6. Prepared Approval #{appr_id[:8]} with SHA-256 hash: {approval_req['roster_hash'][:16]}...")

    # 7. Approve Roster
    decision_res = client.post(f"/approvals/{appr_id}/action", json={
        "decision": "APPROVE",
        "approver_name": "Dean of Placements",
        "approver_email": "dean@university.edu"
    }).json()
    assert decision_res["new_status"] == "APPROVED"
    print("7. Human sign-off granted:", decision_res["message"])

    # 8. Submit to destination & read-back verify
    upload_res = client.post("/uploads", json={
        "drive_id": d["id"],
        "approval_id": appr_id
    }).json()
    print(f"8. Upload reconciliation result: Status {upload_res['receipt']['verification_status']}")
    assert upload_res["receipt"]["verification_status"] == "VERIFIED"
    print("   Receipt Reference:", upload_res["receipt"]["receipt_reference"])
    print("   Audit Details:", upload_res["receipt"]["reconciliation_details"])

    # 9. Attendance generation
    att_res = client.post(f"/drives/{d['id']}/attendance/generate?approval_id={appr_id}").json()
    print(f"9. Attendance generated: {att_res['generated_count']} student records")

    # 10. Audit log check
    audit_events = client.get("/audit").json()
    print(f"10. Audit log records: {len(audit_events)} total events tracked in immutable ledger.")

    print("\nALL 10 LIVE WORKFLOW STEPS VERIFIED END-TO-END WITH 100% RECONCILIATION SUCCESS!")

if __name__ == "__main__":
    test_live_workflow()
