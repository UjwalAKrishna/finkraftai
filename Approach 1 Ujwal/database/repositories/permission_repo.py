# Permission repository - database operations for permissions

from typing import List, Optional, Dict
from database.connection import db_manager


class PermissionRepository:
    """Repository for permission-related database operations"""
    
    def get_user_permissions(self, user_id: str) -> List[str]:
        """Get all permissions for a user (from groups + individual)"""
        
        query = """
        SELECT DISTINCT p.permission_name
        FROM permissions p
        WHERE p.id IN (
            -- Permissions from groups
            SELECT gp.permission_id
            FROM users u
            JOIN user_groups ug ON u.id = ug.user_id
            JOIN group_permissions gp ON ug.group_id = gp.group_id
            WHERE u.user_id = ? AND u.is_active = 1
            
            UNION
            
            -- Individual permissions (granted only)
            SELECT up.permission_id
            FROM users u
            JOIN user_permissions up ON u.id = up.user_id
            WHERE u.user_id = ? AND u.is_active = 1 AND up.granted = 1
        )
        AND p.id NOT IN (
            -- Exclude individually denied permissions
            SELECT up.permission_id
            FROM users u
            JOIN user_permissions up ON u.id = up.user_id
            WHERE u.user_id = ? AND u.is_active = 1 AND up.granted = 0
        )
        """
        
        rows = db_manager.execute_query(query, (user_id, user_id, user_id))
        return [row['permission_name'] for row in rows]
    
    def can_see_traces(self, user_id: str) -> bool:
        """Check if user can see execution traces"""
        
        query = """
        SELECT DISTINCT pg.can_see_traces
        FROM users u
        JOIN user_groups ug ON u.id = ug.user_id
        JOIN permission_groups pg ON ug.group_id = pg.id
        WHERE u.user_id = ? AND u.is_active = 1 AND pg.can_see_traces = 1
        """
        
        result = db_manager.execute_query(query, (user_id,), fetch_one=True)
        return bool(result) if result else False
    
    def get_user_groups(self, user_id: str) -> List[str]:
        """Get all groups for a user"""
        
        query = """
        SELECT pg.group_name
        FROM users u
        JOIN user_groups ug ON u.id = ug.user_id
        JOIN permission_groups pg ON ug.group_id = pg.id
        WHERE u.user_id = ? AND u.is_active = 1
        """
        
        rows = db_manager.execute_query(query, (user_id,))
        return [row['group_name'] for row in rows]
    
    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """Get basic user information"""
        
        query = """
        SELECT user_id, username, email, full_name, workspace_id, is_active
        FROM users
        WHERE user_id = ?
        """
        
        result = db_manager.execute_query(query, (user_id,), fetch_one=True)
        return dict(result) if result else None
    
    def create_user(self, user_id: str, username: str, email: str = None, 
                   full_name: str = None, workspace_id: str = "default") -> bool:
        """Create a new user"""
        
        query = """
        INSERT INTO users (user_id, username, email, full_name, workspace_id)
        VALUES (?, ?, ?, ?, ?)
        """
        
        try:
            db_manager.execute_query(query, (user_id, username, email, full_name, workspace_id))
            return True
        except Exception:
            return False
    
    def assign_user_to_group(self, user_id: str, group_name: str) -> bool:
        """Assign user to a permission group"""
        
        query = """
        INSERT OR IGNORE INTO user_groups (user_id, group_id)
        SELECT u.id, pg.id
        FROM users u, permission_groups pg
        WHERE u.user_id = ? AND pg.group_name = ?
        """
        
        try:
            db_manager.execute_query(query, (user_id, group_name))
            return True
        except Exception:
            return False
    
    def grant_individual_permission(self, user_id: str, permission_name: str, 
                                  granted: bool = True) -> bool:
        """Grant or deny individual permission to user"""
        
        query = """
        INSERT OR REPLACE INTO user_permissions (user_id, permission_id, granted)
        SELECT u.id, p.id, ?
        FROM users u, permissions p
        WHERE u.user_id = ? AND p.permission_name = ?
        """
        
        try:
            db_manager.execute_query(query, (granted, user_id, permission_name))
            return True
        except Exception:
            return False
    
    def get_all_permissions(self) -> List[Dict]:
        """Get all available permissions"""
        
        query = """
        SELECT permission_name, description, category
        FROM permissions
        ORDER BY category, permission_name
        """
        
        rows = db_manager.execute_query(query)
        return [dict(row) for row in rows]
    
    def get_all_groups(self) -> List[Dict]:
        """Get all permission groups"""
        
        query = """
        SELECT group_name, description, can_see_traces
        FROM permission_groups
        ORDER BY group_name
        """
        
        rows = db_manager.execute_query(query)
        return [dict(row) for row in rows]

# Global repository instance
permission_repo = PermissionRepository()