# Permission management and admin endpoints

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from backend.services.auth_service import auth_service
from backend.core.tool_registry import registry
from database.repositories.permission_repo import permission_repo
from database.repositories.user_repo import user_repo

router = APIRouter(prefix="/api/admin", tags=["admin"])


class CreateUserRequest(BaseModel):
    user_id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    workspace_id: str = "default"


class AssignRoleRequest(BaseModel):
    user_id: str
    role_name: str


class GrantPermissionRequest(BaseModel):
    user_id: str
    permission_name: str
    granted: bool = True


def check_admin_access(user_id: str):
    """Dependency to check admin access"""
    if not auth_service.check_admin_access(user_id):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user_id


@router.get("/users")
def get_all_users(admin_user_id: str = Depends(check_admin_access)):
    """Get all users in the system"""
    
    try:
        users = user_repo.get_all_users()
        
        # Enrich with permission info
        enriched_users = []
        for user in users:
            user_permissions = permission_repo.get_user_permissions(user['user_id'])
            user_groups = permission_repo.get_user_groups(user['user_id'])
            
            enriched_users.append({
                **user,
                "permissions": user_permissions,
                "groups": user_groups,
                "permission_count": len(user_permissions)
            })
        
        return {"users": enriched_users}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users")
def create_user(request: CreateUserRequest, admin_user_id: str = Depends(check_admin_access)):
    """Create a new user"""
    
    try:
        # Check if user already exists
        if user_repo.user_exists(request.user_id):
            raise HTTPException(status_code=400, detail="User already exists")
        
        # Create user
        success = user_repo.create_user(
            user_id=request.user_id,
            username=request.username,
            email=request.email,
            full_name=request.full_name,
            workspace_id=request.workspace_id
        )
        
        if success:
            # Assign default viewer role
            permission_repo.assign_user_to_group(request.user_id, "Viewer")
            
            return {
                "success": True,
                "message": f"User {request.user_id} created successfully",
                "user_id": request.user_id
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to create user")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{user_id}/roles")
def assign_user_role(user_id: str, request: AssignRoleRequest, 
                    admin_user_id: str = Depends(check_admin_access)):
    """Assign role to user"""
    
    try:
        # Verify user exists
        if not user_repo.user_exists(user_id):
            raise HTTPException(status_code=404, detail="User not found")
        
        # Assign role
        success = permission_repo.assign_user_to_group(user_id, request.role_name)
        
        if success:
            return {
                "success": True,
                "message": f"Assigned role {request.role_name} to user {user_id}"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to assign role")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/{user_id}/permissions")
def grant_user_permission(user_id: str, request: GrantPermissionRequest,
                         admin_user_id: str = Depends(check_admin_access)):
    """Grant or revoke individual permission"""
    
    try:
        # Verify user exists
        if not user_repo.user_exists(user_id):
            raise HTTPException(status_code=404, detail="User not found")
        
        # Grant/revoke permission
        success = permission_repo.grant_individual_permission(
            user_id, request.permission_name, request.granted
        )
        
        if success:
            action = "granted" if request.granted else "revoked"
            return {
                "success": True,
                "message": f"Permission {request.permission_name} {action} for user {user_id}"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to update permission")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/summary")
def get_user_summary(user_id: str, admin_user_id: str = Depends(check_admin_access)):
    """Get comprehensive user summary"""
    
    try:
        # Get user info
        user_info = user_repo.get_user(user_id)
        if not user_info:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get permissions and roles
        permissions = permission_repo.get_user_permissions(user_id)
        groups = permission_repo.get_user_groups(user_id)
        can_see_traces = permission_repo.can_see_traces(user_id)
        
        # Get tool access
        allowed_tools = registry.get_allowed_tools(user_id)
        
        return {
            "user_info": user_info,
            "permissions": permissions,
            "groups": groups,
            "allowed_tools": allowed_tools,
            "can_see_traces": can_see_traces,
            "permission_summary": {
                "total_permissions": len(permissions),
                "total_groups": len(groups),
                "total_tools": len(allowed_tools)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/permissions")
def get_all_permissions(admin_user_id: str = Depends(check_admin_access)):
    """Get all available permissions"""
    
    try:
        permissions = permission_repo.get_all_permissions()
        return {"permissions": permissions}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/groups")
def get_all_groups(admin_user_id: str = Depends(check_admin_access)):
    """Get all permission groups/roles"""
    
    try:
        groups = permission_repo.get_all_groups()
        return {"groups": groups}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/stats")
def get_system_stats(admin_user_id: str = Depends(check_admin_access)):
    """Get system-wide statistics"""
    
    try:
        from database.connection import db_manager
        from backend.core.vector_store import vector_store
        from backend.core.planning_engine import planning_engine
        
        # User stats
        user_stats = db_manager.execute_query("""
            SELECT 
                COUNT(*) as total_users,
                COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_users
            FROM users
        """, fetch_one=True)
        
        # Conversation stats
        conv_stats = db_manager.execute_query("""
            SELECT 
                COUNT(DISTINCT thread_id) as total_threads,
                COUNT(*) as total_messages,
                COUNT(DISTINCT user_id) as users_with_conversations
            FROM conversations
        """, fetch_one=True)
        
        # Ticket stats
        ticket_stats = db_manager.execute_query("""
            SELECT 
                COUNT(*) as total_tickets,
                COUNT(CASE WHEN status = 'open' THEN 1 END) as open_tickets,
                COUNT(CASE WHEN status = 'closed' THEN 1 END) as closed_tickets
            FROM tickets
        """, fetch_one=True)
        
        # Planning stats
        plan_stats = db_manager.execute_query("""
            SELECT 
                COUNT(*) as total_plans,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_plans,
                COUNT(CASE WHEN status = 'running' THEN 1 END) as running_plans
            FROM execution_plans
        """, fetch_one=True)
        
        # Vector store stats
        vector_stats = vector_store.get_stats()
        
        return {
            "users": dict(user_stats) if user_stats else {},
            "conversations": dict(conv_stats) if conv_stats else {},
            "tickets": dict(ticket_stats) if ticket_stats else {},
            "plans": dict(plan_stats) if plan_stats else {},
            "memory": {
                "total_embeddings": vector_stats.get("total_vectors", 0),
                "embedding_dimension": vector_stats.get("embedding_dimension", 0),
                "model": vector_stats.get("model_name", "unknown")
            },
            "templates": {
                "available_templates": len(planning_engine.business_templates)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{user_id}")
def deactivate_user(user_id: str, admin_user_id: str = Depends(check_admin_access)):
    """Deactivate a user (soft delete)"""
    
    try:
        # Don't allow deactivating admin users
        if auth_service.check_admin_access(user_id):
            raise HTTPException(status_code=400, detail="Cannot deactivate admin users")
        
        # Deactivate user
        success = user_repo.update_user(user_id, is_active=False)
        
        if success:
            return {
                "success": True,
                "message": f"User {user_id} deactivated successfully"
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to deactivate user")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))