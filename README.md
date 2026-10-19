# PlacementOS — Placement Drive Coordinator

[![Tests](https://img.shields.io/badge/tests-24%20passed-emerald)](https://github.com)
[![Next.js](https://img.shields.io/badge/frontend-Next.js%2016%20App%20Router-indigo)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI%200.115-blue)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/license-MIT-zinc)](LICENSE)

> **Ziro National Agentic AI Hackathon 2026**  
> **Category:** Education & Career AI  
> **Problem Statement:** Autonomous recruitment operations coordination: roster ingestion, deterministic eligibility evaluation, schedule clash detection, cryptographic human approval gating, mock destination transmission, destination read-back reconciliation, and official attendance sheet generation.

---

## 1. Product Overview

College placement officers face overwhelming operational friction when coordinating campus recruitment drives: filtering candidate rosters against conflicting employer criteria, detecting overlapping drive time slots, preventing unauthorized roster submissions, and verifying that employer recruitment portals accurately received the approved student records without dropped or injected IDs.

**PlacementOS** is an enterprise-grade AI-powered placement operations platform built with a **strict separation of intelligence and safety**:
- **Deterministic Rules Engine:** All eligibility decisions are 100% deterministic (no hallucinations, strict boundary logic, explainable justifications).
- **Mandatory Cryptographic Approval Gate:** Every roster is bound to a SHA-256 fingerprint, criteria version, and approver identity. Changes to criteria or students immediately invalidate prior sign-offs.
- **Automated Read-back Reconciliation:** Re-inspects destination storage, compares counts and student IDs, detects missing or unexpected candidates, and issues verifiable receipts.
- **Agentic Orchestration:** Controlled natural-language agent interface that invokes real application tools and respects server-side safety boundaries.

---

## 2. Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | Next.js (App Router), React, TypeScript (Strict Mode), Tailwind CSS, Lucide React, Recharts |
| **Backend** | Python 3.12, FastAPI, SQLModel / SQLAlchemy, Pydantic v2, Pandas, OpenPyXL |
| **Database** | SQLite (zero-config local development) / PostgreSQL (production) |
| **Agent Layer** | Controlled tool-calling orchestrator with Provider Abstraction (Deterministic local fallback + Gemini / OpenAI support) |
| **Testing** | Pytest (24 comprehensive business and safety test cases), End-to-end API integration tests |
| **Deployment** | Docker multi-stage builds, Docker Compose, CORS environment configuration |

---

## 3. Architecture & Data Flow

```
[ Candidate Roster (CSV / XLSX) ]
              │
              ▼
    [ Strict Schema Parser ] ──▶ Row-level Validation & Duplicate ID Rejection
              │
              ▼
   [ Deterministic Engine ] ──▶ Evaluates CGPA ≥ min, Branch ∈ set, Backlogs ≤ max, Consent
              │
              ▼
  [ Schedule Clash Detector ] ──▶ Time-interval overlap & Conflicted Student Detection
              │
              ▼
 [ Cryptographic Approval Gate ] ──▶ SHA-256(Drive ID + Criteria Version + Sorted IDs + Destination)
              │
      ┌───────┴──────────────────────────────┐
      │ Requires Explicit Human Sign-off     │
      │ Approver: Name, Email, Timestamp     │
      └───────┬──────────────────────────────┘
              │
              ▼
  [ Employer Destination Adapter ] ──▶ Mock Intake Server / Real Authorized Endpoint
              │
              ▼
 [ Read-Back Reconciliation Engine ] ──▶ Re-reads stored destination IDs & counts
              │
      ┌───────┴─────────────────────────────────────────────┐
      │ • Expected count == Destination count               │
      │ • 0 Missing IDs, 0 Unexpected IDs, 0 Duplicates     │
      └───────┬─────────────────────────────────────────────┘
              │
              ├──▶ Status: VERIFIED ──▶ Issues Downloadable Intake Receipt (JSON)
              └──▶ Official Attendance Sheet Generator (CSV / XLSX with Check-in Tracking)
```

---

## 4. Key Capabilities & Safety Controls

### A. Explainable Deterministic Eligibility
- Boundary conditions tested: `CGPA == threshold` is eligible; `CGPA < threshold` is excluded.
- Branch comparison is case-insensitive normalized (`CSE`, `IT`, `ECE`, etc.).
- Active backlogs strictly capped at employer threshold (including strict no-backlog policy).
- Missing data is **never silently assumed** to satisfy criteria—it is flagged as `Unresolved` and excluded until rectified.
- Generates precise human-readable justifications for every candidate.

### B. Schedule Clash Detection
- Timezone-aware interval arithmetic checks if $\max(S_1, S_2) < \min(E_1, E_2)$.
- Boundary case: contiguous drives where $E_1 = S_2$ are not flagged as clashing.
- Pinpoints specific overlapping student candidates registered for both conflicting drives.

### C. Cryptographic Approval Gate (Non-Bypassable)
- External roster submission is **server-side blocked** without an approved gate record.
- The gate binds: `SHA-256(drive_id | criteria_version | sorted_student_ids | destination_url)`.
- If an administrator updates drive criteria (e.g. raises minimum CGPA) or adds/removes students, the criteria version increments and the hash mismatches—**automatically invalidating the approval**.

### D. Automated Read-Back Reconciliation
- Submissions are marked `VERIFIED` only if the actual records at the destination match the approved roster 100%.
- Detects count discrepancies, missing student IDs, injected rogue IDs, and duplicate transmissions.
- Supports idempotency keys to prevent double-submissions on network retries.

### E. Controlled Agent Orchestrator
- Operates in **Honest Deterministic Mode** when no external LLM API key is present.
- Executes real application tools: `validate_roster`, `evaluate_eligibility`, `explain_student_decision`, `detect_drive_clashes`, `prepare_upload`, `request_human_approval`, `submit_approved_roster`, `verify_uploaded_roster`, and `generate_attendance_sheet`.
- Logs safe execution traces with input arguments, output summaries, and timestamps.

---

## 5. Automated Test Evidence

All **24 required test cases** from Section 8 of the specification have been implemented in `backend/tests/test_all_requirements.py` and pass with 100% success:

```
tests/test_all_requirements.py::test_case_01_student_meets_every_criterion PASSED
tests/test_all_requirements.py::test_case_02_cgpa_exactly_at_threshold PASSED
tests/test_all_requirements.py::test_case_03_cgpa_below_threshold PASSED
tests/test_all_requirements.py::test_case_04_branch_not_eligible PASSED
tests/test_all_requirements.py::test_case_05_active_backlog_violates_criteria PASSED
tests/test_all_requirements.py::test_case_06_consent_missing_or_false PASSED
tests/test_all_requirements.py::test_case_07_required_student_data_missing PASSED
tests/test_all_requirements.py::test_case_08_duplicate_student_ids_in_import PASSED
tests/test_all_requirements.py::test_case_09_invalid_cgpa_rejected PASSED
tests/test_all_requirements.py::test_case_10_overlapping_drives_detected PASSED
tests/test_all_requirements.py::test_case_11_non_overlapping_drives_not_flagged PASSED
tests/test_all_requirements.py::test_case_12_approval_required_before_upload PASSED
tests/test_all_requirements.py::test_case_13_approval_invalidated_after_roster_change PASSED
tests/test_all_requirements.py::test_case_14_valid_approval_permits_upload PASSED
tests/test_all_requirements.py::test_case_15_upload_succeeds_and_all_ids_reconcile PASSED
tests/test_all_requirements.py::test_case_16_uploaded_count_wrong_detected PASSED
tests/test_all_requirements.py::test_case_17_missing_student_id_detected PASSED
tests/test_all_requirements.py::test_case_18_unexpected_student_id_detected PASSED
tests/test_all_requirements.py::test_case_19_duplicate_ids_detected PASSED
tests/test_all_requirements.py::test_case_20_destination_failure_handled PASSED
tests/test_all_requirements.py::test_case_21_idempotent_retry_prevents_duplicate PASSED
tests/test_all_requirements.py::test_case_22_attendance_export_contains_approved_students PASSED
tests/test_all_requirements.py::test_case_23_unauthorized_state_change_rejected PASSED
tests/test_all_requirements.py::test_case_24_fallback_mode_operational PASSED

======================== 24 passed in 4.30s ========================
```

---

## 6. Quick Start & Local Execution

### Prerequisites
- Python 3.12+
- Node.js 20+ and npm

### Step 1: Start Backend
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
*Backend Swagger Docs will be available at:* `http://127.0.0.1:8000/docs`

### Step 2: Start Frontend
```bash
cd frontend
npm install
npm run build
npm run start -p 3000
```
*Frontend Application will be available at:* `http://localhost:3000`

---

## 7. Docker Production Deployment

To run the complete production stack (PostgreSQL + FastAPI + Next.js App Router):

```bash
docker-compose up --build -d
```
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- PostgreSQL: `localhost:5432`

---

## 8. Hackathon Live Demo Scenario (3-Minute Script)

1. **Overview Dashboard (`/`):**
   - Inspect live metrics reading real persisted records.
   - Note the active placement drives and quick shortcuts.
2. **Student Roster (`/students`):**
   - Click **"Seed 15 Demo Students"** (or import a CSV).
   - Observe validation flags: STU104 has backlogs, STU108 has missing consent, STU106 has exact threshold CGPA 6.00.
3. **Placement Drives & Clash Alert (`/drives`):**
   - Inspect the **Schedule Conflict Alert**: Google Cloud and Microsoft drives have an overlapping time window.
   - Point out criteria versioning (v1).
4. **Eligibility Analysis (`/eligibility`):**
   - Click **"Run Evaluation Rules"** for Google Cloud.
   - Explainable breakdown shows 6 Eligible, 9 Excluded.
   - Inspect student STU104: clearly flags CGPA 6.40 < 7.50 AND 1 active backlog.
   - Click **"Export Roster (CSV)"** and **"Proceed to Approval Center"**.
5. **Approval Center Safety Gate (`/approvals`):**
   - View prepared approval with SHA-256 cryptographic fingerprint binding sorted student IDs.
   - Sign off as Placement Officer and click **"Sign & Approve Roster"**.
   - Click **"Submit to Destination"**.
6. **Upload Verification Receipt (`/uploads`):**
   - Review the intake receipt (`RCPT-EMP-...`): Status **VERIFIED**.
   - Destination records re-read and matched 100% (6 of 6 students verified).
   - Click **"Download Receipt (JSON)"**.
7. **Attendance Sheet (`/attendance`):**
   - Export official attendance sheet (CSV/XLSX) defaulted to "Not Marked".
   - Test marking student check-in "Present" with live timestamp.
8. **Agent Workspace (`/agent`):**
   - Issue prompt: *"Explain why student STU104 was excluded."*
   - Observe agent invoke `explain_student_decision` and report the exact rule failure.

---

## 9. Remaining Limitations & Production Roadmap

1. **Live Employer Form Adapter:** Currently defaults to the high-fidelity mock destination adapter (`mock://employer.recruitment/v1/intake`). Real form submission adapters (using authorized Playwright sessions or employer REST APIs) require campus institutional credentials.
2. **Single-User Session Demo:** The local demo operates with single-tenant placement officer roles. Multi-tenant RBAC with SAML/SSO is architected for Phase 2.
3. **External LLM Provider:** Fully functional in deterministic fallback mode. Setting `LLM_PROVIDER=gemini` with `LLM_API_KEY` enables generative reasoning while preserving deterministic rules for all decisions.
