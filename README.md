# 🛡️ SentryML — Predictive Server Failure Detection Using Machine Learning

A real-time server monitoring dashboard that uses machine learning to **predict hardware failures before they happen**. Built with Flask, SQLAlchemy, and scikit-learn.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0+-green?logo=flask)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.3+-orange?logo=scikit-learn)

## 🏗️ Project Structure

```
server/
├── frontend/                    # Client-facing assets
│   ├── templates/               # Jinja2 HTML templates
│   │   ├── base.html            # Base layout with sidebar & nav
│   │   ├── index.html           # Live Health Dashboard
│   │   ├── ml_studio.html       # ML Model Management
│   │   ├── alerts.html          # Alert & Incident Log
│   │   └── db_config.html       # Database Configuration
│   └── static/
│       ├── css/style.css        # Full application styling
│       └── js/
│           ├── dashboard.js     # Dashboard live charts & polling
│           └── ml_studio.js     # ML studio interactions
│
├── backend/                     # Flask application & ML logic
│   ├── app.py                   # Flask routes, API endpoints, simulation worker
│   ├── config.py                # Configuration (DB URI, thresholds)
│   ├── ml_pipeline.py           # ML training, prediction, model management
│   └── saved_models/            # Trained .joblib model files (auto-generated)
│
├── database/                    # Database layer
│   ├── models.py                # SQLAlchemy ORM models
│   ├── db_setup.py              # MySQL setup utility
│   ├── generate_data.py         # Synthetic data generation & DB seeding
│   └── project.db               # SQLite database (auto-generated)
│
├── .env.example                 # Environment variable template
├── requirements.txt             # Python dependencies
├── run.py                       # 🚀 Main entry point
├── START_HERE.bat               # One-click Windows launcher
└── .gitignore
```

## ✨ Features

- **Live Dashboard** — Real-time CPU, memory, temperature, disk health, and network metrics with animated charts
- **ML-Powered Predictions** — 4 trained models (Random Forest, SVM, Neural Network, Logistic Regression) predict failures before they occur
- **Fault Injection** — Simulate CPU Overheat, Memory Leak, Disk Failure, and Network Saturation scenarios
- **Alert System** — Automated critical alerts with audible alarm and resolution tracking
- **Model Management** — Retrain, compare, and hot-swap ML models from the ML Studio page
- **Database Flexibility** — SQLite (default) with optional MySQL support, configurable from the UI
- **Virus Simulation** — Trigger and remediate simulated malicious activity with the AntiGravity system

## 🚀 Quick Start

### Prerequisites
- Python 3.10+

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/venkataajay8096-afk/predictive-server-failure-using-ml.git
cd predictive-server-failure-using-ml

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate it
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the server
python run.py
```

Then open **http://localhost:5000** in your browser.

### Windows One-Click
Double-click `START_HERE.bat` to launch everything automatically.

## 🔧 Configuration

Copy `.env.example` to `.env` and edit as needed:

```env
SECRET_KEY=your-secret-key

# Optional: MySQL (uncomment to use instead of SQLite)
# MYSQL_USER=root
# MYSQL_PASSWORD=your_password
# MYSQL_HOST=localhost
# MYSQL_PORT=3306
# MYSQL_DB=sentryml_db
```

## 🧠 ML Models

| Model | Description |
|---|---|
| Random Forest | Ensemble of decision trees (default active model) |
| Support Vector Machine | Hyperplane-based classification with probability |
| Neural Network | Multi-layer perceptron (32→16 hidden layers) |
| Logistic Regression | Linear probability model (baseline) |

All models are trained on synthetic server telemetry data and can be retrained from the ML Studio page.

## 📄 License

This project is for educational purposes.
