/**
 * FermentIQ Real-Time Dashboard with WebSocket
 * Receives live batch data via WebSocket and updates charts in real-time
 */

// Configuration
const CONFIG = {
    WS_URL: 'ws://localhost:8000/ws',
    API_URL: 'http://localhost:8000',
    RECONNECT_DELAY: 3000,
    MAX_DATA_POINTS: 50,
    CHART_UPDATE_ANIMATION: 250
};

// WebSocket connection
let ws = null;
let reconnectTimeout = null;

// Chart instances
const charts = {
    1: { ph: null, temperature: null, co2: null },
    2: { ph: null, temperature: null, co2: null },
    3: { ph: null, temperature: null, co2: null },
    4: { ph: null, temperature: null, co2: null }
};

// Data storage for each batch
const batchData = {
    1: { timestamps: [], ph: [], temperature: [], co2: [], idealPh: [], idealTemp: [], idealCo2: [] },
    2: { timestamps: [], ph: [], temperature: [], co2: [], idealPh: [], idealTemp: [], idealCo2: [] },
    3: { timestamps: [], ph: [], temperature: [], co2: [], idealPh: [], idealTemp: [], idealCo2: [] },
    4: { timestamps: [], ph: [], temperature: [], co2: [], idealPh: [], idealTemp: [], idealCo2: [] }
};

// Track previous state for each batch to detect changes
const batchStates = {
    1: { currentStatus: null, logs: [], aiSuggestions: [] },
    2: { currentStatus: null, logs: [], aiSuggestions: [] },
    3: { currentStatus: null, logs: [], aiSuggestions: [] },
    4: { currentStatus: null, logs: [], aiSuggestions: [] }
};

// Tank status counts
const tankStatusCounts = {
    perfect: 0,
    acceptable: 0,
    concerning: 0,
    failed: 0
};

// Batch status colors
const STATUS_COLORS = {
    acceptable: { primary: '#10b981', bg: 'rgba(16, 185, 129, 0.1)', border: '#10b981' },
    perfect: { primary: '#3b82f6', bg: 'rgba(59, 130, 246, 0.1)', border: '#3b82f6' },
    failed: { primary: '#ef4444', bg: 'rgba(239, 68, 68, 0.1)', border: '#ef4444' },
    concerning: { primary: '#f59e0b', bg: 'rgba(245, 158, 11, 0.1)', border: '#f59e0b' }
};

// AI Suggestion templates based on status transitions
const AI_SUGGESTIONS = {
    'Perfect → Acceptable': {
        title: 'Minor Deviation Detected',
        suggestions: [
            'Quality score dropped below 95%. Monitor closely for the next 30 minutes.',
            'Consider checking sensor calibration to ensure accurate readings.',
            'Review recent environmental changes that may have affected the batch.'
        ],
        urgency: 'low'
    },
    'Acceptable → Concerning': {
        title: 'Corrective Action Recommended',
        suggestions: [
            'Quality score has dropped to concerning levels. Immediate attention required.',
            'Check temperature control systems for any malfunctions.',
            'Verify pH buffer solutions are within specification.',
            'Consider increasing monitoring frequency to every 15 minutes.'
        ],
        urgency: 'medium'
    },
    'Perfect → Concerning': {
        title: 'Significant Deviation Alert',
        suggestions: [
            'Rapid quality degradation detected. Investigate potential contamination.',
            'Review all parameter changes in the last hour.',
            'Check for equipment failures or power fluctuations.',
            'Consider isolating this batch for detailed analysis.'
        ],
        urgency: 'medium'
    },
    'Concerning → Failed': {
        title: 'Critical Intervention Required',
        suggestions: [
            'Batch has failed quality thresholds. Immediate intervention needed.',
            'Document all current readings for quality assurance report.',
            'Consider salvage options based on current fermentation stage.',
            'Alert quality control team for batch assessment.',
            'Prepare backup batch if production timeline is critical.'
        ],
        urgency: 'high'
    },
    'Acceptable → Failed': {
        title: 'Urgent: Rapid Quality Failure',
        suggestions: [
            'Unexpected rapid decline detected. Check for system failures.',
            'Review all automated control systems.',
            'Document failure mode for root cause analysis.',
            'Initiate emergency quality protocols.'
        ],
        urgency: 'high'
    },
    'Perfect → Failed': {
        title: 'Critical: Severe Quality Failure',
        suggestions: [
            'Catastrophic quality failure from optimal state. Emergency response required.',
            'Immediately check all monitoring equipment for malfunctions.',
            'Isolate batch and begin contamination investigation.',
            'Alert management and quality assurance teams.',
            'Review batch logs from the last 2 hours for anomalies.'
        ],
        urgency: 'high'
    },
    'Concerning → Acceptable': {
        title: 'Recovery in Progress',
        suggestions: [
            'Positive trend detected. Continue current recovery measures.',
            'Maintain elevated monitoring until stable for 1 hour.',
            'Document successful corrective actions for future reference.'
        ],
        urgency: 'low'
    },
    'Failed → Concerning': {
        title: 'Partial Recovery Observed',
        suggestions: [
            'Some improvement detected but still below acceptable thresholds.',
            'Continue intervention measures.',
            'Assess whether full recovery is achievable within timeline.'
        ],
        urgency: 'medium'
    }
};

/**
 * Initialize WebSocket connection
 */
function initWebSocket() {
    updateConnectionStatus('connecting');

    ws = new WebSocket(CONFIG.WS_URL);

    ws.onopen = () => {
        console.log('[WebSocket] Connected to server');
        updateConnectionStatus('connected');
        clearTimeout(reconnectTimeout);
    };

    ws.onclose = () => {
        console.log('[WebSocket] Disconnected');
        updateConnectionStatus('disconnected');
        scheduleReconnect();
    };

    ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
        updateConnectionStatus('error');
    };

    ws.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);
            handleMessage(message);
        } catch (e) {
            console.error('[WebSocket] Error parsing message:', e);
        }
    };
}

/**
 * Schedule reconnection attempt
 */
function scheduleReconnect() {
    clearTimeout(reconnectTimeout);
    reconnectTimeout = setTimeout(() => {
        console.log('[WebSocket] Attempting to reconnect...');
        initWebSocket();
    }, CONFIG.RECONNECT_DELAY);
}

/**
 * Update connection status indicator
 */
function updateConnectionStatus(status) {
    const indicator = document.getElementById('connection-status');
    const text = document.getElementById('connection-text');

    if (!indicator || !text) return;

    const statuses = {
        connecting: { class: 'connecting', text: 'Connecting...' },
        connected: { class: 'connected', text: 'Live' },
        disconnected: { class: 'disconnected', text: 'Disconnected' },
        error: { class: 'error', text: 'Error' }
    };

    const statusInfo = statuses[status] || statuses.disconnected;
    indicator.className = `status-indicator ${statusInfo.class}`;
    text.textContent = statusInfo.text;
}

/**
 * Handle incoming WebSocket messages
 */
function handleMessage(message) {
    switch (message.type) {
        case 'initial_state':
            handleInitialState(message.data);
            break;
        case 'batch_update':
            handleBatchUpdate(message);
            break;
        case 'pong':
            // Heartbeat response
            break;
        default:
            console.log('[WebSocket] Unknown message type:', message.type);
    }
}

/**
 * Handle initial state message
 */
function handleInitialState(data) {
    console.log('[WebSocket] Received initial state');
    for (const batchNum in data) {
        if (data[batchNum]) {
            handleBatchUpdate({
                batch_number: parseInt(batchNum),
                data_point: data[batchNum].data_point,
                comparison: data[batchNum].comparison
            });
        }
    }
}

/**
 * Handle batch update message
 */
function handleBatchUpdate(message) {
    const { batch_number, data_point, comparison } = message;

    // Update batch header based on status
    updateBatchHeader(batch_number, data_point.batch_status, comparison.quality_score);

    // Store data point
    addDataPoint(batch_number, data_point, comparison);

    // Update charts
    updateCharts(batch_number);

    // Update metrics display
    updateMetrics(batch_number, comparison);
}

/**
 * Update batch header styling based on quality score
 * Quality Thresholds:
 * - 95%+ → Green (Perfect)
 * - 90-94.9% → Blue (Acceptable)
 * - 80-89.9% → Yellow (Concerning)
 * - <80% → Red (Failed)
 */
function updateBatchHeader(batchNum, status, qualityScore) {
    const header = document.getElementById(`batch${batchNum}-header`);
    const scoreEl = document.getElementById(`batch${batchNum}-score`);
    const statusTag = document.getElementById(`batch${batchNum}-status-tag`);

    let color, statusText, statusClass;

    // Determine color and status based on quality score
    if (qualityScore >= 95) {
        color = '#10b981';      // Green
        statusText = 'Perfect';
        statusClass = 'perfect';
    } else if (qualityScore >= 90) {
        color = '#3b82f6';      // Blue
        statusText = 'Acceptable';
        statusClass = 'acceptable';
    } else if (qualityScore >= 80) {
        color = '#f59e0b';      // Yellow
        statusText = 'Concerning';
        statusClass = 'concerning';
    } else {
        color = '#ef4444';      // Red
        statusText = 'Failed';
        statusClass = 'failed';
    }

    // Update header background and border
    if (header) {
        header.style.background = `linear-gradient(135deg, ${color}20, ${color}40)`;
        header.style.borderColor = color;
    }

    // Update quality score display
    if (scoreEl) {
        scoreEl.textContent = `Quality: ${qualityScore.toFixed(1)}%`;
    }

    // Update status tag
    if (statusTag) {
        statusTag.textContent = statusText;
        statusTag.className = `status-tag ${statusClass}`;
    }

    // Track state changes and log them
    const batchState = batchStates[batchNum];
    if (batchState.currentStatus !== statusText) {
        const oldStatus = batchState.currentStatus;
        batchState.currentStatus = statusText;

        // Get the current timestamp from the latest data point
        const data = batchData[batchNum];
        const timestamp = data.timestamps.length > 0
            ? data.timestamps[data.timestamps.length - 1]
            : '0.0h';

        logStateChange(batchNum, timestamp, oldStatus, statusText);

        // Generate AI suggestion on status change
        if (oldStatus !== null) {
            generateAISuggestion(batchNum, timestamp, oldStatus, statusText);
        }
    }

    // Update tank status summary
    updateTankStatusSummary();
}

/**
 * Update the tank status summary counters
 */
function updateTankStatusSummary() {
    // Reset counts
    tankStatusCounts.perfect = 0;
    tankStatusCounts.acceptable = 0;
    tankStatusCounts.concerning = 0;
    tankStatusCounts.failed = 0;

    // Count current statuses
    for (let batchNum = 1; batchNum <= 4; batchNum++) {
        const status = batchStates[batchNum].currentStatus;
        if (status) {
            const statusKey = status.toLowerCase();
            if (tankStatusCounts.hasOwnProperty(statusKey)) {
                tankStatusCounts[statusKey]++;
            }
        }
    }

    // Update DOM elements
    document.getElementById('count-perfect').textContent = tankStatusCounts.perfect;
    document.getElementById('count-acceptable').textContent = tankStatusCounts.acceptable;
    document.getElementById('count-concerning').textContent = tankStatusCounts.concerning;
    document.getElementById('count-failed').textContent = tankStatusCounts.failed;

    // Add visual feedback for cards with tanks
    ['perfect', 'acceptable', 'concerning', 'failed'].forEach(status => {
        const card = document.getElementById(`status-card-${status}`);
        if (card) {
            if (tankStatusCounts[status] > 0) {
                card.classList.add('has-tanks');
            } else {
                card.classList.remove('has-tanks');
            }
        }
    });
}

/**
 * Generate AI suggestion based on status transition
 */
function generateAISuggestion(batchNum, timestamp, oldStatus, newStatus) {
    const transitionKey = `${oldStatus} → ${newStatus}`;
    const suggestionTemplate = AI_SUGGESTIONS[transitionKey];

    if (!suggestionTemplate) {
        return; // No suggestion for this transition (e.g., improvement)
    }

    // Pick a random suggestion from the template
    const randomSuggestion = suggestionTemplate.suggestions[
        Math.floor(Math.random() * suggestionTemplate.suggestions.length)
    ];

    const suggestion = {
        timestamp: timestamp,
        transition: transitionKey,
        title: suggestionTemplate.title,
        text: randomSuggestion,
        urgency: suggestionTemplate.urgency,
        time: new Date().toISOString()
    };

    batchStates[batchNum].aiSuggestions.unshift(suggestion);

    // Keep only the last 10 suggestions
    if (batchStates[batchNum].aiSuggestions.length > 10) {
        batchStates[batchNum].aiSuggestions.pop();
    }

    updateAISuggestionsDisplay(batchNum);
}

/**
 * Update the AI suggestions display for a batch
 */
function updateAISuggestionsDisplay(batchNum) {
    const container = document.getElementById(`batch${batchNum}-ai-suggestions`);
    if (!container) return;

    const suggestions = batchStates[batchNum].aiSuggestions;

    if (suggestions.length === 0) {
        container.innerHTML = '<div class="ai-empty">No suggestions yet</div>';
        return;
    }

    container.innerHTML = suggestions.map(s => createAISuggestionCard(s)).join('');
}

/**
 * Create an AI suggestion card HTML
 */
function createAISuggestionCard(suggestion) {
    return `
        <div class="ai-suggestion-card ${suggestion.urgency}">
            <div class="ai-suggestion-header">
                <span class="ai-suggestion-transition">${suggestion.transition}</span>
                <span class="ai-suggestion-time">${suggestion.timestamp}</span>
            </div>
            <div class="ai-suggestion-title">${suggestion.title}</div>
            <div class="ai-suggestion-text">${suggestion.text}</div>
        </div>
    `;
}

/**
 * Add data point to batch storage
 */
function addDataPoint(batchNum, dataPoint, comparison) {
    const data = batchData[batchNum];

    // Add timestamp
    data.timestamps.push(dataPoint.timestamp.toFixed(1) + 'h');

    // Add actual values
    data.ph.push(dataPoint.ph);
    data.temperature.push(dataPoint.temperature);
    data.co2.push(dataPoint.co2);

    // Add ideal values
    data.idealPh.push(comparison.ideal.ph);
    data.idealTemp.push(comparison.ideal.temperature);
    data.idealCo2.push(comparison.ideal.co2);

    // Limit data points
    if (data.timestamps.length > CONFIG.MAX_DATA_POINTS) {
        data.timestamps.shift();
        data.ph.shift();
        data.temperature.shift();
        data.co2.shift();
        data.idealPh.shift();
        data.idealTemp.shift();
        data.idealCo2.shift();
    }
}

/**
 * Update charts with latest data
 */
function updateCharts(batchNum) {
    const data = batchData[batchNum];

    updateChart(charts[batchNum].ph, data.timestamps, data.ph, data.idealPh);
    updateChart(charts[batchNum].temperature, data.timestamps, data.temperature, data.idealTemp);
    updateChart(charts[batchNum].co2, data.timestamps, data.co2, data.idealCo2);
}

/**
 * Update a single chart
 */
function updateChart(chart, labels, actualData, idealData) {
    if (!chart) return;

    chart.data.labels = labels;
    chart.data.datasets[0].data = actualData;
    chart.data.datasets[1].data = idealData;
    chart.update('none');
}

/**
 * Update metrics display
 */
function updateMetrics(batchNum, comparison) {
    const metrics = [
        { id: `batch${batchNum}-ph`, actual: comparison.actual.ph, ideal: comparison.ideal.ph, unit: '', decimals: 2 },
        { id: `batch${batchNum}-temp`, actual: comparison.actual.temperature, ideal: comparison.ideal.temperature, unit: '°C', decimals: 1 },
        { id: `batch${batchNum}-co2`, actual: comparison.actual.co2, ideal: comparison.ideal.co2, unit: '%', decimals: 2 }
    ];

    metrics.forEach(metric => {
        const el = document.getElementById(metric.id);
        if (el) {
            const deviation = Math.abs(metric.actual - metric.ideal);
            const deviationClass = getDeviationClass(metric.id.includes('ph') ? 'ph' : (metric.id.includes('temp') ? 'temperature' : 'co2'), deviation);

            el.innerHTML = `
                <span class="actual ${deviationClass}">${metric.actual.toFixed(metric.decimals)}${metric.unit}</span>
                <span class="separator">vs</span>
                <span class="ideal">${metric.ideal.toFixed(metric.decimals)}${metric.unit}</span>
            `;
        }
    });

    // Update overall status
    const statusEl = document.getElementById(`batch${batchNum}-status`);
    if (statusEl) {
        const status = comparison.status.overall;
        statusEl.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        statusEl.className = `status-badge ${status}`;
    }
}

/**
 * Get deviation class for styling
 */
function getDeviationClass(type, deviation) {
    const thresholds = {
        ph: { warning: 0.3, critical: 0.5 },
        temperature: { warning: 2.0, critical: 3.5 },
        co2: { warning: 1.5, critical: 3.0 }
    };

    const t = thresholds[type];
    if (deviation >= t.critical) return 'critical';
    if (deviation >= t.warning) return 'warning';
    return 'normal';
}

/**
 * Initialize charts for all batches
 */
function initializeCharts() {
    for (let batchNum = 1; batchNum <= 4; batchNum++) {
        charts[batchNum].ph = createChart(`batch${batchNum}-ph-chart`, 'pH');
        charts[batchNum].temperature = createChart(`batch${batchNum}-temp-chart`, 'Temperature (°C)');
        charts[batchNum].co2 = createChart(`batch${batchNum}-co2-chart`, 'CO2 (%)');
    }
}

/**
 * Create a chart instance
 */
function createChart(canvasId, label) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    const ctx = canvas.getContext('2d');

    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: `Actual ${label}`,
                    data: [],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true,
                    pointRadius: 2
                },
                {
                    label: `Ideal ${label}`,
                    data: [],
                    borderColor: '#10b981',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    tension: 0.3,
                    fill: false,
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: CONFIG.CHART_UPDATE_ANIMATION
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    align: 'end',
                    labels: {
                        color: '#94a3b8',
                        usePointStyle: true,
                        pointStyle: 'line',
                        boxWidth: 40, // Wider line for visibility
                        font: { size: 11, family: "'Outfit', sans-serif" }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: {
                        color: '#94a3b8',
                        maxRotation: 0,
                        maxTicksLimit: 8
                    }
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#94a3b8' }
                }
            }
        }
    });
}

/**
 * Send ping to keep connection alive
 */
function sendPing() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('[FermentIQ] Initializing dashboard...');
    initializeCharts();
    initWebSocket();

    // Initialize tank status summary
    updateTankStatusSummary();

    // Send ping every 30 seconds to keep connection alive
    setInterval(sendPing, 30000);
});

/**
 * Log a state change for a batch
 */
function logStateChange(batchNum, timestamp, oldStatus, newStatus) {
    const logEntry = {
        timestamp: timestamp,
        oldStatus: oldStatus,
        newStatus: newStatus,
        time: new Date().toISOString()
    };

    batchStates[batchNum].logs.push(logEntry);
    updateLogDisplay(batchNum);
}

/**
 * Update the log display for a batch
 */
function updateLogDisplay(batchNum) {
    const logContainer = document.getElementById(`batch${batchNum}-log-entries`);
    if (!logContainer) return;

    const logs = batchStates[batchNum].logs;

    if (logs.length === 0) {
        logContainer.innerHTML = '<div class="log-empty">No events logged yet</div>';
        return;
    }

    // Display logs in reverse order (newest first)
    logContainer.innerHTML = logs
        .slice()
        .reverse()
        .map(log => createLogEntry(log))
        .join('');
}

/**
 * Create a log entry HTML element
 */
function createLogEntry(log) {
    const statusIcons = {
        'Perfect': '✓',
        'Acceptable': '◐',
        'Concerning': '⚠',
        'Failed': '✗'
    };

    const statusColors = {
        'Perfect': '#10b981',
        'Acceptable': '#3b82f6',
        'Concerning': '#f59e0b',
        'Failed': '#ef4444'
    };

    const icon = statusIcons[log.newStatus] || '•';
    const color = statusColors[log.newStatus] || '#94a3b8';

    let message;
    if (log.oldStatus === null) {
        message = `Batch started - ${log.newStatus}`;
    } else {
        message = `Quality changed from ${log.oldStatus} to ${log.newStatus}`;
    }

    return `
        <div class="log-entry">
            <span class="log-icon" style="color: ${color}">${icon}</span>
            <span class="log-timestamp">${log.timestamp}</span>
            <span class="log-message">${message}</span>
        </div>
    `;
}

/**
 * Download batch data as CSV file
 * Fetches from backend API and triggers browser download
 */
async function downloadBatchCSV(batchNum) {
    const button = event.target;
    const originalText = button.innerHTML;

    try {
        // Update button to show loading state
        button.innerHTML = '⏳ Loading...';
        button.disabled = true;

        // Fetch CSV from backend API
        const response = await fetch(`${CONFIG.API_URL}/api/batches/${batchNum}/download?format=csv`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        // Get the CSV content
        const csvContent = await response.text();

        // Create blob and download
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);

        // Create temporary link and trigger download
        const link = document.createElement('a');
        link.href = url;
        link.download = `batch_${batchNum}_data_${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Clean up
        URL.revokeObjectURL(url);

        // Show success briefly
        button.innerHTML = '✓ Done!';
        setTimeout(() => {
            button.innerHTML = originalText;
            button.disabled = false;
        }, 1500);

    } catch (error) {
        console.error('[Download] Error:', error);

        // Show error state
        button.innerHTML = '✗ Error';
        setTimeout(() => {
            button.innerHTML = originalText;
            button.disabled = false;
        }, 2000);

        // Alert user
        alert(`Failed to download Batch ${batchNum} data.\n\nMake sure the backend server is running at ${CONFIG.API_URL}\n\nError: ${error.message}`);
    }
}

/**
 * Navigation function to handle navigation between sections
 */
function navigateTo(section) {
    // Update active nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    event.target.closest('.nav-item').classList.add('active');

    if (section === 'live') {
        // Show dashboard
        document.querySelector('.tank-status-summary').style.display = 'block';
        document.querySelector('.dashboard').style.display = 'block';
        
        // Hide about section if it exists
        const aboutSection = document.getElementById('about-section');
        if (aboutSection) {
            aboutSection.style.display = 'none';
        }
    } else if (section === 'about') {
        // Hide dashboard
        document.querySelector('.tank-status-summary').style.display = 'none';
        document.querySelector('.dashboard').style.display = 'none';
        
        // Show or create about section
        let aboutSection = document.getElementById('about-section');
        if (!aboutSection) {
            aboutSection = createAboutSection();
            document.body.insertBefore(aboutSection, document.querySelector('footer'));
        }
        aboutSection.style.display = 'block';
    }
}

/**
 * Create the About section
 */
function createAboutSection() {
    const aboutSection = document.createElement('section');
    aboutSection.id = 'about-section';
    aboutSection.className = 'about-section';
    aboutSection.innerHTML = `
        <div class="about-container">
            <div class="about-header">
                <h1>About FermentIQ</h1>
                <p class="about-subtitle">AI-Powered Fermentation Monitoring Dashboard</p>
            </div>
            <div class="about-content">
                <div class="about-card">
                    <h2>What is FermentIQ?</h2>
                    <p>FermentIQ is a cutting-edge, AI-powered real-time fermentation monitoring dashboard designed to provide precise control and insights into your fermentation batches. Using advanced machine learning algorithms and WebSocket-based streaming, FermentIQ delivers live updates on critical parameters like pH, temperature, and CO2 production.</p>
                </div>
                <div class="about-card">
                    <h2>Key Features</h2>
                    <ul class="features-list">
                        <li><strong>Real-Time Monitoring:</strong> WebSocket-based live streaming of batch data</li>
                        <li><strong>AI-Powered Analysis:</strong> Machine learning algorithms compare your data against golden standards</li>
                        <li><strong>Visual Analytics:</strong> Interactive charts for pH, Temperature, and CO2 metrics</li>
                        <li><strong>Smart Alerts:</strong> Color-coded status indicators (Perfect, Acceptable, Concerning, Failed)</li>
                        <li><strong>Historical Tracking:</strong> Event logs and AI-generated suggestions for batch optimization</li>
                        <li><strong>Data Export:</strong> Download batch data as CSV for further analysis</li>
                    </ul>
                </div>
                <div class="about-card">
                    <h2>Technology Stack</h2>
                    <div class="tech-stack">
                        <div class="tech-item">
                            <span class="tech-name">Frontend</span>
                            <span class="tech-value">HTML5, CSS3, JavaScript, Chart.js</span>
                        </div>
                        <div class="tech-item">
                            <span class="tech-name">Backend</span>
                            <span class="tech-value">FastAPI, Python, WebSockets</span>
                        </div>
                        <div class="tech-item">
                            <span class="tech-name">AI/ML</span>
                            <span class="tech-value">scikit-learn, DTAIDistance, NumPy, Pandas</span>
                        </div>
                        <div class="tech-item">
                            <span class="tech-name">Communication</span>
                            <span class="tech-value">MQTT, WebSockets, REST API</span>
                        </div>
                    </div>
                </div>
                <div class="about-card">
                    <h2>How It Works</h2>
                    <p>FermentIQ continuously monitors your fermentation batches and compares them against a golden standard profile. The system uses Dynamic Time Warping (DTW) distance calculations to measure similarity, providing a quality score that indicates how closely your batch matches ideal fermentation conditions.</p>
                    <p>The AI system categorizes batches into four status categories:</p>
                    <div class="status-legend">
                        <div class="legend-item">
                            <div class="legend-dot perfect"></div>
                            <span><strong>Perfect:</strong> 95%+ match with golden standard</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-dot acceptable"></div>
                            <span><strong>Acceptable:</strong> 90% to under 95% match</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-dot concerning"></div>
                            <span><strong>Concerning:</strong> 80% to under 90% match</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-dot failed"></div>
                            <span><strong>Failed:</strong> Below 80% match</span>
                        </div>
                    </div>
                </div>
                <div class="about-card">
                    <h2>Version</h2>
                    <p>FermentIQ Dashboard v2.0</p>
                    <p class="about-footer">Real-time WebSocket Streaming | AI-Powered Monitoring | Open Source</p>
                </div>
            </div>
        </div>
    `;
    return aboutSection;
}

