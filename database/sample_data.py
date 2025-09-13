# Sample data for database initialization

import sqlite3
from datetime import datetime


def insert_sample_permissions(db_path: str):
    """Insert sample permissions, groups, and users"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Insert permissions
        permissions = [
            ('filter_data', 'Filter dataset by criteria', 'tool'),
            ('export_report', 'Export data as CSV/Excel', 'tool'),
            ('create_ticket', 'Create support tickets', 'tool'),
            ('view_tickets', 'View support tickets', 'tool'),
            ('update_ticket', 'Update/assign/close tickets', 'tool'),
            ('view_traces', 'View execution traces', 'admin'),
            ('manage_users', 'Manage user accounts', 'admin'),
            ('manage_permissions', 'Manage permissions and roles', 'admin'),
        ]
        
        cursor.executemany(
            "INSERT OR IGNORE INTO permissions (permission_name, description, category) VALUES (?, ?, ?)",
            permissions
        )
        
        # Insert permission groups (roles)
        groups = [
            ('Admin', 'Full system access including traces and user management', True),
            ('Manager', 'Can manage data and tickets but no admin access', False),
            ('Viewer', 'Read-only access to data and own tickets', False),
        ]
        
        cursor.executemany(
            "INSERT OR IGNORE INTO permission_groups (group_name, description, can_see_traces) VALUES (?, ?, ?)",
            groups
        )
        
        # Get permission and group IDs
        cursor.execute("SELECT id, permission_name FROM permissions")
        perm_map = {name: id for id, name in cursor.fetchall()}
        
        cursor.execute("SELECT id, group_name FROM permission_groups")
        group_map = {name: id for id, name in cursor.fetchall()}
        
        # Assign permissions to groups
        group_permissions = [
            # Admin - all permissions
            (group_map['Admin'], perm_map['filter_data']),
            (group_map['Admin'], perm_map['export_report']),
            (group_map['Admin'], perm_map['create_ticket']),
            (group_map['Admin'], perm_map['view_tickets']),
            (group_map['Admin'], perm_map['update_ticket']),
            (group_map['Admin'], perm_map['view_traces']),
            (group_map['Admin'], perm_map['manage_users']),
            (group_map['Admin'], perm_map['manage_permissions']),
            
            # Manager - data and ticket management
            (group_map['Manager'], perm_map['filter_data']),
            (group_map['Manager'], perm_map['export_report']),
            (group_map['Manager'], perm_map['create_ticket']),
            (group_map['Manager'], perm_map['view_tickets']),
            (group_map['Manager'], perm_map['update_ticket']),
            
            # Viewer - read-only
            (group_map['Viewer'], perm_map['filter_data']),
            (group_map['Viewer'], perm_map['view_tickets']),
        ]
        
        cursor.executemany(
            "INSERT OR IGNORE INTO group_permissions (group_id, permission_id) VALUES (?, ?)",
            group_permissions
        )
        
        # Insert sample users
        users = [
            ('admin_user', 'admin', 'admin@company.com', 'System Administrator'),
            ('john_doe', 'john.doe', 'john@company.com', 'John Doe'),
            ('jane_smith', 'jane.smith', 'jane@company.com', 'Jane Smith'),
            ('viewer_user', 'viewer', 'viewer@company.com', 'View Only User'),
        ]
        
        cursor.executemany(
            "INSERT OR IGNORE INTO users (user_id, username, email, full_name) VALUES (?, ?, ?, ?)",
            users
        )
        
        # Get user IDs
        cursor.execute("SELECT id, user_id FROM users")
        user_map = {user_id: id for id, user_id in cursor.fetchall()}
        
        # Assign users to groups
        user_groups = [
            (user_map['admin_user'], group_map['Admin']),
            (user_map['john_doe'], group_map['Manager']),
            (user_map['jane_smith'], group_map['Manager']),
            (user_map['viewer_user'], group_map['Viewer']),
        ]
        
        cursor.executemany(
            "INSERT OR IGNORE INTO user_groups (user_id, group_id) VALUES (?, ?)",
            user_groups
        )
        
        conn.commit()
        print("✓ Sample permissions, groups, and users inserted successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"Error inserting sample data: {e}")
        raise
    finally:
        conn.close()


def print_permission_summary(db_path: str):
    """Print summary of permissions setup"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n=== Permission System Summary ===")
    
    # Groups and their permissions
    cursor.execute("""
        SELECT pg.group_name, pg.description, pg.can_see_traces,
               GROUP_CONCAT(p.permission_name, ', ') as permissions
        FROM permission_groups pg
        LEFT JOIN group_permissions gp ON pg.id = gp.group_id
        LEFT JOIN permissions p ON gp.permission_id = p.id
        GROUP BY pg.id, pg.group_name
    """)
    
    for group_name, desc, can_see_traces, permissions in cursor.fetchall():
        print(f"\n{group_name}: {desc}")
        print(f"  Can see traces: {bool(can_see_traces)}")
        print(f"  Permissions: {permissions or 'None'}")
    
    # Users and their groups
    print("\n=== User Assignments ===")
    cursor.execute("""
        SELECT u.user_id, u.full_name, GROUP_CONCAT(pg.group_name, ', ') as groups
        FROM users u
        LEFT JOIN user_groups ug ON u.id = ug.user_id
        LEFT JOIN permission_groups pg ON ug.group_id = pg.id
        GROUP BY u.id, u.user_id
    """)
    
    for user_id, full_name, groups in cursor.fetchall():
        print(f"{user_id} ({full_name}): {groups or 'No groups'}")
    
    conn.close()


if __name__ == "__main__":
    # Test with temporary database
    import os
    test_db = "test_permissions.db"
    
    # Create schema first
    os.system(f"sqlite3 {test_db} < database/migrations/001_initial_schema.sql")
    
    # Insert sample data
    insert_sample_permissions(test_db)
    print_permission_summary(test_db)
    
    # Cleanup
    os.remove(test_db)