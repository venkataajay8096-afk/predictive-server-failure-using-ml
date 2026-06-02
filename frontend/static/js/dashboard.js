// EIHM Live Dashboard Interface
let liveChart = null;
let radarChart = null;
let historicalData = [];
const POLL_INTERVAL = 3000; // 3 seconds matching configuration

// Model Corporate Re-Branding Map
const CORP_MODEL_NAMES = {
    'Random Forest': 'Random Forest',
    'Neural Network': 'Neural Network',
    'Support Vector Machine': 'Support Vector Machine',
    'Logistic Regression': 'Logistic Regression'
};

function getCorpModelName(name) {
    return CORP_MODEL_NAMES[name] || name;
}

// Theme Colors
const colors = {
    blue: 'rgb(2, 130, 199)',
    purple: 'rgb(124, 58, 237)',
    pink: 'rgb(239, 68, 68)',
    teal: 'rgb(13, 148, 136)',
    yellow: 'rgb(234, 88, 12)',
    grid: 'rgba(15, 23, 42, 0.04)',
    text: '#475569'
};

// Background transition based on risk level
function applyRiskBackground(prob) {
    const body = document.body;
    // Remove all previous risk classes
    body.classList.remove('bg-risk-critical', 'bg-risk-warning', 'bg-risk-normal');

    if (prob >= 0.80) {
        // Critical — warm red tint
        body.classList.add('bg-risk-critical');
    } else if (prob >= 0.50) {
        // Warning — amber tint
        body.classList.add('bg-risk-warning');
    } else {
        // Normal — light blue
        body.classList.add('bg-risk-normal');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // 1. Fetch initial live metrics to seed charts
    fetchInitialMetrics();
    
    // 2. Set up polling interval
    setInterval(pollLatestMetric, POLL_INTERVAL);
});

function fetchInitialMetrics() {
    fetch('/api/metrics/live')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                historicalData = data.metrics;
                
                // Initialize Charts
                initTimelineChart(historicalData);
                initRadarChart(historicalData[historicalData.length - 1]);
                
                // Update UI Elements
                if (historicalData.length > 0) {
                    updateDashboardUI(historicalData[historicalData.length - 1]);
                }
                
                // Highlight active fault button
                setActiveFaultButton(data.current_mode);
                
                // Update active model name (translated)
                document.getElementById('ai-active-model-name').textContent = getCorpModelName(data.active_model);
            }
        })
        .catch(err => console.error("Error loading metrics:", err));
}

function pollLatestMetric() {
    fetch('/api/metrics/latest')
        .then(res => res.json())
        .then(data => {
            if (data.success && data.metric) {
                const metric = data.metric;
                
                // Update active model widget and fault button if altered (translated)
                document.getElementById('widget-active-model').textContent = getCorpModelName(data.active_model);
                document.getElementById('ai-active-model-name').textContent = getCorpModelName(data.active_model);
                document.getElementById('widget-current-mode').textContent = data.current_mode;
                setActiveFaultButton(data.current_mode);
                
                // Update UI numeric cards & gauge
                updateDashboardUI(metric);
                
                // 1. Update Timeline Chart
                if (liveChart) {
                    const labelTime = new Date(metric.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                    
                    // Add new data
                    liveChart.data.labels.push(labelTime);
                    liveChart.data.datasets[0].data.push(metric.cpu_usage);
                    liveChart.data.datasets[1].data.push(metric.memory_usage);
                    liveChart.data.datasets[2].data.push(metric.temperature);
                    liveChart.data.datasets[3].data.push(metric.network_traffic / 10.0); // Scale network to fit 0-100% chart nicely
                    
                    // Remove oldest if limit reached
                    if (liveChart.data.labels.length > 40) {
                        liveChart.data.labels.shift();
                        liveChart.data.datasets[0].data.shift();
                        liveChart.data.datasets[1].data.shift();
                        liveChart.data.datasets[2].data.shift();
                        liveChart.data.datasets[3].data.shift();
                    }
                    
                    liveChart.update('none'); // Update without full animation for smooth scrolling
                }
                
                // 2. Update Radar Chart
                if (radarChart) {
                    radarChart.data.datasets[0].data = [
                        metric.cpu_usage,
                        metric.memory_usage,
                        metric.temperature,
                        100.0 - metric.disk_health, // disk degradation
                        Math.min(100, metric.network_traffic / 10.0) // network stress relative load
                    ];
                    radarChart.update();
                }
            }
        })
        .catch(err => console.error("Error polling metric:", err));
}

function initTimelineChart(dataList) {
    const ctx = document.getElementById('liveTimelineChart').getContext('2d');
    
    const labels = dataList.map(d => new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    const cpuData = dataList.map(d => d.cpu_usage);
    const memData = dataList.map(d => d.memory_usage);
    const tempData = dataList.map(d => d.temperature);
    const netScaledData = dataList.map(d => d.network_traffic / 10.0);
    
    liveChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'CPU Usage (%)',
                    data: cpuData,
                    borderColor: colors.blue,
                    backgroundColor: 'rgba(20, 128, 240, 0.03)',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.35,
                    fill: true
                },
                {
                    label: 'Memory Usage (%)',
                    data: memData,
                    borderColor: colors.purple,
                    backgroundColor: 'rgba(163, 82, 252, 0.03)',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.35,
                    fill: true
                },
                {
                    label: 'Temperature (°C)',
                    data: tempData,
                    borderColor: colors.pink,
                    backgroundColor: 'rgba(255, 26, 102, 0.03)',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.35,
                    fill: true
                },
                {
                    label: 'Network Load (Scaled)',
                    data: netScaledData,
                    borderColor: colors.yellow,
                    backgroundColor: 'rgba(255, 191, 0, 0.03)',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.35,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: colors.text,
                        font: { family: 'Inter', size: 11, weight: '500' },
                        boxWidth: 12,
                        padding: 15
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(9, 9, 14, 0.95)',
                    titleColor: '#fff',
                    bodyColor: varColor => varColor.dataset.borderColor,
                    borderColor: 'rgba(255, 255, 255, 0.08)',
                    borderWidth: 1,
                    padding: 12
                }
            },
            scales: {
                x: {
                    grid: { color: colors.grid },
                    ticks: { color: colors.text, font: { family: 'monospace', size: 10 } }
                },
                y: {
                    min: 0,
                    max: 110,
                    grid: { color: colors.grid },
                    ticks: { color: colors.text, font: { family: 'monospace', size: 10 } }
                }
            }
        }
    });
}

function initRadarChart(latestMetric) {
    const ctx = document.getElementById('diagnosticsRadarChart').getContext('2d');
    
    const cpu = latestMetric ? latestMetric.cpu_usage : 30;
    const mem = latestMetric ? latestMetric.memory_usage : 45;
    const temp = latestMetric ? latestMetric.temperature : 40;
    const diskDeg = latestMetric ? (100 - latestMetric.disk_health) : 5;
    const netStress = latestMetric ? Math.min(100, latestMetric.network_traffic / 10.0) : 10;
    
    radarChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['CPU stress', 'RAM stress', 'Thermal core', 'Disk degradation', 'Bandwidth saturation'],
            datasets: [{
                label: 'Stress Index',
                data: [cpu, mem, temp, diskDeg, netStress],
                backgroundColor: 'rgba(0, 230, 184, 0.15)',
                borderColor: colors.teal,
                borderWidth: 2,
                pointBackgroundColor: colors.teal,
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: colors.teal,
                pointRadius: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                r: {
                    angleLines: { color: colors.grid },
                    grid: { color: colors.grid },
                    pointLabels: {
                        color: colors.text,
                        font: { family: 'Inter', size: 9, weight: '600' }
                    },
                    ticks: { display: false },
                    min: 0,
                    max: 100
                }
            }
        }
    });
}

function updateDashboardUI(metric) {
    // 1. Numeric Values
    document.getElementById('val-cpu').textContent = metric.cpu_usage.toFixed(1) + '%';
    document.getElementById('val-mem').textContent = metric.memory_usage.toFixed(1) + '%';
    document.getElementById('val-temp').textContent = metric.temperature.toFixed(1) + '°C';
    document.getElementById('val-disk').textContent = metric.disk_health.toFixed(1) + '%';
    document.getElementById('val-net').textContent = metric.network_traffic.toFixed(1) + ' Mbps';

    // 2. Progress Bar Gauges
    document.getElementById('bar-cpu').style.width = metric.cpu_usage + '%';
    document.getElementById('bar-mem').style.width = metric.memory_usage + '%';
    document.getElementById('bar-temp').style.width = Math.min(100, metric.temperature) + '%';
    document.getElementById('bar-disk').style.width = metric.disk_health + '%';
    document.getElementById('bar-net').style.width = Math.min(100, (metric.network_traffic / 1000.0) * 100) + '%';

    // 3. AI Diagnostics Panel Ring & Stats
    const prob = metric.failure_probability;
    const probPercent = (prob * 100).toFixed(0);
    document.getElementById('risk-percentage').textContent = probPercent + '%';
    
    // Stroke dashoffset for SVG circular ring (radius=85, perimeter = 2 * PI * r = 534)
    const strokeOffset = 534 * (1 - prob);
    document.getElementById('gauge-fill-ring').style.strokeDashoffset = strokeOffset;
    
    // Diagnostic Details
    const diagnosticPanel = document.getElementById('ai-prediction-panel');
    const riskStatusEl = document.getElementById('risk-status');
    const threatClassEl = document.getElementById('ai-threat-class');
    const confidenceEl = document.getElementById('ai-confidence');
    
    // Adjust colors, alerts, and glow statuses
    if (prob >= 0.80) {
        // Critical Anomaly
        riskStatusEl.textContent = 'CRITICAL';
        riskStatusEl.className = 'gauge-status-text text-neon-pink';
        document.getElementById('gauge-fill-ring').style.stroke = colors.pink;
        
        diagnosticPanel.className = 'dashboard-panel ai-panel card-glow-danger';
        threatClassEl.textContent = metric.failure_type;
        threatClassEl.className = 'text-neon-pink';
        
        // Confidence calculation (higher risk -> higher confidence from the model)
        const confidenceVal = Math.max(88, 100 - (prob * 2)).toFixed(1);
        confidenceEl.textContent = confidenceVal + '%';
    } else if (prob >= 0.50) {
        // Warning State
        riskStatusEl.textContent = 'WARNING';
        riskStatusEl.className = 'gauge-status-text text-neon-yellow';
        document.getElementById('gauge-fill-ring').style.stroke = colors.yellow;
        
        diagnosticPanel.className = 'dashboard-panel ai-panel card-glow-warning';
        threatClassEl.textContent = 'Anomalous load';
        threatClassEl.className = 'text-neon-yellow';
        
        const confidenceVal = Math.max(75, 100 - (prob * 8)).toFixed(1);
        confidenceEl.textContent = confidenceVal + '%';
    } else {
        // Healthy State
        riskStatusEl.textContent = 'SECURE';
        riskStatusEl.className = 'gauge-status-text text-neon-cyan';
        document.getElementById('gauge-fill-ring').style.stroke = colors.teal;
        
        diagnosticPanel.className = 'dashboard-panel ai-panel card-glow-normal';
        threatClassEl.textContent = 'Normal Workload';
        threatClassEl.className = 'text-neon-cyan';
        
        const confidenceVal = Math.min(99.9, 95 + (1 - prob) * 4.9).toFixed(1);
        confidenceEl.textContent = confidenceVal + '%';
    }

    // Apply dynamic page background based on risk level
    applyRiskBackground(prob);
}

function injectFault(mode) {
    console.log(`Injecting fault workload: ${mode}`);
    
    fetch('/api/simulation/state', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ mode: mode })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            setActiveFaultButton(mode);
            document.getElementById('widget-current-mode').textContent = mode;
            
            // Instantly poll after fault injection to show immediate reaction on UI
            setTimeout(pollLatestMetric, 200);
        }
    })
    .catch(err => console.error("Error setting fault mode:", err));
}

function setActiveFaultButton(mode) {
    // Remove active class from all buttons
    const buttons = document.querySelectorAll('.btn-fault');
    buttons.forEach(btn => btn.classList.remove('active'));
    
    // We must map spaces/normal to IDs correctly
    // IDs: btn-fault-Normal, btn-fault-CPU-Overheat, btn-fault-Memory-Leak, btn-fault-Disk-Failure, btn-fault-Network-Saturation
    const formattedId = 'btn-fault-' + mode.replace(/ /g, '-');
    const activeBtn = document.getElementById(formattedId);
    if (activeBtn) {
        activeBtn.classList.add('active');
    }
}
