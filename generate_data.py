import os
import sys
from datetime import datetime, timedelta
import random

# Add project path to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from config import Config
from models.database import db, ServerMetrics, ModelPerformance, FailureAlert
from models.ml_pipeline import MLPipeline

def setup_initial_database():
    print("Setting up database and generating initial ML models...")
    
    # Initialize a temporary Flask app to bind the SQLAlchemy db context
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    
    with app.app_context():
        # Recreate tables
        db.drop_all()
        db.create_all()
        print("Database tables created successfully.")
        
        # Instantiate pipeline and generate training dataset
        pipeline = MLPipeline()
        print("Generating 2,000 synthetic historical server log records...")
        df_train = pipeline.generate_synthetic_data(num_samples=2000, random_seed=42)
        
        # Train all models
        print("Training Random Forest, Support Vector Machine, Neural Network, and Logistic Regression models...")
        stats = pipeline.train_models(df_train)
        print("Model training completed successfully.")
        
        # Save performance statistics in the DB
        active_model = 'Random Forest'
        for model_name, metrics in stats.items():
            perf = ModelPerformance(
                model_name=model_name,
                accuracy=metrics['accuracy'],
                precision=metrics['precision'],
                recall=metrics['recall'],
                f1_score=metrics['f1_score'],
                training_time=metrics['training_time'],
                dataset_size=metrics['dataset_size'],
                is_active=(model_name == active_model)
            )
            db.session.add(perf)
            print(f"[{model_name}] Accuracy: {metrics['accuracy']:.4f} | Recall: {metrics['recall']:.4f} | Training Time: {metrics['training_time']:.4f}s")
            
        # Seed 100 historical logs for visual charts on dashboard
        print("Seeding 100 historical metrics records in database...")
        now = datetime.utcnow()
        for i in range(100):
            # Let's make it a normal workload with some random variance
            time_offset = now - timedelta(minutes=(100 - i))
            
            # Normal workload
            cpu = random.uniform(15, 45) + (5 * (i % 5 == 0))
            mem = random.uniform(30, 55)
            temp = random.uniform(38, 52)
            disk = random.uniform(92, 98)
            net = random.uniform(5, 40)
            
            # Let's inject a brief simulated overheat anomaly in the past (around index 70-75)
            true_label = 0
            fail_type = 'Normal'
            if 70 <= i <= 75:
                cpu = random.uniform(90, 95)
                temp = random.uniform(85, 90)
                true_label = 1
                fail_type = 'CPU Overheat'
                
            pred_fail, fail_prob = pipeline.predict('Random Forest', cpu, mem, temp, disk, net)
            
            metric = ServerMetrics(
                timestamp=time_offset,
                cpu_usage=cpu,
                memory_usage=mem,
                temperature=temp,
                disk_health=disk,
                network_traffic=net,
                predicted_failure=pred_fail,
                failure_probability=fail_prob,
                active_model='Random Forest',
                true_label=true_label,
                failure_type=fail_type
            )
            db.session.add(metric)
            
            # If it was an overheat failure, also add an alert log!
            if true_label == 1 and i == 72:
                alert = FailureAlert(
                    timestamp=time_offset,
                    failure_type='CPU Overheat',
                    probability=fail_prob,
                    severity='Critical',
                    message=f"CRITICAL ALERT: CPU temperature spiked to {temp:.1f}°C (CPU usage: {cpu:.1f}%). High risk of core damage or crash.",
                    resolved=True,
                    resolved_at=time_offset + timedelta(minutes=15),
                    resolution_notes="Automatic thermal mitigation triggered. CPU load cooled down."
                )
                db.session.add(alert)
                
        db.session.commit()
        print("Database seeded with historical metrics and historical resolved alerts successfully!")

if __name__ == '__main__':
    setup_initial_database()
