-- Memory System Database Schema
-- Comprehensive conversation and entity memory

-- Conversation threads - logical grouping of related conversations
CREATE TABLE conversation_threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    title TEXT,
    description TEXT,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    workspace_id TEXT DEFAULT 'default',
    thread_type TEXT DEFAULT 'general', -- general, investigation, project, support
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Enhanced conversations table
DROP TABLE IF EXISTS conversations;
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL, -- 'user' or 'assistant'
    message TEXT NOT NULL,
    message_type TEXT DEFAULT 'text', -- text, tool_call, tool_result, system
    tool_name TEXT,
    tool_parameters TEXT, -- JSON
    tool_result TEXT, -- JSON
    session_id TEXT,
    workspace_id TEXT DEFAULT 'default',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    importance_score REAL DEFAULT 0.5, -- 0.0 to 1.0
    tokens_used INTEGER DEFAULT 0,
    FOREIGN KEY (thread_id) REFERENCES conversation_threads(thread_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Conversation summaries for long threads
CREATE TABLE conversation_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,
    summary_text TEXT NOT NULL,
    summary_type TEXT DEFAULT 'auto', -- auto, manual, key_points
    start_message_id INTEGER,
    end_message_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    token_count INTEGER DEFAULT 0,
    FOREIGN KEY (thread_id) REFERENCES conversation_threads(thread_id),
    FOREIGN KEY (start_message_id) REFERENCES conversations(id),
    FOREIGN KEY (end_message_id) REFERENCES conversations(id)
);

-- Entity mentions and tracking
CREATE TABLE entity_mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    entity_type TEXT NOT NULL, -- vendor, invoice, ticket, product, etc.
    entity_id TEXT NOT NULL, -- business object ID
    entity_name TEXT, -- human readable name
    mention_context TEXT, -- surrounding text
    confidence_score REAL DEFAULT 0.8,
    extracted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- User memory - patterns, preferences, behavioral insights
CREATE TABLE user_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    memory_type TEXT NOT NULL, -- preference, pattern, fact, relationship
    memory_key TEXT NOT NULL, -- e.g., 'preferred_export_format', 'frequent_vendor'
    memory_value TEXT NOT NULL, -- JSON or plain text
    confidence_score REAL DEFAULT 0.8,
    evidence_count INTEGER DEFAULT 1, -- how many times observed
    last_reinforced DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    workspace_id TEXT DEFAULT 'default',
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    UNIQUE(user_id, memory_key, workspace_id)
);

-- Memory embeddings for semantic search
CREATE TABLE memory_embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id INTEGER NOT NULL, -- references conversations.id
    content_type TEXT NOT NULL, -- message, summary, entity
    embedding_vector BLOB NOT NULL, -- serialized numpy array
    content_text TEXT NOT NULL, -- original text for reference
    metadata TEXT, -- JSON with additional context
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Session state tracking
CREATE TABLE session_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    state_key TEXT NOT NULL, -- active_filters, current_dataset, working_on
    state_value TEXT NOT NULL, -- JSON
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    workspace_id TEXT DEFAULT 'default',
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    UNIQUE(session_id, user_id, state_key)
);

-- Memory retrieval cache for performance
CREATE TABLE memory_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT UNIQUE NOT NULL, -- hash of query parameters
    cache_data TEXT NOT NULL, -- JSON result
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    hit_count INTEGER DEFAULT 0
);

-- Memory analytics for insights
CREATE TABLE memory_analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    metric_name TEXT NOT NULL, -- total_conversations, avg_session_length, etc.
    metric_value REAL NOT NULL,
    metric_date DATE NOT NULL,
    workspace_id TEXT DEFAULT 'default',
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Indexes for performance
CREATE INDEX idx_conversation_threads_user ON conversation_threads(user_id);
CREATE INDEX idx_conversation_threads_active ON conversation_threads(is_active, last_activity);
CREATE INDEX idx_conversations_thread ON conversations(thread_id);
CREATE INDEX idx_conversations_user_time ON conversations(user_id, timestamp);
CREATE INDEX idx_conversations_tool ON conversations(tool_name);
CREATE INDEX idx_entity_mentions_conversation ON entity_mentions(conversation_id);
CREATE INDEX idx_entity_mentions_entity ON entity_mentions(entity_type, entity_id);
CREATE INDEX idx_user_memory_user ON user_memory(user_id, memory_type);
CREATE INDEX idx_memory_embeddings_content ON memory_embeddings(content_id, content_type);
CREATE INDEX idx_session_states_session ON session_states(session_id, user_id);
CREATE INDEX idx_memory_cache_key ON memory_cache(cache_key);

-- Views for common queries
CREATE VIEW active_conversations AS
SELECT 
    c.*,
    ct.title as thread_title,
    ct.thread_type
FROM conversations c
JOIN conversation_threads ct ON c.thread_id = ct.thread_id
WHERE ct.is_active = 1;

CREATE VIEW user_conversation_summary AS
SELECT 
    user_id,
    COUNT(DISTINCT thread_id) as total_threads,
    COUNT(*) as total_messages,
    MAX(timestamp) as last_activity,
    AVG(importance_score) as avg_importance
FROM conversations
WHERE timestamp >= datetime('now', '-30 days')
GROUP BY user_id;