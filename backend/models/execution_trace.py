# Execution trace and audit models

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExecutionTrace:
    """Model for tracking tool executions and agent decisions"""
    id: Optional[int] = None
    trace_id: str = ""
    conversation_id: Optional[int] = None
    user_id: str = ""
    user_message: str = ""
    llm_plan: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    results: Optional[List[Dict[str, Any]]] = None
    explanation: Optional[str] = None
    execution_time_ms: int = 0
    workspace_id: str = "default"
    timestamp: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "user_message": self.user_message,
            "llm_plan": self.llm_plan,
            "tool_calls": self.tool_calls,
            "results": self.results,
            "explanation": self.explanation,
            "execution_time_ms": self.execution_time_ms,
            "workspace_id": self.workspace_id,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        return cls(**data)


@dataclass
class ToolExecution:
    """Individual tool execution within a trace"""
    tool_name: str
    parameters: Dict[str, Any]
    result: Dict[str, Any]
    status: str  # success, error, permission_denied
    execution_time_ms: int = 0
    error_message: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "result": self.result,
            "status": self.status,
            "execution_time_ms": self.execution_time_ms,
            "error_message": self.error_message
        }


@dataclass
class AuditEvent:
    """Audit event for compliance tracking"""
    id: Optional[int] = None
    event_id: str = ""
    event_type: str = ""  # user_action, system_action, data_access, permission_change
    user_id: str = ""
    resource_type: str = ""  # tool, data, user, permission
    resource_id: str = ""
    action: str = ""  # create, read, update, delete, execute
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    workspace_id: str = "default"
    timestamp: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "user_id": self.user_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "workspace_id": self.workspace_id,
            "timestamp": self.timestamp
        }


@dataclass
class PerformanceMetric:
    """Performance and usage metrics"""
    id: Optional[int] = None
    metric_name: str = ""
    metric_value: float = 0.0
    metric_unit: str = ""
    context: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    workspace_id: str = "default"
    timestamp: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "metric_unit": self.metric_unit,
            "context": self.context,
            "user_id": self.user_id,
            "workspace_id": self.workspace_id,
            "timestamp": self.timestamp
        }