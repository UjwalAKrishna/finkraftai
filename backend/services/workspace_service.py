# Workspace and multi-tenancy service

from typing import Dict, List, Optional, Any
from database.connection import db_manager
from backend.models.user import Workspace
import time


class WorkspaceService:
    """Service for managing workspaces and multi-tenancy"""
    
    def __init__(self):
        self._create_workspace_tables()
    
    def _create_workspace_tables(self):
        """Create workspace-related tables"""
        
        # Workspaces table
        db_manager.execute_query("""
            CREATE TABLE IF NOT EXISTS workspaces (
                workspace_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_by TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(user_id)
            )
        """)
        
        # Workspace members
        db_manager.execute_query("""
            CREATE TABLE IF NOT EXISTS workspace_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT DEFAULT 'member', -- owner, admin, member, viewer
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                UNIQUE(workspace_id, user_id)
            )
        """)
        
        # Workspace settings
        db_manager.execute_query("""
            CREATE TABLE IF NOT EXISTS workspace_settings (
                workspace_id TEXT NOT NULL,
                setting_key TEXT NOT NULL,
                setting_value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_by TEXT,
                PRIMARY KEY (workspace_id, setting_key),
                FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id)
            )
        """)
        
        # Create default workspace if not exists
        self._ensure_default_workspace()
    
    def _ensure_default_workspace(self):
        """Ensure default workspace exists"""
        
        existing = db_manager.execute_query("""
            SELECT workspace_id FROM workspaces WHERE workspace_id = 'default'
        """, fetch_one=True)
        
        if not existing:
            db_manager.execute_query("""
                INSERT INTO workspaces (workspace_id, name, description, created_by)
                VALUES ('default', 'Default Workspace', 'System default workspace', 'system')
            """)
    
    def create_workspace(self, workspace_id: str, name: str, created_by: str,
                        description: str = None) -> bool:
        """Create a new workspace"""
        
        try:
            db_manager.execute_query("""
                INSERT INTO workspaces (workspace_id, name, description, created_by)
                VALUES (?, ?, ?, ?)
            """, (workspace_id, name, description, created_by))
            
            # Add creator as owner
            self.add_workspace_member(workspace_id, created_by, "owner")
            
            return True
        except Exception:
            return False
    
    def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Get workspace details"""
        
        result = db_manager.execute_query("""
            SELECT workspace_id, name, description, created_by, is_active, created_at
            FROM workspaces
            WHERE workspace_id = ?
        """, (workspace_id,), fetch_one=True)
        
        return dict(result) if result else None
    
    def get_user_workspaces(self, user_id: str) -> List[Dict[str, Any]]:
        """Get workspaces user has access to"""
        
        workspaces = db_manager.execute_query("""
            SELECT w.workspace_id, w.name, w.description, wm.role, wm.joined_at
            FROM workspaces w
            JOIN workspace_members wm ON w.workspace_id = wm.workspace_id
            WHERE wm.user_id = ? AND wm.is_active = 1 AND w.is_active = 1
            ORDER BY w.name
        """, (user_id,))
        
        return [dict(ws) for ws in workspaces]
    
    def add_workspace_member(self, workspace_id: str, user_id: str, role: str = "member") -> bool:
        """Add user to workspace"""
        
        try:
            db_manager.execute_query("""
                INSERT OR REPLACE INTO workspace_members (workspace_id, user_id, role)
                VALUES (?, ?, ?)
            """, (workspace_id, user_id, role))
            return True
        except Exception:
            return False
    
    def remove_workspace_member(self, workspace_id: str, user_id: str) -> bool:
        """Remove user from workspace"""
        
        try:
            db_manager.execute_query("""
                UPDATE workspace_members 
                SET is_active = 0
                WHERE workspace_id = ? AND user_id = ?
            """, (workspace_id, user_id))
            return True
        except Exception:
            return False
    
    def get_workspace_members(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get workspace members"""
        
        members = db_manager.execute_query("""
            SELECT wm.user_id, u.username, u.full_name, wm.role, wm.joined_at
            FROM workspace_members wm
            JOIN users u ON wm.user_id = u.user_id
            WHERE wm.workspace_id = ? AND wm.is_active = 1
            ORDER BY wm.role, u.username
        """, (workspace_id,))
        
        return [dict(member) for member in members]
    
    def update_member_role(self, workspace_id: str, user_id: str, new_role: str) -> bool:
        """Update workspace member role"""
        
        try:
            db_manager.execute_query("""
                UPDATE workspace_members 
                SET role = ?
                WHERE workspace_id = ? AND user_id = ?
            """, (new_role, workspace_id, user_id))
            return True
        except Exception:
            return False
    
    def check_workspace_access(self, workspace_id: str, user_id: str, required_role: str = None) -> bool:
        """Check if user has access to workspace"""
        
        result = db_manager.execute_query("""
            SELECT role FROM workspace_members
            WHERE workspace_id = ? AND user_id = ? AND is_active = 1
        """, (workspace_id, user_id), fetch_one=True)
        
        if not result:
            return False
        
        if required_role:
            role_hierarchy = ["viewer", "member", "admin", "owner"]
            user_role_level = role_hierarchy.index(result['role']) if result['role'] in role_hierarchy else -1
            required_role_level = role_hierarchy.index(required_role) if required_role in role_hierarchy else 999
            
            return user_role_level >= required_role_level
        
        return True
    
    def set_workspace_setting(self, workspace_id: str, key: str, value: str, updated_by: str) -> bool:
        """Set workspace setting"""
        
        try:
            db_manager.execute_query("""
                INSERT OR REPLACE INTO workspace_settings 
                (workspace_id, setting_key, setting_value, updated_by)
                VALUES (?, ?, ?, ?)
            """, (workspace_id, key, value, updated_by))
            return True
        except Exception:
            return False
    
    def get_workspace_setting(self, workspace_id: str, key: str, default_value: str = None) -> Optional[str]:
        """Get workspace setting"""
        
        result = db_manager.execute_query("""
            SELECT setting_value FROM workspace_settings
            WHERE workspace_id = ? AND setting_key = ?
        """, (workspace_id, key), fetch_one=True)
        
        return result['setting_value'] if result else default_value
    
    def get_workspace_settings(self, workspace_id: str) -> Dict[str, str]:
        """Get all workspace settings"""
        
        settings = db_manager.execute_query("""
            SELECT setting_key, setting_value FROM workspace_settings
            WHERE workspace_id = ?
        """, (workspace_id,))
        
        return {setting['setting_key']: setting['setting_value'] for setting in settings}
    
    def get_workspace_stats(self, workspace_id: str) -> Dict[str, Any]:
        """Get workspace statistics"""
        
        # Member count
        member_count = db_manager.execute_query("""
            SELECT COUNT(*) as count FROM workspace_members
            WHERE workspace_id = ? AND is_active = 1
        """, (workspace_id,), fetch_one=True)
        
        # Conversation count
        conv_count = db_manager.execute_query("""
            SELECT COUNT(*) as count FROM conversations
            WHERE workspace_id = ?
        """, (workspace_id,), fetch_one=True)
        
        # Ticket count
        ticket_count = db_manager.execute_query("""
            SELECT COUNT(*) as count FROM tickets
            WHERE workspace_id = ?
        """, (workspace_id,), fetch_one=True)
        
        return {
            "members": member_count['count'] if member_count else 0,
            "conversations": conv_count['count'] if conv_count else 0,
            "tickets": ticket_count['count'] if ticket_count else 0
        }


# Global workspace service instance
workspace_service = WorkspaceService()