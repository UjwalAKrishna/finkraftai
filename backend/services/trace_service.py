# Execution trace and audit service

from typing import Dict, List, Optional, Any
from database.connection import db_manager
from backend.models.execution_trace import ExecutionTrace, ToolExecution, AuditEvent
import json
import time
import uuid


class TraceService:
    """Service for tracking and auditing tool executions"""
    
    def __init__(self):
        self._create_trace_tables()
    
    def _create_trace_tables(self):
        """Create trace and audit tables"""
        
        # Audit events table
        db_manager.execute_query("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                event_type TEXT NOT NULL,
                user_id TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT, -- JSON
                ip_address TEXT,
                user_agent TEXT,
                workspace_id TEXT DEFAULT 'default',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        db_manager.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_audit_events_user ON audit_events(user_id, timestamp)
        """)
        
        db_manager.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_audit_events_resource ON audit_events(resource_type, resource_id)
        """)
    
    def create_execution_trace(self, user_id: str, user_message: str, 
                             conversation_id: int = None, workspace_id: str = "default") -> str:
        """Create a new execution trace"""
        
        trace_id = f"trace_{user_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # Store in traces table (existing schema)
        db_manager.execute_query("""
            INSERT INTO traces (
                trace_id, conversation_id, user_id, user_message, workspace_id
            ) VALUES (?, ?, ?, ?, ?)
        """, (trace_id, conversation_id, user_id, user_message, workspace_id))
        
        return trace_id
    
    def update_trace_plan(self, trace_id: str, llm_plan: str):
        """Update trace with LLM planning details"""
        
        db_manager.execute_query("""
            UPDATE traces 
            SET llm_plan = ?
            WHERE trace_id = ?
        """, (llm_plan, trace_id))
    
    def add_tool_execution(self, trace_id: str, tool_name: str, parameters: Dict[str, Any],
                          result: Dict[str, Any], status: str, execution_time_ms: int = 0):
        """Add tool execution to trace"""
        
        # Get current tool calls
        trace_data = db_manager.execute_query("""
            SELECT tool_calls, results FROM traces WHERE trace_id = ?
        """, (trace_id,), fetch_one=True)
        
        if trace_data:
            # Parse existing data
            tool_calls = json.loads(trace_data['tool_calls']) if trace_data['tool_calls'] else []
            results = json.loads(trace_data['results']) if trace_data['results'] else []
            
            # Add new execution
            tool_calls.append({
                "tool_name": tool_name,
                "parameters": parameters,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            results.append({
                "tool_name": tool_name,
                "result": result,
                "status": status,
                "execution_time_ms": execution_time_ms,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            # Update trace
            db_manager.execute_query("""
                UPDATE traces 
                SET tool_calls = ?, results = ?, execution_time_ms = execution_time_ms + ?
                WHERE trace_id = ?
            """, (json.dumps(tool_calls), json.dumps(results), execution_time_ms, trace_id))
    
    def complete_trace(self, trace_id: str, explanation: str = None):
        """Mark trace as complete with final explanation"""
        
        if explanation:
            db_manager.execute_query("""
                UPDATE traces 
                SET explanation = ?
                WHERE trace_id = ?
            """, (explanation, trace_id))
    
    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get execution trace by ID"""
        
        result = db_manager.execute_query("""
            SELECT trace_id, conversation_id, user_id, user_message, llm_plan,
                   tool_calls, results, explanation, execution_time_ms, timestamp
            FROM traces
            WHERE trace_id = ?
        """, (trace_id,), fetch_one=True)
        
        if result:
            trace_dict = dict(result)
            # Parse JSON fields
            trace_dict['tool_calls'] = json.loads(trace_dict['tool_calls']) if trace_dict['tool_calls'] else []
            trace_dict['results'] = json.loads(trace_dict['results']) if trace_dict['results'] else []
            return trace_dict
        
        return None
    
    def get_user_traces(self, user_id: str, limit: int = 50, workspace_id: str = "default") -> List[Dict[str, Any]]:
        """Get execution traces for a user"""
        
        traces = db_manager.execute_query("""
            SELECT trace_id, user_message, execution_time_ms, timestamp
            FROM traces
            WHERE user_id = ? AND workspace_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (user_id, workspace_id, limit))
        
        return [dict(trace) for trace in traces]
    
    def log_audit_event(self, event_type: str, user_id: str, resource_type: str,
                       resource_id: str, action: str, details: Dict[str, Any] = None,
                       ip_address: str = None, user_agent: str = None,
                       workspace_id: str = "default") -> str:
        """Log an audit event"""
        
        event_id = f"audit_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        db_manager.execute_query("""
            INSERT INTO audit_events (
                event_id, event_type, user_id, resource_type, resource_id,
                action, details, ip_address, user_agent, workspace_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id, event_type, user_id, resource_type, resource_id,
            action, json.dumps(details) if details else None,
            ip_address, user_agent, workspace_id
        ))
        
        return event_id
    
    def get_audit_events(self, user_id: str = None, resource_type: str = None,
                        limit: int = 100, workspace_id: str = "default") -> List[Dict[str, Any]]:
        """Get audit events with optional filters"""
        
        query = """
            SELECT event_id, event_type, user_id, resource_type, resource_id,
                   action, details, timestamp
            FROM audit_events
            WHERE workspace_id = ?
        """
        params = [workspace_id]
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if resource_type:
            query += " AND resource_type = ?"
            params.append(resource_type)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        events = db_manager.execute_query(query, tuple(params))
        
        result = []
        for event in events:
            event_dict = dict(event)
            event_dict['details'] = json.loads(event_dict['details']) if event_dict['details'] else {}
            result.append(event_dict)
        
        return result
    
    def get_trace_statistics(self, user_id: str = None, workspace_id: str = "default") -> Dict[str, Any]:
        """Get trace and audit statistics"""
        
        # Trace stats
        trace_query = "SELECT COUNT(*) as count, AVG(execution_time_ms) as avg_time FROM traces WHERE workspace_id = ?"
        trace_params = [workspace_id]
        
        if user_id:
            trace_query += " AND user_id = ?"
            trace_params.append(user_id)
        
        trace_stats = db_manager.execute_query(trace_query, tuple(trace_params), fetch_one=True)
        
        # Audit stats
        audit_query = "SELECT COUNT(*) as count FROM audit_events WHERE workspace_id = ?"
        audit_params = [workspace_id]
        
        if user_id:
            audit_query += " AND user_id = ?"
            audit_params.append(user_id)
        
        audit_stats = db_manager.execute_query(audit_query, tuple(audit_params), fetch_one=True)
        
        return {
            "traces": {
                "total_traces": trace_stats['count'] if trace_stats else 0,
                "avg_execution_time_ms": trace_stats['avg_time'] if trace_stats else 0
            },
            "audit_events": {
                "total_events": audit_stats['count'] if audit_stats else 0
            }
        }


# Global trace service instance
trace_service = TraceService()