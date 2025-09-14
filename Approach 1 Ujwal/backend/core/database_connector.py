# Database connection management for external business databases

import sqlite3
import json
import os
from typing import Dict, List, Any, Optional
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """Database connection configuration"""
    name: str
    type: str  # sqlite, mysql, postgresql, etc.
    host: str = None
    port: int = None
    database: str = None
    username: str = None
    password: str = None
    file_path: str = None  # For SQLite
    schema: str = None


class DatabaseConnector:
    """Manages connections to external business databases"""
    
    def __init__(self):
        self.connections = {}
        self.load_database_configs()
    
    def load_database_configs(self):
        """Load database configurations"""
        
        # For MVP, we'll use a simple config
        # In production, this would come from secure config/environment
        self.configs = {
            'business_db': DatabaseConfig(
                name='business_db',
                type='sqlite',
                file_path='business_data.db',
                schema='main'
            ),
            # Example of how other databases would be configured
            'customer_mysql': DatabaseConfig(
                name='customer_mysql',
                type='mysql',
                host='localhost',
                port=3306,
                database='customer_business',
                username='user',
                password='password'
            )
        }
    
    @contextmanager
    def get_connection(self, db_name: str = 'business_db'):
        """Get database connection with automatic cleanup"""
        
        if db_name not in self.configs:
            raise ValueError(f"Database '{db_name}' not configured")
        
        config = self.configs[db_name]
        
        if config.type == 'sqlite':
            conn = sqlite3.connect(config.file_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
        elif config.type == 'mysql':
            # Would implement MySQL connection here
            raise NotImplementedError("MySQL support not implemented yet")
        elif config.type == 'postgresql':
            # Would implement PostgreSQL connection here
            raise NotImplementedError("PostgreSQL support not implemented yet")
        else:
            raise ValueError(f"Unsupported database type: {config.type}")
        
        try:
            yield conn
        finally:
            conn.close()
    
    def execute_query(self, query: str, params: tuple = (), db_name: str = 'business_db', fetch_one: bool = False):
        """Execute query on specified database"""
        
        with self.get_connection(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if query.strip().upper().startswith('SELECT'):
                if fetch_one:
                    result = cursor.fetchone()
                    return dict(result) if result else None
                else:
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
            else:
                conn.commit()
                return cursor.lastrowid
    
    def get_table_schema(self, table_name: str, db_name: str = 'business_db') -> List[Dict]:
        """Get table schema information"""
        
        config = self.configs[db_name]
        
        if config.type == 'sqlite':
            query = f"PRAGMA table_info({table_name})"
            results = self.execute_query(query, db_name=db_name)
            
            schema = []
            for row in results:
                schema.append({
                    'column_name': row['name'],
                    'data_type': row['type'],
                    'nullable': not row['notnull'],
                    'primary_key': row['pk'] == 1
                })
            return schema
        else:
            # Would implement for other database types
            raise NotImplementedError(f"Schema introspection not implemented for {config.type}")
    
    def get_available_tables(self, db_name: str = 'business_db') -> List[str]:
        """Get list of available tables"""
        
        config = self.configs[db_name]
        
        if config.type == 'sqlite':
            query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            results = self.execute_query(query, db_name=db_name)
            return [row['name'] for row in results]
        else:
            raise NotImplementedError(f"Table listing not implemented for {config.type}")
    
    def test_connection(self, db_name: str = 'business_db') -> bool:
        """Test database connection"""
        
        try:
            with self.get_connection(db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            print(f"Connection test failed for {db_name}: {e}")
            return False
    
    def get_database_info(self, db_name: str = 'business_db') -> Dict[str, Any]:
        """Get database information and statistics"""
        
        try:
            with self.get_connection(db_name) as conn:
                cursor = conn.cursor()
                
                info = {
                    'database_name': db_name,
                    'config': self.configs[db_name].__dict__,
                    'tables': {},
                    'connection_status': 'connected'
                }
                
                # Get table information
                tables = self.get_available_tables(db_name)
                
                for table in tables:
                    try:
                        # Get row count
                        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                        row_count = cursor.fetchone()[0]
                        
                        # Get schema
                        schema = self.get_table_schema(table, db_name)
                        
                        info['tables'][table] = {
                            'row_count': row_count,
                            'columns': len(schema),
                            'schema': schema
                        }
                    except Exception as e:
                        info['tables'][table] = {'error': str(e)}
                
                return info
                
        except Exception as e:
            return {
                'database_name': db_name,
                'connection_status': 'failed',
                'error': str(e)
            }


# Global database connector instance
db_connector = DatabaseConnector()