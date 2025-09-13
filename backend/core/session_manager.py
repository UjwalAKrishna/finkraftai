# Cross-session user identity management

from typing import Dict, Optional, List
from backend.core.context_manager import context_manager
from backend.services.auth_service import auth_service
from database.repositories.user_repo import user_repo
import time
import uuid


class SessionManager:
    """Manages user sessions and cross-session continuity"""
    
    def __init__(self):
        self._active_sessions = {}  # session_id -> session_data
    
    def create_session(self, user_id: str, workspace_id: str = "default") -> Dict[str, str]:
        """Create a new user session with context"""
        
        # Validate user exists
        if not auth_service.validate_user(user_id):
            raise ValueError(f"Invalid user: {user_id}")
        
        # Check workspace access
        if not auth_service.authorize_workspace_access(user_id, workspace_id):
            raise ValueError(f"User {user_id} cannot access workspace {workspace_id}")
        
        # Generate session ID
        session_id = f"sess_{user_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # Create user context
        context = context_manager.create_user_context(user_id, workspace_id, session_id)
        
        # Create session data
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "workspace_id": workspace_id,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "last_activity": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "active",
            "context": context
        }
        
        # Store in memory
        self._active_sessions[session_id] = session_data
        
        return session_data
    
    def get_session(self, session_id: str) -> Optional[Dict[str, str]]:
        """Get session information"""
        
        # Check memory cache
        if session_id in self._active_sessions:
            session_data = self._active_sessions[session_id]
            self._update_session_activity(session_id)
            return session_data
        
        # Load from database
        session_info = context_manager.get_session_info(session_id)
        if session_info and session_info.get('is_active'):
            # Reconstruct session data
            session_data = {
                "session_id": session_id,
                "user_id": session_info['user_id'],
                "workspace_id": session_info['workspace_id'],
                "created_at": session_info['started_at'],
                "last_activity": session_info['last_activity'],
                "status": "active" if session_info['is_active'] else "inactive",
                "context": session_info.get('context_data', {})
            }
            
            # Cache in memory
            self._active_sessions[session_id] = session_data
            self._update_session_activity(session_id)
            
            return session_data
        
        return None
    
    def validate_session(self, session_id: str, user_id: str = None) -> bool:
        """Validate if session is active and belongs to user"""
        
        session = self.get_session(session_id)
        if not session:
            return False
        
        if user_id and session.get('user_id') != user_id:
            return False
        
        return session.get('status') == 'active'
    
    def end_session(self, session_id: str) -> bool:
        """End a user session"""
        
        # Update database
        context_manager.update_session_activity(session_id)
        
        # Remove from memory
        if session_id in self._active_sessions:
            self._active_sessions[session_id]['status'] = 'ended'
            del self._active_sessions[session_id]
        
        return True
    
    def get_user_sessions(self, user_id: str, active_only: bool = True) -> List[Dict[str, str]]:
        """Get all sessions for a user"""
        
        return context_manager.get_user_sessions(user_id, active_only)
    
    def switch_workspace(self, session_id: str, new_workspace_id: str) -> bool:
        """Switch session to different workspace"""
        
        session = self.get_session(session_id)
        if not session:
            return False
        
        user_id = session['user_id']
        
        # Check access to new workspace
        if not auth_service.authorize_workspace_access(user_id, new_workspace_id):
            return False
        
        # Update session
        session['workspace_id'] = new_workspace_id
        session['last_activity'] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Update context
        context_manager.create_user_context(user_id, new_workspace_id, session_id)
        
        return True
    
    def get_session_context(self, session_id: str) -> Optional[Dict[str, any]]:
        """Get session context"""
        
        session = self.get_session(session_id)
        if not session:
            return None
        
        user_id = session['user_id']
        workspace_id = session['workspace_id']
        
        return context_manager.get_user_context(user_id, workspace_id)
    
    def update_session_context(self, session_id: str, context_key: str, context_value: any):
        """Update session context"""
        
        session = self.get_session(session_id)
        if not session:
            return False
        
        user_id = session['user_id']
        workspace_id = session['workspace_id']
        
        context_manager.update_user_context(user_id, workspace_id, context_key, context_value)
        self._update_session_activity(session_id)
        
        return True
    
    def track_session_activity(self, session_id: str, activity_type: str, activity_data: Dict = None):
        """Track user activity in session"""
        
        session = self.get_session(session_id)
        if not session:
            return
        
        user_id = session['user_id']
        workspace_id = session['workspace_id']
        
        # Track tool usage
        if activity_type == 'tool_execution' and activity_data:
            tool_name = activity_data.get('tool_name')
            if tool_name:
                context_manager.track_tool_usage(user_id, tool_name, workspace_id)
        
        # Track conversation activity
        elif activity_type == 'conversation':
            self._update_session_activity(session_id)
        
        # Track task activity
        elif activity_type == 'task_start' and activity_data:
            task_description = activity_data.get('description', 'Unknown task')
            context_manager.set_current_task(user_id, task_description, workspace_id)
        
        elif activity_type == 'task_complete':
            context_manager.clear_current_task(user_id, workspace_id)
    
    def _update_session_activity(self, session_id: str):
        """Update session last activity timestamp"""
        
        if session_id in self._active_sessions:
            self._active_sessions[session_id]['last_activity'] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        context_manager.update_session_activity(session_id)
    
    def cleanup_expired_sessions(self, hours_old: int = 24):
        """Clean up expired sessions"""
        
        # Clean up database
        context_manager.cleanup_inactive_sessions(hours_old)
        
        # Clean up memory
        current_time = time.time()
        expired_sessions = []
        
        for session_id, session_data in self._active_sessions.items():
            try:
                last_activity = time.mktime(time.strptime(session_data['last_activity'], "%Y-%m-%d %H:%M:%S"))
                if (current_time - last_activity) > (hours_old * 3600):
                    expired_sessions.append(session_id)
            except:
                expired_sessions.append(session_id)  # Remove malformed sessions
        
        for session_id in expired_sessions:
            del self._active_sessions[session_id]
        
        return len(expired_sessions)
    
    def get_session_stats(self) -> Dict[str, int]:
        """Get session statistics"""
        
        return {
            "active_sessions": len(self._active_sessions),
            "total_sessions_today": self._count_sessions_today()
        }
    
    def _count_sessions_today(self) -> int:
        """Count sessions created today"""
        
        from database.connection import db_manager
        
        result = db_manager.execute_query("""
            SELECT COUNT(*) as count
            FROM user_sessions
            WHERE DATE(started_at) = DATE('now')
        """, fetch_one=True)
        
        return result['count'] if result else 0


# Global session manager instance
session_manager = SessionManager()