from typing import Optional
from datetime import datetime, timezone
import uuid
from sqlmodel import SQLModel, Field

class AgentExecution(SQLModel, table=True):
    __tablename__ = "agent_executions"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    prompt: str
    status: str = Field(default="COMPLETED")  # RUNNING, COMPLETED, FAILED, WAITING_APPROVAL
    summary: str
    current_task: Optional[str] = None
    next_action: Optional[str] = None
    tool_calls_count: int = Field(default=0)
    provider_used: str = Field(default="deterministic")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AgentToolCall(SQLModel, table=True):
    __tablename__ = "agent_tool_calls"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    execution_id: str = Field(index=True)
    tool_name: str
    arguments_json: str
    result_summary: str
    status: str = Field(default="SUCCESS") # SUCCESS, ERROR, REJECTED
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
