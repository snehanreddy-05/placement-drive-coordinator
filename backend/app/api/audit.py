from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from app.database import get_session
from app.models.audit import AuditEvent

router = APIRouter(prefix="/audit", tags=["Audit Log"])

@router.get("")
def get_audit_trail(
    event_type: Optional[str] = Query(None),
    limit: int = 50,
    session: Session = Depends(get_session)
):
    query = select(AuditEvent)
    if event_type:
        query = query.where(AuditEvent.event_type == event_type)
    query = query.order_by(AuditEvent.created_at.desc()).limit(limit)
    events = session.exec(query).all()

    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "actor": e.actor,
            "action_details": e.action_details,
            "metadata": e.metadata_json,
            "created_at": e.created_at.isoformat()
        } for e in events
    ]
