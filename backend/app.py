import os
import re
import threading
import time
import random
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
import pymysql
from sqlalchemy import inspect, text

from backend.config import Config
from database.models import db, ServerMetrics, FailureAlert, ModelPerformance
from backend.ml_pipeline import MLPipeline

# Project root directory (one level up from backend/)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

app = Flask(
    __name__,
    template_folder=os.path.join(PROJECT_ROOT, 'frontend', 'templates'),
    static_folder=os.path.join(PROJECT_ROOT, 'frontend', 'static')
)
app.config.from_object(Config)
db.init_app(app)


def ensure_database_schema():
    """Ensure the existing SQLite schema includes the virus alert fields used by the dashboard."""
    with app.app_context():
        db.create_all()
        inspector = inspect(db.engine)
        if 'server_metrics' not in inspector.get_table_names():
            return

        columns = {column['name'] for column in inspector.get_columns('server_metrics')}
        if 'virus_active' not in columns:
            db.session.execute(text('ALTER TABLE server_metrics ADD COLUMN virus_active BOOLEAN DEFAULT 0 NOT NULL'))
        if 'system_mode' not in columns:
            db.session.execute(text("ALTER TABLE server_metrics ADD COLUMN system_mode VARCHAR(50) DEFAULT 'Normal' NOT NULL"))
        db.session.commit()


ensure_database_schema()

# Global ML Pipeline instance
pipeline = MLPipeline()

# Global Simulation state
# Modes: 'Normal', 'CPU Overheat', 'Memory Leak', 'Disk Failure', 'Network Saturation'
SIMULATION_STATE = {
    'mode': 'Normal',
    'active_model': 'Random Forest',
    'is_running': True,
    'last_metric': None
}

def get_active_model_name():
    """Helper to query the DB or fallback to global state for the active model name."""
    try:
        active_model = ModelPerformance.query.filter_by(is_active=True).first()
        if active_model:
            SIMULATION_STATE['active_model'] = active_model.model_name
            return active_model.model_name
    except Exception as e:
        print(f"Error querying active model: {e}")
    return SIMULATION_STATE['active_model']


def metric_simulation_worker(app_instance):
    """
    Background worker that runs continuously to simulate live server sensor metrics,
    predict failure probability using the active ML model, and trigger alerts if necessary.
    """
    print("Background metric simulation thread started.")
    
    with app_instance.app_context():
        # Ensure database and models are loaded
        # Attempt to load trained models. If they are not trained, load_models will fail.
        # It's expected that generate_data.py has already run.
        pipeline.load_models()
        
        while SIMULATION_STATE['is_running']:
            try:
                mode = SIMULATION_STATE['mode']
                active_model = get_active_model_name()
                
                # 1. Simulate base metrics according to the selected mode
                cpu = 0.0
                mem = 0.0
                temp = 0.0
                disk = 0.0
                net = 0.0
                
                if mode == 'Normal':
                    cpu = random.uniform(20, 55)
                    mem = random.uniform(35, 60)
                    temp = random.uniform(40, 55)
                    disk = random.uniform(92, 98) # Healthy
                    net = random.uniform(15, 60) # Mbps
                elif mode == 'CPU Overheat':
                    # CPU usage climbs towards 95-100%, temperature rapidly spikes
                    cpu = random.uniform(85, 98)
                    mem = random.uniform(40, 65)
                    temp = random.uniform(82, 102) # Danger zone
                    disk = random.uniform(85, 95)
                    net = random.uniform(20, 80)
                elif mode == 'Memory Leak':
                    # Memory usage climbs to near 100%, CPU moderately high
                    cpu = random.uniform(50, 75)
                    mem = random.uniform(91, 99.5) # Leak
                    temp = random.uniform(55, 72)
                    disk = random.uniform(85, 95)
                    net = random.uniform(20, 80)
                elif mode == 'Disk Failure':
                    # Disk health plummets rapidly, other metrics relatively normal
                    cpu = random.uniform(15, 45)
                    mem = random.uniform(30, 55)
                    temp = random.uniform(38, 52)
                    disk = random.uniform(5, 28) # Impending crash
                    net = random.uniform(5, 45)
                elif mode == 'Network Saturation':
                    # DDOS simulation - huge network traffic, very high CPU load
                    cpu = random.uniform(80, 95)
                    mem = random.uniform(45, 70)
                    temp = random.uniform(62, 79)
                    disk = random.uniform(80, 95)
                    net = random.uniform(780, 1040) # Saturation in Mbps
                
                # 2. Run ML prediction on the simulated metrics
                predicted_fail = 0
                fail_prob = 0.0
                
                if pipeline.is_trained:
                    try:
                        predicted_fail, fail_prob = pipeline.predict(
                            active_model, cpu, mem, temp, disk, net
                        )
                    except Exception as ex:
                        print(f"Prediction error: {ex}")
                        predicted_fail = 1 if (cpu > 80 or mem > 90 or temp > 80 or disk < 30 or net > 500) else 0
                        fail_prob = 0.95 if predicted_fail else 0.15
                else:
                    # Fallback if model not trained yet
                    predicted_fail = 1 if (cpu > 80 or mem > 90 or temp > 80 or disk < 30 or net > 500) else 0
                    fail_prob = 0.95 if predicted_fail else 0.15
                
                # 3. Write metric records to database
                metric = ServerMetrics(
                    cpu_usage=cpu,
                    memory_usage=mem,
                    temperature=temp,
                    disk_health=disk,
                    network_traffic=net,
                    predicted_failure=predicted_fail,
                    failure_probability=fail_prob,
                    active_model=active_model,
                    true_label=1 if mode != 'Normal' else 0,
                    failure_type=mode
                )
                db.session.add(metric)
                db.session.commit()
                
                # Cache latest metric in memory for fast socket-free polling API
                SIMULATION_STATE['last_metric'] = metric.to_dict()
                
                # 4. Handle Alerts
                # Trigger an alert if fail probability exceeds threshold and we don't already have
                # an active alert of the same type in the last 1 minute
                if fail_prob >= Config.ALERT_THRESHOLD:
                    one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
                    existing_active_alert = FailureAlert.query.filter(
                        FailureAlert.failure_type == mode,
                        FailureAlert.resolved == False,
                        FailureAlert.timestamp >= one_minute_ago
                    ).first()
                    
                    if not existing_active_alert:
                        severity = 'Critical' if fail_prob >= 0.90 else 'Warning'
                        message = ""
                        if mode == 'CPU Overheat':
                            message = f"CRITICAL: Thermal shutdown threat! CPU temperature at {temp:.1f}°C and CPU load at {cpu:.1f}%. High risk of physical hardware failure."
                        elif mode == 'Memory Leak':
                            message = f"CRITICAL: Severe resource exhaustion! Memory utilization is at {mem:.1f}%. Out-of-memory (OOM) daemon may kill critical processes."
                        elif mode == 'Disk Failure':
                            message = f"CRITICAL: Storage health deterioration! Hard drive SMART status reporting critical condition: {disk:.1f}% health remaining. Backup immediately."
                        elif mode == 'Network Saturation':
                            message = f"WARNING: Network saturation detected! Bandwidth throughput is extremely high at {net:.1f} Mbps. System is processing heavy packets, possible DDoS attack."
                        else:
                            message = f"ALERT: Server anomaly detected! Active ML model predicts imminent failure probability of {fail_prob*100:.1f}%."
                            
                        alert = FailureAlert(
                            metric_id=metric.id,
                            failure_type=mode if mode != 'Normal' else 'Anomalous Activity',
                            probability=fail_prob,
                            severity=severity,
                            message=message,
                            resolved=False
                        )
                        db.session.add(alert)
                        db.session.commit()
                        print(f"ALERT TRIGGERED: {message}")
                
                # 5. DB Cleanup: keep only last 500 rows to ensure database size remains compact
                row_count = ServerMetrics.query.count()
                if row_count > 500:
                    oldest_records = ServerMetrics.query.order_by(ServerMetrics.timestamp.asc()).limit(row_count - 500).all()
                    for r in oldest_records:
                        db.session.delete(r)
                    db.session.commit()
                    
            except Exception as e:
                db.session.rollback()
                print(f"Error in background simulator: {e}")
                
            # Wait for next simulation interval
            time.sleep(Config.SIMULATION_INTERVAL)


# ==========================================
# PAGE CONTROLLERS (Web Pages)
# ==========================================

@app.route('/')
def dashboard():
    """Main live analytics dashboard page."""
    return render_template('index.html', active_page='dashboard')

@app.route('/ml-studio')
def ml_studio():
    """Machine learning model metrics, training, and performance comparisons page."""
    return render_template('ml_studio.html', active_page='ml_studio')

@app.route('/alerts')
def alerts_page():
    """Alerts history, detail view, and resolution page."""
    return render_template('alerts.html', active_page='alerts')


@app.route('/db-config')
def db_config_page():
    """Database configuration and connection management page."""
    return render_template('db_config.html', active_page='db_config')


# ==========================================
# REST API ENDPOINTS
# ==========================================

@app.route('/api/metrics/live', methods=['GET'])
def get_live_metrics():
    """Fetch the latest server metrics and modify them if a virus is active."""
    latest_metric = ServerMetrics.query.order_by(ServerMetrics.timestamp.desc()).first()
    if not latest_metric:
        return jsonify({"success": False, "message": "No metrics available."}), 404

    # Modify metrics if virus is active
    if latest_metric.virus_active:
        latest_metric.cpu_usage = 95.0  # Force CPU spike
        latest_metric.temperature = 90.0  # Critical temperature
        latest_metric.system_mode = 'CRITICAL ALERT'

    return jsonify({
        "success": True,
        "metric": {
            "cpu_usage": latest_metric.cpu_usage,
            "memory_usage": latest_metric.memory_usage,
            "temperature": latest_metric.temperature,
            "disk_health": latest_metric.disk_health,
            "network_traffic": latest_metric.network_traffic,
            "failure_probability": latest_metric.failure_probability,
            "system_mode": latest_metric.system_mode,
            "virus_active": latest_metric.virus_active
        }
    })


@app.route('/api/trigger-virus', methods=['POST'])
def trigger_virus():
    """Toggle the virus alert state to simulate malicious activity."""
    try:
        latest_metric = ServerMetrics.query.order_by(ServerMetrics.timestamp.desc()).first()
        if not latest_metric:
            return jsonify({'success': False, 'message': 'No metrics found.'}), 404

        latest_metric.virus_active = True
        latest_metric.system_mode = 'CRITICAL ALERT'
        latest_metric.cpu_usage = 95.0
        latest_metric.temperature = 90.0
        db.session.commit()

        SIMULATION_STATE['mode'] = 'CRITICAL ALERT'
        SIMULATION_STATE['last_metric'] = latest_metric.to_dict()

        return jsonify({'success': True, 'message': 'Virus activated.', 'system_mode': latest_metric.system_mode})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/activate-antigravity', methods=['POST'])
def activate_antigravity():
    """Lift the virus into an isolated sandbox and restore normal telemetry state."""
    try:
        latest_metric = ServerMetrics.query.order_by(ServerMetrics.timestamp.desc()).first()
        if not latest_metric:
            return jsonify({'success': False, 'message': 'No metrics found.'}), 404

        latest_metric.virus_active = False
        latest_metric.system_mode = 'Normal'
        latest_metric.cpu_usage = 33.4
        latest_metric.temperature = 44.1
        latest_metric.failure_probability = 0.0
        db.session.commit()

        SIMULATION_STATE['mode'] = 'Normal'
        SIMULATION_STATE['last_metric'] = latest_metric.to_dict()

        alert = FailureAlert(
            timestamp=datetime.utcnow(),
            failure_type='Virus Remediation',
            probability=0.0,
            severity='Info',
            message='Virus lifted into isolated Zero-G sandbox and purged.'
        )
        db.session.add(alert)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Virus lifted into isolated Zero-G sandbox and purged.', 'system_mode': latest_metric.system_mode})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/metrics/latest', methods=['GET'])
def get_latest_metric():
    """Returns the single latest simulated metric, for quick polling updates."""
    try:
        last = SIMULATION_STATE['last_metric']
        if not last:
            # Fallback to DB
            record = ServerMetrics.query.order_by(ServerMetrics.timestamp.desc()).first()
            if record:
                last = record.to_dict()
                SIMULATION_STATE['last_metric'] = last
                
        active_model = get_active_model_name()
        
        return jsonify({
            'success': True,
            'metric': last,
            'active_model': active_model,
            'current_mode': SIMULATION_STATE['mode']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/simulation/state', methods=['GET', 'POST'])
def handle_simulation_state():
    """Gets or sets the current simulation mode (used for Fault Injection)."""
    if request.method == 'POST':
        data = request.get_json() or {}
        new_mode = data.get('mode')
        
        valid_modes = ['Normal', 'CPU Overheat', 'Memory Leak', 'Disk Failure', 'Network Saturation']
        if new_mode not in valid_modes:
            return jsonify({'success': False, 'error': f"Invalid mode. Choose from {valid_modes}"}), 400
            
        SIMULATION_STATE['mode'] = new_mode
        print(f"Simulation mode changed to: {new_mode}")
        return jsonify({'success': True, 'mode': new_mode})
        
    return jsonify({
        'success': True,
        'mode': SIMULATION_STATE['mode']
    })


@app.route('/api/models', methods=['GET'])
def get_models_info():
    """Returns lists of models, their DB-stored accuracy stats, and active status."""
    try:
        models_data = ModelPerformance.query.order_by(ModelPerformance.accuracy.desc()).all()
        return jsonify({
            'success': True,
            'models': [m.to_dict() for m in models_data],
            'active_model': get_active_model_name()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/models/activate', methods=['POST'])
def activate_model():
    """Swaps the active machine learning model for predictions."""
    try:
        data = request.get_json() or {}
        model_name = data.get('model_name')
        
        if not model_name:
            return jsonify({'success': False, 'error': "model_name parameter is required"}), 400
            
        # Verify model exists in DB
        model = ModelPerformance.query.filter_by(model_name=model_name).first()
        if not model:
            return jsonify({'success': False, 'error': f"Model '{model_name}' not found in database"}), 404
            
        # Deactivate all models
        ModelPerformance.query.update({ModelPerformance.is_active: False})
        
        # Activate target model
        model.is_active = True
        db.session.commit()
        
        SIMULATION_STATE['active_model'] = model_name
        print(f"Active ML model switched to: {model_name}")
        
        return jsonify({
            'success': True,
            'active_model': model_name,
            'message': f"Successfully activated model '{model_name}'."
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/models/train', methods=['POST'])
def train_models_endpoint():
    """
    Triggers model retraining. It regenerates a synthetic dataset with custom size 
    and trains all four models, updating their performance statistics in the DB.
    """
    try:
        data = request.get_json() or {}
        dataset_size = int(data.get('dataset_size', 2000))
        
        if dataset_size < 500 or dataset_size > 10000:
            return jsonify({'success': False, 'error': "Dataset size must be between 500 and 10,000 samples."}), 400
            
        # Run training in main thread (or lock to prevent parallel training conflicts)
        print(f"Retraining requested with dataset size: {dataset_size}")
        df = pipeline.generate_synthetic_data(num_samples=dataset_size, random_seed=int(time.time()))
        stats = pipeline.train_models(df)
        
        # Update database with new training stats
        for name, metrics in stats.items():
            db_model = ModelPerformance.query.filter_by(model_name=name).first()
            if db_model:
                db_model.accuracy = metrics['accuracy']
                db_model.precision = metrics['precision']
                db_model.recall = metrics['recall']
                db_model.f1_score = metrics['f1_score']
                db_model.training_time = metrics['training_time']
                db_model.dataset_size = metrics['dataset_size']
                db_model.timestamp = datetime.utcnow()
            else:
                db_model = ModelPerformance(
                    model_name=name,
                    accuracy=metrics['accuracy'],
                    precision=metrics['precision'],
                    recall=metrics['recall'],
                    f1_score=metrics['f1_score'],
                    training_time=metrics['training_time'],
                    dataset_size=metrics['dataset_size'],
                    is_active=(name == SIMULATION_STATE['active_model'])
                )
                db.session.add(db_model)
                
        db.session.commit()
        pipeline.load_models() # Reload updated models
        
        # Query fresh performance entries to return
        models_data = ModelPerformance.query.order_by(ModelPerformance.accuracy.desc()).all()
        
        return jsonify({
            'success': True,
            'message': "All machine learning models retrained and updated successfully.",
            'models': [m.to_dict() for m in models_data],
            'active_model': get_active_model_name()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/alerts/active', methods=['GET'])
def get_active_alerts():
    """Returns all active (unresolved) server alerts."""
    try:
        alerts = FailureAlert.query.filter_by(resolved=False).order_by(FailureAlert.timestamp.desc()).all()
        return jsonify({
            'success': True,
            'alerts': [a.to_dict() for a in alerts]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/alerts/all', methods=['GET'])
def get_all_alerts():
    """Returns the entire historical log of alerts (limit 100)."""
    try:
        alerts = FailureAlert.query.order_by(FailureAlert.timestamp.desc()).limit(100).all()
        return jsonify({
            'success': True,
            'alerts': [a.to_dict() for a in alerts]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/alerts/resolve', methods=['POST'])
def resolve_alert():
    """Marks a specific alert as resolved with custom technician notes."""
    try:
        data = request.get_json() or {}
        alert_id = data.get('alert_id')
        notes = data.get('notes', 'Resolved by administrator.')
        
        if not alert_id:
            return jsonify({'success': False, 'error': "alert_id parameter is required"}), 400
            
        alert = FailureAlert.query.get(alert_id)
        if not alert:
            return jsonify({'success': False, 'error': f"Alert ID {alert_id} not found"}), 404
            
        alert.resolved = True
        alert.resolved_at = datetime.utcnow()
        alert.resolution_notes = notes
        
        db.session.commit()
        print(f"ALERT RESOLVED: Alert ID {alert_id} marked resolved with notes: '{notes}'")
        
        return jsonify({
            'success': True,
            'message': f"Alert ID {alert_id} successfully marked as resolved.",
            'alert': alert.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==========================================
# DATABASE CONFIG API ENDPOINTS
# ==========================================

def _read_env_vars():
    """Read current MySQL env vars from .env file."""
    env_path = os.path.join(PROJECT_ROOT, '.env')
    vals = {'MYSQL_USER': '', 'MYSQL_PASSWORD': '', 'MYSQL_HOST': 'localhost',
            'MYSQL_PORT': '3306', 'MYSQL_DB': ''}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    if k.strip() in vals:
                        vals[k.strip()] = v.strip()
    return vals


def _write_env_file(user='', password='', host='localhost', port='3306', db_name=''):
    """Write MySQL credentials (or clear them) to the .env file."""
    env_path = os.path.join(PROJECT_ROOT, '.env')
    secret = os.environ.get('SECRET_KEY', 'predictive-server-failure-detect-key-9821')
    lines = [
        '# =========================================================================\n',
        '# SENTRYML ENVIRONMENT CONFIGURATION\n',
        '# =========================================================================\n',
        '\n',
        f'SECRET_KEY={secret}\n',
        '\n',
        '# MySQL Connection Details\n',
    ]
    if user and db_name:
        lines += [
            f'MYSQL_USER={user}\n',
            f'MYSQL_PASSWORD={password}\n',
            f'MYSQL_HOST={host}\n',
            f'MYSQL_PORT={port}\n',
            f'MYSQL_DB={db_name}\n',
        ]
    else:
        lines += [
            '# MYSQL_USER=root\n',
            '# MYSQL_PASSWORD=\n',
            '# MYSQL_HOST=localhost\n',
            '# MYSQL_PORT=3306\n',
            '# MYSQL_DB=sentryml_db\n',
        ]
    with open(env_path, 'w') as f:
        f.writelines(lines)


@app.route('/api/db/status', methods=['GET'])
def db_status():
    """Return current database connection status and basic stats."""
    try:
        uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        is_mysql = uri.startswith('mysql')
        engine = 'MySQL' if is_mysql else 'SQLite'

        # Try a quick DB query to verify connectivity
        metric_count = ServerMetrics.query.count()
        alert_count  = FailureAlert.query.count()
        model_count  = ModelPerformance.query.count()
        tables = 3  # server_metrics, failure_alerts, model_performance

        env = _read_env_vars()
        host    = env.get('MYSQL_HOST', 'localhost') if is_mysql else 'local file'
        port    = env.get('MYSQL_PORT', '3306')      if is_mysql else '—'
        db_name = env.get('MYSQL_DB', 'project.db')  if is_mysql else 'project.db'
        user    = env.get('MYSQL_USER', '')           if is_mysql else '—'

        return jsonify({
            'connected': True,
            'engine':    engine,
            'host':      host,
            'port':      port,
            'db_name':   db_name,
            'user':      user,
            'tables':    tables,
            'records':   metric_count + alert_count + model_count,
            'uri_hint':  uri.split('@')[-1] if '@' in uri else uri.split(':///')[-1]
        })
    except Exception as e:
        return jsonify({'connected': False, 'engine': 'Unknown', 'error': str(e),
                        'host': '—', 'db_name': '—', 'tables': 0, 'records': 0})


@app.route('/api/db/test', methods=['POST'])
def db_test():
    """Test a MySQL connection with provided credentials (does NOT save)."""
    data     = request.get_json() or {}
    host     = data.get('host', 'localhost')
    port     = int(data.get('port', 3306))
    user     = data.get('user', '')
    password = data.get('password', '')
    db_name  = data.get('db_name', '')

    if not user or not db_name:
        return jsonify({'success': False, 'error': 'Username and Database Name are required.'}), 400

    try:
        conn = pymysql.connect(
            host=host, port=port, user=user, password=password,
            connect_timeout=8, autocommit=True
        )
        conn.close()
        return jsonify({
            'success': True,
            'message': f'Successfully connected to MySQL at {host}:{port} as "{user}". Ready to use database "{db_name}".'
        })
    except pymysql.Error as e:
        return jsonify({'success': False, 'error': f'MySQL connection failed: {e}'})


@app.route('/api/db/connect', methods=['POST'])
def db_connect():
    """Save credentials to .env and update the live database URI."""
    data       = request.get_json() or {}
    use_sqlite = data.get('use_sqlite', False)

    if use_sqlite:
        _write_env_file()  # Clear MySQL vars
        new_uri = 'sqlite:///' + os.path.join(PROJECT_ROOT, 'database', 'project.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = new_uri
        return jsonify({'success': True,
                        'message': 'Reverted to local SQLite database. Restart run.py to fully apply.'})

    host     = data.get('host', 'localhost')
    port     = str(data.get('port', '3306'))
    user     = data.get('user', '').strip()
    password = data.get('password', '')
    db_name  = data.get('db_name', '').strip()

    if not user or not db_name:
        return jsonify({'success': False, 'error': 'Username and Database Name are required.'})

    # First verify we can reach the server
    try:
        conn = pymysql.connect(
            host=host, port=int(port), user=user, password=password,
            connect_timeout=8, autocommit=True
        )
        cursor = conn.cursor()
        cursor.execute(f'CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;')
        conn.commit()
        cursor.close()
        conn.close()
    except pymysql.Error as e:
        return jsonify({'success': False, 'error': f'Cannot connect to MySQL: {e}'})

    # Save to .env
    _write_env_file(user=user, password=password, host=host, port=port, db_name=db_name)

    # Hot-swap the SQLAlchemy URI
    new_uri = f'mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}'
    app.config['SQLALCHEMY_DATABASE_URI'] = new_uri

    # Re-create tables in the new database
    try:
        with app.app_context():
            db.create_all()
    except Exception as e:
        return jsonify({'success': False, 'error': f'Database connected but table creation failed: {e}'})

    return jsonify({
        'success': True,
        'message': f'Connected to MySQL database "{db_name}" on {host}:{port}. Tables created. Restart run.py to fully activate the background simulator on the new database.'
    })


@app.route('/api/db/seed', methods=['POST'])
def db_seed():
    """Re-run initial data seeding and model training on the current database."""
    try:
        # Import and run the seeder within this app context
        import importlib, sys
        # Remove cached module so it re-runs cleanly
        if 'database.generate_data' in sys.modules:
            del sys.modules['database.generate_data']

        # We'll manually call the pipeline + DB seed steps here
        print('Re-seeding database from API request...')
        db.drop_all()
        db.create_all()

        from backend.ml_pipeline import MLPipeline as _PL
        pl = _PL()
        df = pl.generate_synthetic_data(num_samples=2000, random_seed=42)
        stats = pl.train_models(df)

        import random as _rnd
        now = datetime.utcnow()
        active_m = 'Random Forest'
        for model_name, metrics in stats.items():
            perf = ModelPerformance(
                model_name=model_name, accuracy=metrics['accuracy'],
                precision=metrics['precision'], recall=metrics['recall'],
                f1_score=metrics['f1_score'], training_time=metrics['training_time'],
                dataset_size=metrics['dataset_size'], is_active=(model_name == active_m)
            )
            db.session.add(perf)

        from datetime import timedelta as _td
        for i in range(100):
            ts  = now - _td(minutes=(100 - i))
            cpu = _rnd.uniform(15, 45)
            mem = _rnd.uniform(30, 55)
            tmp = _rnd.uniform(38, 52)
            dsk = _rnd.uniform(92, 98)
            net = _rnd.uniform(5, 40)
            true_l, ftype = 0, 'Normal'
            if 70 <= i <= 75:
                cpu, tmp, true_l, ftype = _rnd.uniform(90,95), _rnd.uniform(85,90), 1, 'CPU Overheat'
            pf, fp = pl.predict(active_m, cpu, mem, tmp, dsk, net)
            db.session.add(ServerMetrics(
                timestamp=ts, cpu_usage=cpu, memory_usage=mem, temperature=tmp,
                disk_health=dsk, network_traffic=net, predicted_failure=pf,
                failure_probability=fp, active_model=active_m,
                true_label=true_l, failure_type=ftype
            ))

        db.session.commit()
        pipeline.load_models()
        SIMULATION_STATE['active_model'] = active_m
        print('Database re-seeded successfully.')

        return jsonify({'success': True,
                        'message': '2,000 synthetic records generated, all 4 ML models retrained, and 100 historical log entries seeded successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


# Start the background simulator thread when Flask launches
def start_simulator_thread():
    simulator_thread = threading.Thread(
        target=metric_simulation_worker, 
        args=(app,), 
        daemon=True
    )
    simulator_thread.start()

# Only run simulator thread if not running in debug reloader subprocess
if not os.environ.get('WERKZEUG_RUN_MAIN'):
    # In development mode, Werkzeug runs two processes: one for monitoring, one for the app.
    # We want to start the thread only in the actual app process.
    # If not running under reloader, start it directly.
    start_simulator_thread()
else:
    # If reloader IS active, start it only in the worker process (which has WERKZEUG_RUN_MAIN=true)
    start_simulator_thread()

if __name__ == '__main__':
    # Ensure saved models and logs folders exist
    os.makedirs(app.config['SAVED_MODELS_DIR'], exist_ok=True)
    
    # Run server
    app.run(host='0.0.0.0', port=5000, debug=True)
