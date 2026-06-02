import os
import time
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import joblib

# Paths for saving models — backend/saved_models/
MODEL_DIR = os.path.join(os.path.dirname(__file__), 'saved_models')
os.makedirs(MODEL_DIR, exist_ok=True)

class MLPipeline:
    def __init__(self):
        self.models = {
            'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
            'Support Vector Machine': SVC(probability=True, random_state=42),
            'Neural Network': MLPClassifier(hidden_layer_sizes=(32, 16), max_iter=500, random_state=42),
            'Logistic Regression': LogisticRegression(random_state=42)
        }
        self.scaler = StandardScaler()
        self.active_model_name = 'Random Forest'
        self.is_trained = False
        
    def generate_synthetic_data(self, num_samples=2000, random_seed=42):
        """
        Generates realistic synthetic server metrics labeled as normal or containing 
        specific server failures.
        """
        np.random.seed(random_seed)
        
        # 1. Generate Normal Logs (approx 70% of dataset)
        num_normal = int(num_samples * 0.70)
        cpu_normal = np.random.uniform(10, 60, num_normal)
        mem_normal = np.random.uniform(20, 65, num_normal)
        temp_normal = np.random.uniform(35, 60, num_normal)
        disk_normal = np.random.uniform(80, 100, num_normal) # High health
        net_normal = np.random.uniform(2, 80, num_normal) # Mbps
        
        df_normal = pd.DataFrame({
            'cpu_usage': cpu_normal,
            'memory_usage': mem_normal,
            'temperature': temp_normal,
            'disk_health': disk_normal,
            'network_traffic': net_normal,
            'label': 0,
            'failure_type': 'Normal'
        })
        
        # 2. Generate CPU Overheat Logs (approx 8%)
        num_cpu_fail = int(num_samples * 0.08)
        cpu_fail = np.random.uniform(88, 100, num_cpu_fail)
        mem_cpu_fail = np.random.uniform(40, 75, num_cpu_fail)
        temp_cpu_fail = np.random.uniform(82, 105, num_cpu_fail) # Very hot
        disk_cpu_fail = np.random.uniform(70, 100, num_cpu_fail)
        net_cpu_fail = np.random.uniform(10, 150, num_cpu_fail)
        
        df_cpu = pd.DataFrame({
            'cpu_usage': cpu_fail,
            'memory_usage': mem_cpu_fail,
            'temperature': temp_cpu_fail,
            'disk_health': disk_cpu_fail,
            'network_traffic': net_cpu_fail,
            'label': 1,
            'failure_type': 'CPU Overheat'
        })
        
        # 3. Generate Memory Leak Logs (approx 8%)
        num_mem_fail = int(num_samples * 0.08)
        cpu_mem_fail = np.random.uniform(40, 85, num_mem_fail)
        mem_mem_fail = np.random.uniform(90, 100, num_mem_fail) # Leaked memory
        temp_mem_fail = np.random.uniform(50, 78, num_mem_fail)
        disk_mem_fail = np.random.uniform(70, 100, num_mem_fail)
        net_mem_fail = np.random.uniform(10, 150, num_mem_fail)
        
        df_mem = pd.DataFrame({
            'cpu_usage': cpu_mem_fail,
            'memory_usage': mem_mem_fail,
            'temperature': temp_mem_fail,
            'disk_health': disk_mem_fail,
            'network_traffic': net_mem_fail,
            'label': 1,
            'failure_type': 'Memory Leak'
        })
        
        # 4. Generate Disk Failure Logs (approx 7%)
        num_disk_fail = int(num_samples * 0.07)
        cpu_disk_fail = np.random.uniform(15, 60, num_disk_fail)
        mem_disk_fail = np.random.uniform(25, 65, num_disk_fail)
        temp_disk_fail = np.random.uniform(35, 65, num_disk_fail)
        disk_disk_fail = np.random.uniform(5, 30, num_disk_fail) # Degraded health
        net_disk_fail = np.random.uniform(2, 90, num_disk_fail)
        
        df_disk = pd.DataFrame({
            'cpu_usage': cpu_disk_fail,
            'memory_usage': mem_disk_fail,
            'temperature': temp_disk_fail,
            'disk_health': disk_disk_fail,
            'network_traffic': net_disk_fail,
            'label': 1,
            'failure_type': 'Disk Failure'
        })
        
        # 5. Generate Network Saturation / DDOS Logs (approx 7%)
        num_net_fail = int(num_samples * 0.07)
        cpu_net_fail = np.random.uniform(75, 98, num_net_fail) # High CPU handling packets
        mem_net_fail = np.random.uniform(40, 70, num_net_fail)
        temp_net_fail = np.random.uniform(60, 80, num_net_fail)
        disk_net_fail = np.random.uniform(70, 100, num_net_fail)
        net_net_fail = np.random.uniform(750, 1050, num_net_fail) # High Traffic
        
        df_net = pd.DataFrame({
            'cpu_usage': cpu_net_fail,
            'memory_usage': mem_net_fail,
            'temperature': temp_net_fail,
            'disk_health': disk_net_fail,
            'network_traffic': net_net_fail,
            'label': 1,
            'failure_type': 'Network Saturation'
        })
        
        # Combine all parts and shuffle
        df = pd.concat([df_normal, df_cpu, df_mem, df_disk, df_net], ignore_index=True)
        df = df.sample(frac=1.0, random_state=random_seed).reset_index(drop=True)
        return df

    def train_models(self, df):
        """
        Trains all 4 machine learning models, scales features, evaluates performance,
        saves the models to disk, and returns a dictionary of stats.
        """
        X = df[['cpu_usage', 'memory_usage', 'temperature', 'disk_health', 'network_traffic']]
        y = df['label']
        
        # Fit scaler
        X_scaled = self.scaler.fit_transform(X)
        
        # Save scaler
        joblib.dump(self.scaler, os.path.join(MODEL_DIR, 'scaler.joblib'))
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.25, random_state=42)
        
        performance_stats = {}
        
        for name, model in self.models.items():
            start_time = time.time()
            model.fit(X_train, y_train)
            train_duration = time.time() - start_time
            
            # Predict
            y_pred = model.predict(X_test)
            
            # Calculate metrics
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, zero_division=0)
            recall = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)
            
            # Store in performance dictionary
            performance_stats[name] = {
                'accuracy': float(accuracy),
                'precision': float(precision),
                'recall': float(recall),
                'f1_score': float(f1),
                'training_time': float(train_duration),
                'dataset_size': int(len(X))
            }
            
            # Save the trained model
            safe_name = name.lower().replace(' ', '_')
            joblib.dump(model, os.path.join(MODEL_DIR, f'{safe_name}_model.joblib'))
            
        self.is_trained = True
        return performance_stats

    def load_models(self):
        """
        Loads all models and scaler from disk.
        """
        try:
            scaler_path = os.path.join(MODEL_DIR, 'scaler.joblib')
            if not os.path.exists(scaler_path):
                return False
                
            self.scaler = joblib.load(scaler_path)
            
            for name in self.models.keys():
                safe_name = name.lower().replace(' ', '_')
                model_path = os.path.join(MODEL_DIR, f'{safe_name}_model.joblib')
                if os.path.exists(model_path):
                    self.models[name] = joblib.load(model_path)
                else:
                    return False
            
            self.is_trained = True
            return True
        except Exception as e:
            print(f"Error loading models: {e}")
            return False

    def predict(self, model_name, cpu_usage, memory_usage, temperature, disk_health, network_traffic):
        """
        Predicts whether the server will fail and returns the probability of failure.
        """
        if not self.is_trained:
            success = self.load_models()
            if not success:
                raise ValueError("Models are not trained or loaded. Please train first.")
                
        # Format metric inputs
        features = np.array([[cpu_usage, memory_usage, temperature, disk_health, network_traffic]])
        
        # Scale features
        features_scaled = self.scaler.transform(features)
        
        # Get model
        model = self.models.get(model_name)
        if model is None:
            raise ValueError(f"Model '{model_name}' not found.")
            
        # Predict class and probability
        prediction = int(model.predict(features_scaled)[0])
        
        # SVC probability and others
        probability = float(model.predict_proba(features_scaled)[0][1])
        
        return prediction, probability
        
    def get_fault_type(self, cpu_usage, memory_usage, temperature, disk_health, network_traffic):
        """
        Analyzes metric thresholds to diagnose the specific type of threat/anomaly.
        This provides descriptive context to the system alerts.
        """
        if temperature > 80:
            return "CPU Overheat"
        elif memory_usage > 90:
            return "Memory Leak"
        elif disk_health < 30:
            return "Disk Failure"
        elif network_traffic > 500:
            return "Network Saturation"
        elif cpu_usage > 85:
            return "High Resource Load"
        else:
            return "Unknown Anomaly"
