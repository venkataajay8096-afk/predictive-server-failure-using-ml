@echo off
cd /d "%~dp0"

echo ===== Checking Python =====
.venv\Scripts\python.exe --version
echo.

echo ===== Checking requirements =====
.venv\Scripts\python.exe -m pip list | findstr Flask
.venv\Scripts\python.exe -m pip list | findstr SQLAlchemy
echo.

echo ===== Testing imports =====
.venv\Scripts\python.exe -c "import flask; print('Flask OK')"
.venv\Scripts\python.exe -c "import flask_sqlalchemy; print('Flask-SQLAlchemy OK')"
.venv\Scripts\python.exe -c "from backend.config import Config; print('Config OK')"
.venv\Scripts\python.exe -c "from database.models import db; print('Database Models OK')"
.venv\Scripts\python.exe -c "from backend.ml_pipeline import MLPipeline; print('ML Pipeline OK')"
echo.

echo ===== Attempting to initialize database =====
.venv\Scripts\python.exe -c "from database.generate_data import setup_initial_database; setup_initial_database()"
echo Database initialization exit code: %errorlevel%
echo.

echo ===== Starting Flask (verbose output) =====
.venv\Scripts\python.exe -u run.py

pause
