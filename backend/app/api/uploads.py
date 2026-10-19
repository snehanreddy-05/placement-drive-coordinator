import json
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session, select
from app.database import get_session
from app.models.drive import PlacementDrive
from app.models.upload import UploadJob, UploadReceipt
from app.services.upload_service import execute_approved_upload
from app.services.mock_destination import mock_destination_service

router = APIRouter(prefix="/uploads", tags=["Upload & Verification"])

class UploadSubmissionRequest(BaseModel):
    drive_id: str
    approval_id: str
    idempotency_key: Optional[str] = None
    simulation_mode: Optional[str] = None # None, "WRONG_COUNT", "MISSING_ID", "UNEXPECTED_ID", "DUPLICATE_ID", "FAILURE"

@router.post("")
def submit_and_verify_upload(
    request: UploadSubmissionRequest,
    session: Session = Depends(get_session)
):
    try:
        job, receipt = execute_approved_upload(
            session=session,
            drive_id=request.drive_id,
            approval_id=request.approval_id,
            idempotency_key=request.idempotency_key,
            simulation_mode=request.simulation_mode
        )
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    return {
        "upload_job_id": job.id,
        "status": job.status,
        "submitted_count": job.submitted_count,
        "receipt": {
            "receipt_reference": receipt.receipt_reference if receipt else None,
            "verification_status": receipt.verification_status if receipt else "UNKNOWN",
            "expected_count": receipt.expected_count if receipt else job.expected_count,
            "actual_destination_count": receipt.actual_destination_count if receipt else 0,
            "matched_count": receipt.matched_count if receipt else 0,
            "missing_ids": json.loads(receipt.missing_ids_json) if receipt else [],
            "unexpected_ids": json.loads(receipt.unexpected_ids_json) if receipt else [],
            "duplicate_ids": json.loads(receipt.duplicate_ids_json) if receipt else [],
            "reconciliation_details": receipt.reconciliation_details if receipt else "No receipt",
            "verified_at": receipt.verified_at.isoformat() if receipt else None
        }
    }

@router.get("")
def list_uploads(
    drive_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    session: Session = Depends(get_session)
):
    query = select(UploadJob)
    if drive_id:
        query = query.where(UploadJob.drive_id == drive_id)
    if status:
        query = query.where(UploadJob.status == status)
    query = query.order_by(UploadJob.created_at.desc())
    jobs = session.exec(query).all()

    items = []
    for job in jobs:
        drive = session.get(PlacementDrive, job.drive_id)
        receipt = session.exec(select(UploadReceipt).where(UploadReceipt.upload_job_id == job.id)).first()
        items.append({
            "id": job.id,
            "drive_id": job.drive_id,
            "employer_name": drive.employer_name if drive else "Unknown",
            "drive_title": drive.drive_title if drive else "",
            "destination_url": job.destination_url,
            "status": job.status,
            "expected_count": job.expected_count,
            "submitted_count": job.submitted_count,
            "idempotency_key": job.idempotency_key,
            "created_at": job.created_at.isoformat(),
            "receipt": {
                "receipt_reference": receipt.receipt_reference if receipt else None,
                "verification_status": receipt.verification_status if receipt else None,
                "reconciliation_details": receipt.reconciliation_details if receipt else None,
                "actual_count": receipt.actual_destination_count if receipt else None
            } if receipt else None
        })
    return items

@router.get("/{upload_id}")
def get_upload_detail(upload_id: str, session: Session = Depends(get_session)):
    job = session.get(UploadJob, upload_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Upload job {upload_id} not found.")

    drive = session.get(PlacementDrive, job.drive_id)
    receipt = session.exec(select(UploadReceipt).where(UploadReceipt.upload_job_id == job.id)).first()

    return {
        "job": {
            "id": job.id,
            "drive_id": job.drive_id,
            "employer_name": drive.employer_name if drive else "",
            "destination_url": job.destination_url,
            "status": job.status,
            "expected_count": job.expected_count,
            "submitted_count": job.submitted_count,
            "submitted_ids": json.loads(job.submitted_ids_json),
            "idempotency_key": job.idempotency_key,
            "created_at": job.created_at.isoformat()
        },
        "receipt": {
            "id": receipt.id,
            "receipt_reference": receipt.receipt_reference,
            "verification_status": receipt.verification_status,
            "expected_count": receipt.expected_count,
            "actual_destination_count": receipt.actual_destination_count,
            "matched_count": receipt.matched_count,
            "missing_ids": json.loads(receipt.missing_ids_json),
            "unexpected_ids": json.loads(receipt.unexpected_ids_json),
            "duplicate_ids": json.loads(receipt.duplicate_ids_json),
            "reconciliation_details": receipt.reconciliation_details,
            "verified_at": receipt.verified_at.isoformat()
        } if receipt else None
    }

@router.get("/{upload_id}/receipt/download")
def download_upload_receipt(upload_id: str, session: Session = Depends(get_session)):
    receipt = session.exec(select(UploadReceipt).where(UploadReceipt.upload_job_id == upload_id)).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="No receipt generated for this upload job.")

    drive = session.get(PlacementDrive, receipt.drive_id)
    receipt_data = {
        "receipt_reference": receipt.receipt_reference,
        "employer": drive.employer_name if drive else "Unknown",
        "drive_title": drive.drive_title if drive else "",
        "destination_url": receipt.destination,
        "verification_status": receipt.verification_status,
        "expected_count": receipt.expected_count,
        "actual_destination_count": receipt.actual_destination_count,
        "matched_count": receipt.matched_count,
        "missing_ids": json.loads(receipt.missing_ids_json),
        "unexpected_ids": json.loads(receipt.unexpected_ids_json),
        "duplicate_ids": json.loads(receipt.duplicate_ids_json),
        "reconciliation_details": receipt.reconciliation_details,
        "verified_at_utc": receipt.verified_at.isoformat(),
        "issued_by": "PlacementOS Cryptographic Verification Gateway"
    }

    formatted_json = json.dumps(receipt_data, indent=2)
    return Response(
        content=formatted_json.encode("utf-8"),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=receipt_{receipt.receipt_reference}.json"}
    )
