# Database initialization script

from database.connection import db_manager
from database.sample_data import insert_sample_permissions, print_permission_summary


def initialize_database(db_path: str = "finkraftai.db"):
    """Initialize the database with schema and sample data"""
    
    print(f"Initializing FinkraftAI database: {db_path}")
    
    # Database manager will create schema automatically
    db_manager.db_path = db_path
    db_manager.ensure_database_exists()
    
    print("✓ Database initialization complete!")
    print_permission_summary(db_path)


if __name__ == "__main__":
    initialize_database()