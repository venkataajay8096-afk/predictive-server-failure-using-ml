@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo ========================================
echo   Server Failure Prediction App
echo ========================================
echo.

REM Activate venv and run with explicit error output
echo Activating virtual environment and starting app...
echo.

.venv\Scripts\python.exe -c "import sys; sys.path.insert(0, '.'); from backend.app import app; app.run(host='0.0.0.0', port=5000, debug=False)"

if errorlevel 1 (
    echo.
    echo ERROR: App failed to start. See errors above.
    echo.
)

pause
