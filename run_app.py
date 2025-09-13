# Simple application launcher

import uvicorn
import os
import sys

def main():
    """Start the FastAPI backend server"""
    
    print("🚀 Starting FinkraftAI Backend...")
    print("📊 Database-driven permission system")
    print("🔧 Simple tools: filter_data, export_report, create_ticket, view_tickets, update_ticket")
    print("👥 Roles: Admin, Manager, Viewer")
    print()
    
    # Ensure database exists
    from database.connection import db_manager
    db_manager.ensure_database_exists()
    
    print("✅ Database ready")
    print("🌐 Starting server at http://localhost:8000")
    print("📖 API docs at http://localhost:8000/docs")
    print()
    
    # Start FastAPI server
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()