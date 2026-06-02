// EIHM Machine Learning Studio Controller
let accuracyChart = null;
let speedChart = null;
let modelsList = [];

// Model Corporate Re-Branding Map
const CORP_MODEL_NAMES = {
    'Random Forest': 'Standard Multi-Decision Tree Array',
    'Neural Network': 'Deep Learning Inference Engine',
    'Support Vector Machine': 'High-Dimensional Classifier Engine',
    'Logistic Regression': 'Linear Logistic Regressor Engine'
};

function getCorpModelName(name) {
    return CORP_MODEL_NAMES[name] || name;
}

document.addEventListener('DOMContentLoaded', () => {
    // Load models statistics and initialize graphs
    loadModelsData();
});

function loadModelsData(updateChartsOnly = false) {
    fetch('/api/models')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                modelsList = data.models;
                
                // Render Model Cards
                renderModelCards(modelsList, data.active_model);
                
                // Update/Initialize Charts
                renderStudioCharts(modelsList);
            }
        })
        .catch(err => console.error("Error loading model data:", err));
}

function renderModelCards(models, activeModelName) {
    const container = document.getElementById('ml-models-list');
    
    if (models.length === 0) {
        container.innerHTML = `<p class="no-alerts-msg">No models trained yet. Please trigger retraining below.</p>`;
        return;
    }
    
    container.innerHTML = models.map(model => {
        const isActive = model.model_name === activeModelName;
        const cardClass = isActive ? 'model-card-item active' : 'model-card-item';
        const date = new Date(model.timestamp).toLocaleString();
        
        let iconHtml = '';
        let colorClass = '';
        if (model.model_name === 'Random Forest') {
            iconHtml = '<i class="fa-solid fa-tree"></i>';
            colorClass = 'text-neon-blue';
        } else if (model.model_name === 'Support Vector Machine') {
            iconHtml = '<i class="fa-solid fa-arrows-split-up-and-left"></i>';
            colorClass = 'text-neon-teal';
        } else if (model.model_name === 'Neural Network') {
            iconHtml = '<i class="fa-solid fa-brain"></i>';
            colorClass = 'text-neon-purple';
        } else if (model.model_name === 'Logistic Regression') {
            iconHtml = '<i class="fa-solid fa-bezier-curve"></i>';
            colorClass = 'text-neon-yellow';
        }
        
        const actionButton = isActive 
            ? `<span class="active-status-badge"><i class="fa-solid fa-circle-check"></i> Active</span>`
            : `<button class="btn-secondary" onclick="activateModel('${model.model_name}')"><i class="fa-solid fa-bolt"></i> Activate Model</button>`;

        return `
            <div class="${cardClass}">
                <div class="model-card-header">
                    <div class="model-card-title ${colorClass}">
                        ${iconHtml}
                        <h3>${getCorpModelName(model.model_name)}</h3>
                    </div>
                    ${actionButton}
                </div>
                
                <div class="model-stats-grid">
                    <div class="model-stat-box">
                        <span class="model-stat-label">Accuracy</span>
                        <span class="model-stat-val text-neon-cyan">${(model.accuracy * 100).toFixed(1)}%</span>
                    </div>
                    <div class="model-stat-box">
                        <span class="model-stat-label">Precision</span>
                        <span class="model-stat-val text-neon-purple">${(model.precision * 100).toFixed(1)}%</span>
                    </div>
                    <div class="model-stat-box">
                        <span class="model-stat-label">Recall</span>
                        <span class="model-stat-val text-neon-teal">${(model.recall * 100).toFixed(1)}%</span>
                    </div>
                    <div class="model-stat-box">
                        <span class="model-stat-label">F1 Score</span>
                        <span class="model-stat-val text-neon-pink">${(model.f1_score * 100).toFixed(1)}%</span>
                    </div>
                </div>
                
                <div class="model-card-footer">
                    <div class="model-meta-info">
                        <span><i class="fa-regular fa-calendar-check"></i> Trained: ${date}</span>
                        <span><i class="fa-solid fa-database"></i> Size: ${model.dataset_size} samples</span>
                    </div>
                    <div class="model-meta-info">
                        <span><i class="fa-regular fa-clock"></i> Speed: ${(model.training_time * 1000).toFixed(0)} ms</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function renderStudioCharts(models) {
    const accuracyCtx = document.getElementById('modelAccuracyChart').getContext('2d');
    const speedCtx = document.getElementById('modelSpeedChart').getContext('2d');
    
    const names = models.map(m => getCorpModelName(m.model_name));
    const accuracies = models.map(m => m.accuracy * 100);
    const speeds = models.map(m => m.training_time * 1000); // in milliseconds
    
    const chartColors = [
        'rgba(20, 128, 240, 0.75)',  // Blue - RF
        'rgba(0, 230, 184, 0.75)',   // Teal - SVM
        'rgba(163, 82, 252, 0.75)',  // Purple - NN
        'rgba(255, 191, 0, 0.75)'    // Yellow - LR
    ];
    
    const chartBorders = [
        'rgb(20, 128, 240)',
        'rgb(0, 230, 184)',
        'rgb(163, 82, 252)',
        'rgb(255, 191, 0)'
    ];

    // 1. Accuracy Comparative Bar Chart
    if (accuracyChart) {
        accuracyChart.data.labels = names;
        accuracyChart.data.datasets[0].data = accuracies;
        accuracyChart.update();
    } else {
        accuracyChart = new Chart(accuracyCtx, {
            type: 'bar',
            data: {
                labels: names,
                datasets: [{
                    data: accuracies,
                    backgroundColor: chartColors,
                    borderColor: chartBorders,
                    borderWidth: 1,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: '#9aa4bf', font: { family: 'Inter', size: 11, weight: '500' } } },
                    y: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#9aa4bf', font: { family: 'monospace', size: 10 } }, min: 80, max: 100 }
                }
            }
        });
    }

    // 2. Training speed comparative chart
    if (speedChart) {
        speedChart.data.labels = names;
        speedChart.data.datasets[0].data = speeds;
        speedChart.update();
    } else {
        speedChart = new Chart(speedCtx, {
            type: 'bar',
            data: {
                labels: names,
                datasets: [{
                    data: speeds,
                    backgroundColor: chartColors,
                    borderColor: chartBorders,
                    borderWidth: 1,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: '#9aa4bf', font: { family: 'Inter', size: 11, weight: '500' } } },
                    y: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#9aa4bf', font: { family: 'monospace', size: 10 } } }
                }
            }
        });
    }
}

function activateModel(modelName) {
    console.log(`Activating model: ${modelName}`);
    
    fetch('/api/models/activate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ model_name: modelName })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            loadModelsData();
            
            // Sync with global widgets if on-screen
            const widgetModel = document.getElementById('widget-active-model');
            if (widgetModel) widgetModel.textContent = modelName;
        } else {
            alert("Error activating model: " + data.error);
        }
    })
    .catch(err => console.error("Error activating model:", err));
}

function triggerRetrain() {
    const sizeInput = document.getElementById('dataset-size');
    const size = parseInt(sizeInput.value) || 2000;
    
    if (size < 500 || size > 10000) {
        alert("Dataset size must be between 500 and 10,000 samples.");
        return;
    }
    
    const retrainBtn = document.getElementById('btn-retrain');
    const loader = document.getElementById('training-progress');
    const statusText = document.getElementById('training-status-step');
    
    // UI Loading state
    retrainBtn.disabled = true;
    loader.style.display = 'flex';
    
    // Simulate steps text in Javascript for visual engagement while request is executing
    const steps = [
        "Re-generating synthetic load distributions...",
        "Executing feature extraction & normalization scaler...",
        "Fitting Random Forest Classifier trees (100 estimators)...",
        "Drawing Support Vector boundaries (Radial Basis Kernel)...",
        "Backpropagating MLP Neural Network matrices (32x16 layers)...",
        "Optimizing Logistic Regression thresholds...",
        "Serializing pipelines to disk and updating performance history..."
    ];
    
    let currentStep = 0;
    statusText.textContent = steps[0];
    const stepInterval = setInterval(() => {
        if (currentStep < steps.length - 1) {
            currentStep++;
            statusText.textContent = steps[currentStep];
        }
    }, 1500);
    
    // Fire actual retraining API call
    fetch('/api/models/train', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ dataset_size: size })
    })
    .then(res => res.json())
    .then(data => {
        clearInterval(stepInterval);
        loader.style.display = 'none';
        retrainBtn.disabled = false;
        
        if (data.success) {
            modelsList = data.models;
            renderModelCards(modelsList, data.active_model);
            renderStudioCharts(modelsList);
        } else {
            alert("Retraining failed: " + data.error);
        }
    })
    .catch(err => {
        clearInterval(stepInterval);
        loader.style.display = 'none';
        retrainBtn.disabled = false;
        console.error("Error during retraining:", err);
        alert("Error connection failed during retraining.");
    });
}
