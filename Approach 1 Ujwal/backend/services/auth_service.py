# Session and permission validation service

from typing import Optional, Dict, List
from database.repositories.user_repo import user_repo
from database.repositories.permission_repo import permission_repo
from backend.tools.base_tool import UserContext


class AuthService:
    """Authentication and authorization service"""
    
    def __init__(self):
        pass
    
    def validate_user(self, user_id: str) -> bool:
        """Validate if user exists and is active"""
        
        user = user_repo.get_user(user_id)
        return user is not None and user.get('is_active', False)
    
    def get_user_context(self, user_id: str) -> Optional[UserContext]:
        """Get user context with permissions"""
        
        if not self.validate_user(user_id):
            return None
        
        try:
            return UserContext(user_id=user_id)
        except Exception:
            return None
    
    def check_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has a specific permission"""
        
        user_permissions = permission_repo.get_user_permissions(user_id)
        return permission in user_permissions
    
    def check_tool_access(self, user_id: str, tool_name: str) -> bool:
        """Check if user can access a specific tool"""
        
        return self.check_permission(user_id, tool_name)
    
    def get_user_permissions(self, user_id: str) -> List[str]:
        """Get all permissions for a user"""
        
        return permission_repo.get_user_permissions(user_id)
    
    def get_user_roles(self, user_id: str) -> List[str]:
        """Get user's roles/groups"""
        
        return permission_repo.get_user_groups(user_id)
    
    def create_session(self, user_id: str, workspace_id: str = "default") -> Dict[str, str]:
        """Create a new user session"""
        
        import uuid
        import time
        
        session_id = f"sess_{user_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # Simple session tracking (could be enhanced with database storage)
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "workspace_id": workspace_id,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "active"
        }
        
        return session_data
    
    def validate_session(self, session_id: str, user_id: str) -> bool:
        """Validate a user session"""
        
        # Simple validation - in production would check database
        return session_id.startswith(f"sess_{user_id}_")
    
    def authorize_workspace_access(self, user_id: str, workspace_id: str) -> bool:
        """Check if user can access a workspace"""
        
        user = user_repo.get_user(user_id)
        if not user:
            return False
        
        # Simple check - user's default workspace or default workspace
        return user.get('workspace_id') == workspace_id or workspace_id == "default"
    
    def get_accessible_workspaces(self, user_id: str) -> List[str]:
        """Get workspaces accessible to user"""
        
        user = user_repo.get_user(user_id)
        if not user:
            return []
        
        # Simple implementation - user's workspace + default
        workspaces = ["default"]
        user_workspace = user.get('workspace_id')
        if user_workspace and user_workspace != "default":
            workspaces.append(user_workspace)
        
        return workspaces
    
    def check_admin_access(self, user_id: str) -> bool:
        """Check if user has admin access"""
        
        user_roles = self.get_user_roles(user_id)
        return "Admin" in user_roles
    
    def check_trace_access(self, user_id: str) -> bool:
        """Check if user can view execution traces"""
        
        return permission_repo.can_see_traces(user_id)


# Global auth service instance
auth_service = AuthService()