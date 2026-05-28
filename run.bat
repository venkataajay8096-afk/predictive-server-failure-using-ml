@echo off
setlocal enabledelayedexpansion

set PROJECT_DIR=C:\Users\venka\Desktop\sever project
cd /d "%PROJECT_DIR%"

echo.
echo ========================================
echo   Server Failure Prediction - Startup
echo ========================================
echo.

REM Step 1: Install dependencies
echo [Step 1/3] Installing dependencies...
.venv\Scripts\python.exe -m pip install -r requirements.txt -q 2>&1 | find /V "WARNING"
echo [OK] Dependencies installed

REM Step 2: Initialize database and train models
echo.
echo [Step 2/3] Initializing database and ML models...
echo        (This may take 30-60 seconds on first run)
.venv\Scripts\python.exe -c "from generate_data import setup_initial_database; setup_initial_database()"
if errorlevel 1 (
    echo [WARNING] Database initialization issue detected
)
echo [OK] Database initialized

REM Step 3: Start Flask server
echo.
echo [Step 3/3] Starting Flask server...
echo.
echo ========================================
echo  Server running at: http://localhost:5000
echo ========================================
echo.

.venv\Scripts\python.exe app.py

pause
