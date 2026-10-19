import json
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.database import get_session
from app.models.agent import AgentExecution, AgentToolCall
from app.services.agent_service import AgentOrchestrator, AVAILABLE_TOOLS

router = APIRouter(prefix="/agent", tags=["Agent Workspace"])

class AgentChatRequest(BaseModel):
    prompt: str
    drive_id: Optional[str] = None

@router.get("/tools")
def get_available_tools():
    return {"tools": AVAILABLE_TOOLS}

@router.post("/chat")
def chat_with_agent(
    request: AgentChatRequest,
    session: Session = Depends(get_session)
):
    orchestrator = AgentOrchestrator(session)
    execution = orchestrator.run_agent(request.prompt, request.drive_id)

    tool_calls = session.exec(
        select(AgentToolCall).where(AgentToolCall.execution_id == execution.id).order_by(AgentToolCall.timestamp)
    ).all()

    return {
        "execution_id": execution.id,
        "prompt": execution.prompt,
        "status": execution.status,
        "summary": execution.summary,
        "current_task": execution.current_task,
        "next_action": execution.next_action,
        "provider_used": execution.provider_used,
        "created_at": execution.created_at.isoformat(),
        "tool_calls": [
            {
                "id": tc.id,
                "tool_name": tc.tool_name,
                "arguments": json.loads(tc.arguments_json) if tc.arguments_json else {},
                "result_summary": tc.result_summary,
                "status": tc.status,
                "timestamp": tc.timestamp.isoformat()
            } for tc in tool_calls
        ]
    }

@router.get("/executions")
def list_agent_executions(limit: int = 20, session: Session = Depends(get_session)):
    executions = session.exec(
        select(AgentExecution).order_by(AgentExecution.created_at.desc()).limit(limit)
    ).all()

    return [
        {
            "id": ex.id,
            "prompt": ex.prompt,
            "status": ex.status,
            "summary": ex.summary,
            "next_action": ex.next_action,
            "tool_calls_count": ex.tool_calls_count,
            "provider_used": ex.provider_used,
            "created_at": ex.created_at.isoformat()
        } for ex in executions
    ]

@router.get("/executions/{execution_id}")
def get_agent_execution_detail(execution_id: str, session: Session = Depends(get_session)):
    ex = session.get(AgentExecution, execution_id)
    if not ex:
        raise HTTPException(status_code=404, detail=f"Agent execution {execution_id} not found.")

    tool_calls = session.exec(
        select(AgentToolCall).where(AgentToolCall.execution_id == execution_id).order_by(AgentToolCall.timestamp)
    ).all()

    return {
        "execution": {
            "id": ex.id,
            "prompt": ex.prompt,
            "status": ex.status,
            "summary": ex.summary,
            "current_task": ex.current_task,
            "next_action": ex.next_action,
            "provider_used": ex.provider_used,
            "created_at": ex.created_at.isoformat()
        },
        "tool_calls": [
            {
                "id": tc.id,
                "tool_name": tc.tool_name,
                "arguments": json.loads(tc.arguments_json) if tc.arguments_json else {},
                "result_summary": tc.result_summary,
                "status": tc.status,
                "timestamp": tc.timestamp.isoformat()
            } for tc in tool_calls
        ]
    }
