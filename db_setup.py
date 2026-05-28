import os
import sys
import pymysql
from dotenv import load_dotenv

# Load project path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, '.env'))

def create_mysql_database():
    """
    Connects to a MySQL server using credentials from .env and creates the
    target database if it doesn't already exist.
    """
    user     = os.environ.get('MYSQL_USER')
    password = os.environ.get('MYSQL_PASSWORD', '')
    host     = os.environ.get('MYSQL_HOST', 'localhost')
    port     = int(os.environ.get('MYSQL_PORT', 3306))
    db_name  = os.environ.get('MYSQL_DB')

    if not user or not db_name:
        print("[ERROR] MYSQL_USER and MYSQL_DB must be set in your .env file.")
        sys.exit(1)

    print(f"Connecting to MySQL server at {host}:{port} as '{user}'...")

    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            connect_timeout=10
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.commit()
        cursor.close()
        conn.close()
        print(f"[OK] MySQL database '{db_name}' created/verified successfully.")
        return True
    except pymysql.Error as e:
        print(f"[ERROR] Could not connect to MySQL: {e}")
        print("       Please check your .env file credentials and ensure MySQL is running.")
        return False


def seed_database():
    """Run generate_data.py to create tables, train models, seed records."""
    from generate_data import setup_initial_database
    setup_initial_database()


if __name__ == '__main__':
    print("=" * 60)
    print("  SentryML — MySQL Database Setup Script")
    print("=" * 60)

    success = create_mysql_database()
    if not success:
        sys.exit(1)

    print("\nCreating tables, training ML models, and seeding data...")
    seed_database()

    print("\n[DONE] MySQL database is fully initialised.")
    print("       You can now (re)start app.py to use MySQL.")
