# User and workspace context persistence

from typing import Dict, Any, Optional, List
from database.connection import db_manager
from backend.models.user import User, Session, Workspace
import json
import time


class ContextManager:
    """Manages user and workspace context across sessions"""
    
    def __init__(self):
        self._active_contexts = {}  # user_id -> context data
        self._create_context_tables()
    
    def _create_context_tables(self):
        """Create context storage tables"""
        
        # User sessions
        db_manager.execute_query("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                workspace_id TEXT DEFAULT 'default',
                context_data TEXT, -- JSON
                started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # User context state
        db_manager.execute_query("""
            CREATE TABLE IF NOT EXISTS user_context (
                user_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                context_key TEXT NOT NULL,
                context_value TEXT NOT NULL, -- JSON
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, workspace_id, context_key),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        db_manager.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id, is_active)
        """)
    
    def create_user_context(self, user_id: str, workspace_id: str = "default", 
                           session_id: str = None) -> Dict[str, Any]:
        """Create or load user context"""
        
        # Create session if not provided
        if not session_id:
            import uuid
            session_id = f"ctx_{user_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # Load existing context or create new
        existing_context = self.get_user_context(user_id, workspace_id)
        
        context_data = {
            "user_id": user_id,
            "workspace_id": workspace_id,
            "session_id": session_id,
            "active_thread": existing_context.get("active_thread"),
            "preferences": existing_context.get("preferences", {}),
            "recent_tools": existing_context.get("recent_tools", []),
            "current_task": existing_context.get("current_task"),
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Store session
        db_manager.execute_query("""
            INSERT OR REPLACE INTO user_sessions 
            (session_id, user_id, workspace_id, context_data, last_activity)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (session_id, user_id, workspace_id, json.dumps(context_data)))
        
        # Cache in memory
        self._active_contexts[f"{user_id}:{workspace_id}"] = context_data
        
        return context_data
    
    def get_user_context(self, user_id: str, workspace_id: str = "default") -> Dict[str, Any]:
        """Get user's current context"""
        
        cache_key = f"{user_id}:{workspace_id}"
        
        # Check memory cache first
        if cache_key in self._active_contexts:
            return self._active_contexts[cache_key]
        
        # Load from database
        context_items = db_manager.execute_query("""
            SELECT context_key, context_value
            FROM user_context
            WHERE user_id = ? AND workspace_id = ?
        """, (user_id, workspace_id))
        
        context_data = {"user_id": user_id, "workspace_id": workspace_id}
        for item in context_items:
            try:
                context_data[item['context_key']] = json.loads(item['context_value'])
            except:
                context_data[item['context_key']] = item['context_value']
        
        # Cache result
        self._active_contexts[cache_key] = context_data
        
        return context_data
    
    def update_user_context(self, user_id: str, workspace_id: str, 
                           context_key: str, context_value: Any):
        """Update specific context value"""
        
        # Update database
        db_manager.execute_query("""
            INSERT OR REPLACE INTO user_context 
            (user_id, workspace_id, context_key, context_value)
            VALUES (?, ?, ?, ?)
        """, (user_id, workspace_id, context_key, json.dumps(context_value)))
        
        # Update cache
        cache_key = f"{user_id}:{workspace_id}"
        if cache_key in self._active_contexts:
            self._active_contexts[cache_key][context_key] = context_value
            self._active_contexts[cache_key]["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    
    def set_active_thread(self, user_id: str, thread_id: str, workspace_id: str = "default"):
        """Set user's active conversation thread"""
        
        self.update_user_context(user_id, workspace_id, "active_thread", thread_id)
    
    def get_active_thread(self, user_id: str, workspace_id: str = "default") -> Optional[str]:
        """Get user's active conversation thread"""
        
        context = self.get_user_context(user_id, workspace_id)
        return context.get("active_thread")
    
    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any], 
                               workspace_id: str = "default"):
        """Update user preferences"""
        
        existing_prefs = self.get_user_context(user_id, workspace_id).get("preferences", {})
        existing_prefs.update(preferences)
        
        self.update_user_context(user_id, workspace_id, "preferences", existing_prefs)
    
    def track_tool_usage(self, user_id: str, tool_name: str, workspace_id: str = "default"):
        """Track tool usage for context"""
        
        context = self.get_user_context(user_id, workspace_id)
        recent_tools = context.get("recent_tools", [])
        
        # Add to front of list, keep last 10
        if tool_name in recent_tools:
            recent_tools.remove(tool_name)
        recent_tools.insert(0, tool_name)
        recent_tools = recent_tools[:10]
        
        self.update_user_context(user_id, workspace_id, "recent_tools", recent_tools)
    
    def set_current_task(self, user_id: str, task_description: str, 
                        workspace_id: str = "default"):
        """Set user's current task context"""
        
        task_data = {
            "description": task_description,
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "active"
        }
        
        self.update_user_context(user_id, workspace_id, "current_task", task_data)
    
    def clear_current_task(self, user_id: str, workspace_id: str = "default"):
        """Clear user's current task"""
        
        self.update_user_context(user_id, workspace_id, "current_task", None)
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        
        result = db_manager.execute_query("""
            SELECT session_id, user_id, workspace_id, context_data, 
                   started_at, last_activity, is_active
            FROM user_sessions
            WHERE session_id = ?
        """, (session_id,), fetch_one=True)
        
        if result:
            session_data = dict(result)
            try:
                session_data['context_data'] = json.loads(session_data['context_data']) if session_data['context_data'] else {}
            except:
                session_data['context_data'] = {}
            return session_data
        
        return None
    
    def update_session_activity(self, session_id: str):
        """Update session last activity"""
        
        db_manager.execute_query("""
            UPDATE user_sessions 
            SET last_activity = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """, (session_id,))
    
    def cleanup_inactive_sessions(self, hours_old: int = 24):
        """Clean up old inactive sessions"""
        
        db_manager.execute_query("""
            UPDATE user_sessions 
            SET is_active = 0
            WHERE last_activity < datetime('now', '-{} hours')
        """.format(hours_old))
    
    def get_user_sessions(self, user_id: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get user's sessions"""
        
        query = """
            SELECT session_id, workspace_id, started_at, last_activity, is_active
            FROM user_sessions
            WHERE user_id = ?
        """
        params = [user_id]
        
        if active_only:
            query += " AND is_active = 1"
        
        query += " ORDER BY last_activity DESC"
        
        rows = db_manager.execute_query(query, tuple(params))
        return [dict(row) for row in rows]


# Global context manager instance
context_manager = ContextManager()