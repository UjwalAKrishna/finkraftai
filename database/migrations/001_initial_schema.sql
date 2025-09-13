-- Initial database schema for FinkraftAI
-- Database-driven permission system

-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE NOT NULL,
    username TEXT NOT NULL,
    email TEXT,
    full_name TEXT,
    workspace_id TEXT DEFAULT 'default',
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Permissions table - defines all available permissions
CREATE TABLE permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    permission_name TEXT UNIQUE NOT NULL,
    description TEXT,
    category TEXT DEFAULT 'general', -- 'tool', 'admin', 'view', etc.
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Permission groups table - roles like Admin, Manager, Viewer
CREATE TABLE permission_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_name TEXT UNIQUE NOT NULL,
    description TEXT,
    can_see_traces BOOLEAN DEFAULT FALSE,
    workspace_id TEXT DEFAULT 'default',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Group permissions - which permissions each group has
CREATE TABLE group_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES permission_groups(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE,
    UNIQUE(group_id, permission_id)
);

-- User group assignments - which groups each user belongs to
CREATE TABLE user_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    group_id INTEGER NOT NULL,
    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    assigned_by TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (group_id) REFERENCES permission_groups(id) ON DELETE CASCADE,
    UNIQUE(user_id, group_id)
);

-- Individual user permissions - direct permissions to users
CREATE TABLE user_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    granted BOOLEAN DEFAULT TRUE, -- TRUE=granted, FALSE=denied (overrides group)
    granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    granted_by TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE,
    UNIQUE(user_id, permission_id)
);

-- Conversations table
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    role TEXT,
    message TEXT NOT NULL,
    sender TEXT NOT NULL, -- 'user' or 'assistant'
    session_id TEXT,
    workspace_id TEXT DEFAULT 'default',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tickets table
CREATE TABLE tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'open', -- open, in_progress, closed
    priority TEXT DEFAULT 'medium', -- low, medium, high
    created_by TEXT NOT NULL,
    assigned_to TEXT,
    workspace_id TEXT DEFAULT 'default',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Execution traces table
CREATE TABLE traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id TEXT UNIQUE NOT NULL,
    conversation_id INTEGER,
    user_id TEXT NOT NULL,
    user_message TEXT,
    llm_plan TEXT,
    tool_calls TEXT, -- JSON
    results TEXT, -- JSON
    explanation TEXT,
    execution_time_ms INTEGER,
    workspace_id TEXT DEFAULT 'default',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

-- Indexes for better performance
CREATE INDEX idx_users_user_id ON users(user_id);
CREATE INDEX idx_users_workspace ON users(workspace_id);
CREATE INDEX idx_conversations_user ON conversations(user_id);
CREATE INDEX idx_conversations_session ON conversations(session_id);
CREATE INDEX idx_tickets_created_by ON tickets(created_by);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_traces_user ON traces(user_id);
CREATE INDEX idx_traces_conversation ON traces(conversation_id);