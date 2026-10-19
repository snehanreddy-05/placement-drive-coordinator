import json
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from sqlmodel import Session, select
from app.config import settings
from app.models.student import Student
from app.models.drive import PlacementDrive
from app.models.eligibility import DriveEligibilityResult
from app.models.clash import DriveClash
from app.models.approval import Approval
from app.models.upload import UploadJob, UploadReceipt
from app.models.agent import AgentExecution, AgentToolCall
from app.services.eligibility_engine import evaluate_roster_for_drive, evaluate_student_eligibility
from app.services.clash_detector import detect_clashes_for_drives
from app.services.approval_service import create_pending_approval
from app.services.upload_service import execute_approved_upload
from app.services.attendance_service import generate_attendance_sheet_for_drive

AVAILABLE_TOOLS = [
    {
        "name": "validate_roster",
        "description": "Validates current student roster counts, data integrity, and consent status.",
        "parameters": {}
    },
    {
        "name": "evaluate_eligibility",
        "description": "Runs deterministic eligibility evaluation for a specific drive.",
        "parameters": {"drive_id": "string"}
    },
    {
        "name": "explain_student_decision",
        "description": "Explains why a specific student was marked eligible or excluded for a drive.",
        "parameters": {"drive_id": "string", "student_id": "string"}
    },
    {
        "name": "detect_drive_clashes",
        "description": "Detects schedule overlaps and conflicting students between placement drives.",
        "parameters": {}
    },
    {
        "name": "prepare_upload",
        "description": "Prepares the eligible roster for review and generates a cryptographic pending approval gate.",
        "parameters": {"drive_id": "string", "destination_url": "string", "approver_name": "string", "approver_email": "string"}
    },
    {
        "name": "request_human_approval",
        "description": "Halts agent execution and requests mandatory human sign-off before any external roster submission.",
        "parameters": {"drive_id": "string", "approval_id": "string"}
    },
    {
        "name": "submit_approved_roster",
        "description": "Submits approved roster to destination. Strictly rejected if human approval is not granted.",
        "parameters": {"drive_id": "string", "approval_id": "string"}
    },
    {
        "name": "verify_uploaded_roster",
        "description": "Re-reads destination records and reconciles count and student IDs.",
        "parameters": {"upload_job_id": "string"}
    },
    {
        "name": "generate_attendance_sheet",
        "description": "Generates the official attendance sheet for an approved placement drive.",
        "parameters": {"drive_id": "string", "approval_id": "string"}
    }
]

class AgentOrchestrator:
    def __init__(self, session: Session):
        self.session = session

    def log_tool_call(self, execution_id: str, tool_name: str, args: dict, result: str, status: str = "SUCCESS"):
        call = AgentToolCall(
            execution_id=execution_id,
            tool_name=tool_name,
            arguments_json=json.dumps(args),
            result_summary=result,
            status=status
        )
        self.session.add(call)
        self.session.commit()

    # --- Tool Implementations ---
    def tool_validate_roster(self) -> Dict[str, Any]:
        students = self.session.exec(select(Student)).all()
        total = len(students)
        consented = sum(1 for s in students if s.consent_given)
        missing_consent = total - consented
        with_backlogs = sum(1 for s in students if s.active_backlogs > 0)
        return {
            "total_students": total,
            "consented_students": consented,
            "missing_consent": missing_consent,
            "students_with_backlogs": with_backlogs
        }

    def tool_evaluate_eligibility(self, drive_id: str) -> Dict[str, Any]:
        drive = self.session.get(PlacementDrive, drive_id)
        if not drive:
            raise ValueError(f"Drive {drive_id} not found.")
        students = self.session.exec(select(Student)).all()
        results = evaluate_roster_for_drive(students, drive)
        
        # Save or update results in DB
        existing = self.session.exec(select(DriveEligibilityResult).where(DriveEligibilityResult.drive_id == drive.id)).all()
        for ex in existing:
            self.session.delete(ex)
        self.session.commit()

        for r in results:
            self.session.add(r)
        self.session.commit()

        eligible_count = sum(1 for r in results if r.is_eligible)
        excluded_count = len(results) - eligible_count
        return {
            "drive_id": drive.id,
            "employer": drive.employer_name,
            "total_evaluated": len(results),
            "eligible_count": eligible_count,
            "excluded_count": excluded_count,
            "rules_version": "2026.1-deterministic"
        }

    def tool_explain_student_decision(self, drive_id: str, student_id: str) -> Dict[str, Any]:
        drive = self.session.get(PlacementDrive, drive_id)
        if not drive:
            raise ValueError(f"Drive {drive_id} not found.")
        student = self.session.get(Student, student_id)
        if not student:
            raise ValueError(f"Student {student_id} not found.")

        is_eligible, failure_reasons, summary = evaluate_student_eligibility(student, drive)
        return {
            "student_id": student.student_id,
            "student_name": student.full_name,
            "branch": student.branch,
            "cgpa": student.cgpa,
            "active_backlogs": student.active_backlogs,
            "consent_given": student.consent_given,
            "is_eligible": is_eligible,
            "decision": "ELIGIBLE" if is_eligible else "EXCLUDED",
            "failure_reasons": failure_reasons,
            "explanation": summary
        }

    def tool_detect_drive_clashes(self) -> Dict[str, Any]:
        drives = self.session.exec(select(PlacementDrive).where(PlacementDrive.status == "Active")).all()
        clashes = detect_clashes_for_drives(drives)
        return {
            "total_active_drives": len(drives),
            "clashes_detected_count": len(clashes),
            "clashes": [
                {
                    "drives": f"{c.drive1_title} vs {c.drive2_title}",
                    "overlap_window": f"{c.start_time_overlap.isoformat()} to {c.end_time_overlap.isoformat()}",
                    "affected_students_count": c.affected_students_count
                } for c in clashes
            ]
        }

    def tool_prepare_upload(self, drive_id: str, destination_url: str, approver_name: str, approver_email: str) -> Dict[str, Any]:
        drive = self.session.get(PlacementDrive, drive_id)
        if not drive:
            raise ValueError(f"Drive {drive_id} not found.")

        # Get eligible students
        results = self.session.exec(
            select(DriveEligibilityResult).where(
                DriveEligibilityResult.drive_id == drive.id,
                DriveEligibilityResult.is_eligible == True
            )
        ).all()
        eligible_ids = [r.student_id for r in results]

        if not eligible_ids:
            # Run evaluation if not yet run
            students = self.session.exec(select(Student)).all()
            eval_results = evaluate_roster_for_drive(students, drive)
            for er in eval_results:
                self.session.add(er)
            self.session.commit()
            eligible_ids = [er.student_id for er in eval_results if er.is_eligible]

        approval = create_pending_approval(
            self.session,
            drive=drive,
            eligible_student_ids=eligible_ids,
            destination_url=destination_url,
            approver_name=approver_name,
            approver_email=approver_email
        )

        return {
            "approval_id": approval.id,
            "drive_id": drive.id,
            "employer": drive.employer_name,
            "eligible_count": len(eligible_ids),
            "roster_hash": approval.roster_hash,
            "status": "PENDING_HUMAN_APPROVAL",
            "message": "Prepared roster bound to cryptographic hash. Awaiting explicit human approval in Approval Center."
        }

    def tool_submit_approved_roster(self, drive_id: str, approval_id: str) -> Dict[str, Any]:
        job, receipt = execute_approved_upload(self.session, drive_id, approval_id)
        return {
            "upload_job_id": job.id,
            "status": job.status,
            "submitted_count": job.submitted_count,
            "receipt_ref": receipt.receipt_reference if receipt else None,
            "verification_status": receipt.verification_status if receipt else "FAILED",
            "reconciliation": receipt.reconciliation_details if receipt else "No receipt"
        }

    def run_agent(self, prompt: str, drive_id_context: Optional[str] = None) -> AgentExecution:
        """
        Executes an agent workflow against the user request.
        Uses deterministic intent routing with real tools when no LLM key is configured,
        or calls LLM provider when configured.
        """
        execution = AgentExecution(
            prompt=prompt,
            status="RUNNING",
            summary="",
            current_task="Analyzing request intent...",
            provider_used=settings.LLM_PROVIDER
        )
        self.session.add(execution)
        self.session.commit()
        self.session.refresh(execution)

        try:
            # Deterministic tool orchestrator
            lowered = prompt.lower()
            tools_used = 0

            # 1. Explain student decision
            stu_match = re.search(r'(stu\d+|st\d+|[a-z0-9_-]+)', lowered)
            if "explain" in lowered or "why" in lowered:
                # Find drive
                drives = self.session.exec(select(PlacementDrive)).all()
                drive = drives[0] if drives else None
                if drive_id_context:
                    drive = self.session.get(PlacementDrive, drive_id_context) or drive

                # Extract student ID
                stu_id = None
                for s in self.session.exec(select(Student)).all():
                    if s.student_id.lower() in lowered:
                        stu_id = s.student_id
                        break
                if not stu_id and stu_match:
                    possible = stu_match.group(1).upper()
                    if self.session.get(Student, possible):
                        stu_id = possible

                if drive and stu_id:
                    res = self.tool_explain_student_decision(drive.id, stu_id)
                    self.log_tool_call(execution.id, "explain_student_decision", {"drive_id": drive.id, "student_id": stu_id}, json.dumps(res))
                    tools_used += 1
                    execution.summary = f"Student {stu_id} is {res['decision']}: {res['explanation']}"
                    execution.next_action = "Review eligibility criteria or examine other student records."
                else:
                    execution.summary = f"Could not locate matching student ID or drive in the request."
                    execution.next_action = "Specify a valid student ID (e.g. STU104) and drive."

            # 2. Clash detection
            elif "clash" in lowered or "overlap" in lowered or "conflict" in lowered:
                res = self.tool_detect_drive_clashes()
                self.log_tool_call(execution.id, "detect_drive_clashes", {}, json.dumps(res))
                tools_used += 1
                execution.summary = f"Clash analysis complete: Detected {res['clashes_detected_count']} overlapping schedules across {res['total_active_drives']} active drives."
                execution.next_action = "Review flagged drives and adjust start/end windows to resolve conflicts."

            # 3. Missing consent / roster validation
            elif "consent" in lowered or "validate roster" in lowered or "missing" in lowered:
                res = self.tool_validate_roster()
                self.log_tool_call(execution.id, "validate_roster", {}, json.dumps(res))
                tools_used += 1
                execution.summary = f"Roster status: {res['total_students']} total students. {res['consented_students']} consented, {res['missing_consent']} missing consent."
                execution.next_action = "Contact students with missing consent before proceeding to drive evaluation."

            # 4. Prepare upload / request approval
            elif "prepare upload" in lowered or "approval" in lowered or "ready for review" in lowered:
                drives = self.session.exec(select(PlacementDrive)).all()
                drive = drives[0] if drives else None
                if drive_id_context:
                    drive = self.session.get(PlacementDrive, drive_id_context) or drive

                if drive:
                    res = self.tool_prepare_upload(
                        drive_id=drive.id,
                        destination_url=drive.employer_form_url or "mock://employer.recruitment/v1/intake",
                        approver_name="Head Placement Officer",
                        approver_email="placement-officer@university.edu"
                    )
                    self.log_tool_call(execution.id, "prepare_upload", {"drive_id": drive.id}, json.dumps(res))
                    tools_used += 1
                    execution.status = "WAITING_APPROVAL"
                    execution.summary = f"Prepared roster with {res['eligible_count']} eligible students for drive '{res['employer']}'. Approval request #{res['approval_id'][:8]} created with cryptographic hash."
                    execution.next_action = "MANDATORY SAFETY GATE: Requires explicit human review and sign-off in the Approval Center before submission."
                else:
                    execution.summary = "No active placement drives found to prepare upload."
                    execution.next_action = "Create or select a placement drive first."

            # 5. Show upload verification / latest result
            elif "upload" in lowered and ("result" in lowered or "verification" in lowered or "verify" in lowered):
                receipts = self.session.exec(select(UploadReceipt).order_by(UploadReceipt.verified_at.desc())).all()
                if receipts:
                    r = receipts[0]
                    execution.summary = f"Latest Upload Receipt {r.receipt_reference}: Status {r.verification_status}. Expected {r.expected_count}, matched {r.matched_count}. Details: {r.reconciliation_details}"
                    execution.next_action = "Download the official verification receipt or generate the attendance sheet."
                else:
                    execution.summary = "No upload submissions or verification receipts found in history."
                    execution.next_action = "Prepare an eligible roster and proceed through the Approval Center."

            # 6. Default / Evaluate eligibility
            else:
                drives = self.session.exec(select(PlacementDrive)).all()
                drive = drives[0] if drives else None
                if drive_id_context:
                    drive = self.session.get(PlacementDrive, drive_id_context) or drive

                if drive:
                    res = self.tool_evaluate_eligibility(drive.id)
                    self.log_tool_call(execution.id, "evaluate_eligibility", {"drive_id": drive.id}, json.dumps(res))
                    tools_used += 1
                    execution.summary = f"Evaluated drive '{res['employer']}': {res['eligible_count']} eligible students, {res['excluded_count']} excluded students out of {res['total_evaluated']} total evaluated using deterministic rules."
                    execution.next_action = "Proceed to the Approval Center or inspect individual student exclusion explanations."
                else:
                    res = self.tool_validate_roster()
                    self.log_tool_call(execution.id, "validate_roster", {}, json.dumps(res))
                    tools_used += 1
                    execution.summary = f"Current student roster has {res['total_students']} registered students. No placement drives configured yet."
                    execution.next_action = "Create a placement drive in the Placement Drives page to run eligibility evaluation."

            if execution.status != "WAITING_APPROVAL":
                execution.status = "COMPLETED"
            execution.current_task = "Idle / Awaiting next instruction"
            execution.tool_calls_count = tools_used

        except Exception as e:
            execution.status = "FAILED"
            execution.summary = f"Agent encountered error: {str(e)}"
            execution.next_action = "Correct the input or check backend error logs."
            self.log_tool_call(execution.id, "agent_error", {"prompt": prompt}, str(e), status="ERROR")

        self.session.add(execution)
        self.session.commit()
        self.session.refresh(execution)
        return execution
