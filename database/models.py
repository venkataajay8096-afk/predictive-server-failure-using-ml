from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class ServerMetrics(db.Model):
    __tablename__ = 'server_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    cpu_usage = db.Column(db.Float, nullable=False)          # %
    memory_usage = db.Column(db.Float, nullable=False)       # %
    temperature = db.Column(db.Float, nullable=False)        # °C
    disk_health = db.Column(db.Float, nullable=False)        # % health (or usage, let's store health where lower is worse)
    network_traffic = db.Column(db.Float, nullable=False)    # Mbps
    
    # ML Prediction fields
    predicted_failure = db.Column(db.Integer, default=0)     # 0 = Normal, 1 = Predicted Failure
    failure_probability = db.Column(db.Float, default=0.0)   # 0.0 to 1.0
    active_model = db.Column(db.String(50), nullable=True)   # Model used for this prediction
    
    # Ground truth (if simulated or marked post-event)
    true_label = db.Column(db.Integer, default=0)            # 0 = Normal, 1 = Actual Failure
    failure_type = db.Column(db.String(50), default='Normal') # Normal, CPU Overheat, Memory Leak, Disk Error, etc.
    virus_active = db.Column(db.Boolean, default=False, nullable=False)
    system_mode = db.Column(db.String(50), default='Normal', nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'temperature': self.temperature,
            'disk_health': self.disk_health,
            'network_traffic': self.network_traffic,
            'predicted_failure': self.predicted_failure,
            'failure_probability': self.failure_probability,
            'active_model': self.active_model,
            'true_label': self.true_label,
            'failure_type': self.failure_type,
            'virus_active': self.virus_active,
            'system_mode': self.system_mode
        }


class FailureAlert(db.Model):
    __tablename__ = 'failure_alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    metric_id = db.Column(db.Integer, db.ForeignKey('server_metrics.id'), nullable=True)
    
    failure_type = db.Column(db.String(50), nullable=False)   # CPU Overheat, Memory Leak, etc.
    probability = db.Column(db.Float, nullable=False)         # e.g., 0.85 (85%)
    severity = db.Column(db.String(20), nullable=False)        # Info, Warning, Critical
    message = db.Column(db.Text, nullable=False)
    
    resolved = db.Column(db.Boolean, default=False, nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)
    
    # Relationship
    metric = db.relationship('ServerMetrics', backref='alerts')

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'metric_id': self.metric_id,
            'failure_type': self.failure_type,
            'probability': self.probability,
            'severity': self.severity,
            'message': self.message,
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolution_notes': self.resolution_notes
        }


class ModelPerformance(db.Model):
    __tablename__ = 'model_performance'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    model_name = db.Column(db.String(50), nullable=False, unique=True) # Random Forest, SVM, Neural Network, Logistic Regression
    
    accuracy = db.Column(db.Float, nullable=False)
    precision = db.Column(db.Float, nullable=False)
    recall = db.Column(db.Float, nullable=False)
    f1_score = db.Column(db.Float, nullable=False)
    training_time = db.Column(db.Float, nullable=False)       # seconds
    dataset_size = db.Column(db.Integer, nullable=False)       # number of samples
    
    is_active = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'model_name': self.model_name,
            'accuracy': self.accuracy,
            'precision': self.precision,
            'recall': self.recall,
            'f1_score': self.f1_score,
            'training_time': self.training_time,
            'dataset_size': self.dataset_size,
            'is_active': self.is_active
        }
