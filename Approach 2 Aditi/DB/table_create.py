import sqlite3


conn = sqlite3.connect("chatbot.db")
cursor = conn.cursor()



# Create tables
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    password TEXT NOT NULL,
    role TEXT NOT NULL
);
""")


''''This table will store all open tickets raised by user'''
cursor.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY,
    user_id INTEGER,
    short_description TEXT,
    description TEXT,
    creation_time TEXT,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    role TEXT,
    message TEXT NOT NULL,
    sender TEXT NOT NULL, -- 'user' or 'assistant'
    session_id TEXT,
    workspace_id TEXT DEFAULT 'default',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
""")

conn.commit()
conn.close()
