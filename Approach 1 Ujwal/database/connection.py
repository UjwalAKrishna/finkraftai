# Database connection management

import sqlite3
import os
from contextlib import contextmanager
from typing import Optional


class DatabaseManager:
    """Simple database connection manager"""
    
    def __init__(self, db_path: str = "finkraftai.db"):
        self.db_path = db_path
        self.ensure_database_exists()
    
    def ensure_database_exists(self):
        """Create database and tables if they don't exist"""
        if not os.path.exists(self.db_path):
            self.initialize_database()
    
    def initialize_database(self):
        """Initialize database with schema and sample data"""
        print(f"Initializing database: {self.db_path}")
        
        # Create schema
        conn = sqlite3.connect(self.db_path)
        try:
            with open("database/migrations/001_initial_schema.sql", "r") as f:
                schema_sql = f.read()
            conn.executescript(schema_sql)
            conn.commit()

            with open("database/migrations/002_memory_schema.sql", "r") as f:
                schema_sql = f.read()
            conn.executescript(schema_sql)
            conn.commit()
            print("✓ Database schema created")
            
            # Insert sample data
            from database.sample_data import insert_sample_permissions
            conn.close()  # Close before sample_data opens it
            insert_sample_permissions(self.db_path)
            
        except Exception as e:
            print(f"Error initializing database: {e}")
            conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
        finally:
            conn.close()
    
    def execute_query(self, query: str, params: tuple = (), fetch_one: bool = False):
        """Execute a query and return results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if query.strip().upper().startswith('SELECT'):
                return cursor.fetchone() if fetch_one else cursor.fetchall()
            else:
                conn.commit()
                return cursor.lastrowid

# Global database manager instance
db_manager = DatabaseManager()