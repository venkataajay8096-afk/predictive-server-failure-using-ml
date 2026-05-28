#!/usr/bin/env python
"""
Simplified startup script - handles database init and server start
"""
import os
import sys

# Add project to path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

print("\n" + "="*50)
print("  Server Failure Prediction - Startup")
print("="*50 + "\n")

# Step 1: Initialize database
print("[1/2] Initializing database and ML models...")
try:
    from generate_data import setup_initial_database
    setup_initial_database()
    print("[OK] Database initialized\n")
except Exception as e:
    print(f"[WARNING] Database init error: {e}\n")
    print("Continuing anyway...\n")

# Step 2: Start Flask app
print("[2/2] Starting Flask server...")
print("\n" + "="*50)
print("  Server running at: http://localhost:5000")
print("="*50 + "\n")

try:
    from app import app
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
except Exception as e:
    print(f"ERROR: Failed to start server: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
