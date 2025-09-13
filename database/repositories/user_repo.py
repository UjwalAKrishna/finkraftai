# User and session data access repository

from typing import List, Optional, Dict
from database.connection import db_manager


class UserRepository:
    """Repository for user-related database operations"""
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        
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
    
    def update_user(self, user_id: str, **updates) -> bool:
        """Update user fields"""
        
        if not updates:
            return False
        
        allowed_fields = ['username', 'email', 'full_name', 'is_active']
        set_clauses = []
        params = []
        
        for field, value in updates.items():
            if field in allowed_fields:
                set_clauses.append(f"{field} = ?")
                params.append(value)
        
        if not set_clauses:
            return False
        
        params.append(user_id)
        
        query = f"""
        UPDATE users 
        SET {', '.join(set_clauses)}
        WHERE user_id = ?
        """
        
        try:
            db_manager.execute_query(query, tuple(params))
            return True
        except Exception:
            return False
    
    def get_all_users(self, workspace_id: str = None) -> List[Dict]:
        """Get all users, optionally filtered by workspace"""
        
        query = "SELECT user_id, username, email, full_name, workspace_id, is_active FROM users"
        params = []
        
        if workspace_id:
            query += " WHERE workspace_id = ?"
            params.append(workspace_id)
        
        query += " ORDER BY username"
        
        rows = db_manager.execute_query(query, tuple(params))
        return [dict(row) for row in rows]
    
    def user_exists(self, user_id: str) -> bool:
        """Check if user exists"""
        
        query = "SELECT 1 FROM users WHERE user_id = ?"
        result = db_manager.execute_query(query, (user_id,), fetch_one=True)
        return bool(result)

# Global repository instance
user_repo = UserRepository()