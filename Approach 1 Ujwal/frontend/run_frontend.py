#!/usr/bin/env python3
"""
FinkraftAI Frontend Launcher
Run this to start the Streamlit frontend application
"""

import subprocess
import sys
import os

def main():
    print("🚀 Starting FinkraftAI Frontend...")
    print("📱 Streamlit Web Interface")
    print("🔗 Make sure backend is running on http://localhost:8000")
    print()
    
    # Change to frontend directory
    frontend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(frontend_dir)
    
    # Run streamlit
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0",
            "--theme.base", "light"
        ])
    except KeyboardInterrupt:
        print("\n👋 Frontend stopped")

if __name__ == "__main__":
    main()