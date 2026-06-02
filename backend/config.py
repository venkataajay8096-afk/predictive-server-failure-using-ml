import os
from dotenv import load_dotenv

# BASE_DIR points to the project root (one level up from backend/)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables from .env file if it exists
load_dotenv(os.path.join(BASE_DIR, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'predictive-server-failure-detect-key-9821'
    
    # Database Configuration: MySQL support with local SQLite fallback
    MYSQL_USER = os.environ.get('MYSQL_USER')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD')
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = os.environ.get('MYSQL_PORT', '3306')
    MYSQL_DB = os.environ.get('MYSQL_DB')
    
    if MYSQL_USER and MYSQL_DB:
        # Try to connect to MySQL to verify it is online and credentials are valid
        try:
            import pymysql
            conn = pymysql.connect(
                host=MYSQL_HOST,
                port=int(MYSQL_PORT or 3306),
                user=MYSQL_USER,
                password=MYSQL_PASSWORD or '',
                connect_timeout=2
            )
            conn.close()
            SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
            print(f"[DATABASE] Successfully connected to MySQL at {MYSQL_HOST}:{MYSQL_PORT}. Active engine: MySQL.")
        except Exception as e:
            print(f"[DATABASE WARNING] MySQL is configured in .env but connection failed: {e}")
            print("[DATABASE WARNING] Gracefully falling back to local SQLite database ('database/project.db').")
            SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'database', 'project.db')
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'database', 'project.db')
        print("[DATABASE] Using local SQLite database ('database/project.db').")
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ML Models Configuration
    SAVED_MODELS_DIR = os.path.join(BASE_DIR, 'backend', 'saved_models')
    
    # Simulation settings
    SIMULATION_INTERVAL = 3.0  # seconds between metric generation
    ALERT_THRESHOLD = 0.80     # Trigger critical alert if failure probability >= 80%
    WARNING_THRESHOLD = 0.50   # Trigger warning if failure probability >= 50%
