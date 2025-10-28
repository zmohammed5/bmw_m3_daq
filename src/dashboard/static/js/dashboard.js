// BMW M3 DAQ Dashboard JavaScript

// Initialize Socket.IO connection
const socket = io();

// Connection status
socket.on('connect', function() {
    console.log('Connected to server');
    updateConnectionStatus(true);
});

socket.on('disconnect', function() {
    console.log('Disconnected from server');
    updateConnectionStatus(false);
});

// Receive sensor updates
socket.on('sensor_update', function(data) {
    updateDashboard(data);
});

// Update connection status indicator
function updateConnectionStatus(connected) {
    const statusBar = document.querySelector('.status-bar');
    if (connected) {
        statusBar.style.borderLeft = '4px solid var(--status-connected)';
    } else {
        statusBar.style.borderLeft = '4px solid var(--status-disconnected)';
    }
}

// Update all dashboard elements
function updateDashboard(data) {
    // Update timestamp
    const now = new Date();
    document.getElementById('last-update').textContent = now.toLocaleTimeString();

    // Update sensor connection status
    if (data.connection_status) {
        updateSensorStatus('status-obd', data.connection_status.obd);
        updateSensorStatus('status-accel', data.connection_status.accelerometer);
        updateSensorStatus('status-gps', data.connection_status.gps);
        updateSensorStatus('status-temp', data.connection_status.temperature);
    }

    // Update RPM
    if (data.rpm !== undefined) {
        updateGauge('rpm', data.rpm, 0, 8000);
    }

    // Update Speed
    if (data.speed_mph !== undefined) {
        updateGauge('speed', data.speed_mph, 0, 155);
    }

    // Update Throttle
    if (data.throttle_pos !== undefined) {
        updateGauge('throttle', data.throttle_pos, 0, 100);
    }

    // Update G-Forces
    if (data.accel_long_g !== undefined) {
        updateGForce('g-long', data.accel_long_g, -1.5, 1.0);
    }

    if (data.accel_lat_g !== undefined) {
        updateGForce('g-lat', data.accel_lat_g, -1.2, 1.2);
    }

    if (data.accel_total_g !== undefined) {
        const totalElement = document.getElementById('g-total');
        if (totalElement) {
            totalElement.innerHTML = data.accel_total_g.toFixed(2) + '<span class="unit">g</span>';
        }
    }

    // Update Temperatures
    updateTemperature('temp-oil', data.temp_engine_oil, 280, 300);
    updateTemperature('temp-intake', data.temp_intake_air, 140, 160);
    updateTemperature('temp-brake', data.temp_brake_fluid, 250, 300);
    updateTemperature('temp-trans', data.temp_transmission, 240, 260);

    // Update GPS
    if (data.gps_speed_mph !== undefined) {
        const gpsSpeedElement = document.getElementById('gps-speed');
        if (gpsSpeedElement) {
            gpsSpeedElement.innerHTML = Math.round(data.gps_speed_mph) + '<span class="unit">mph</span>';
        }
    }

    if (data.gps_satellites !== undefined) {
        const satElement = document.getElementById('gps-sats');
        if (satElement) {
            satElement.textContent = data.gps_satellites;

            // Color code by satellite count
            if (data.gps_satellites >= 4) {
                satElement.style.color = 'var(--gauge-safe)';
            } else {
                satElement.style.color = 'var(--gauge-danger)';
            }
        }
    }
}

// Update sensor connection status
function updateSensorStatus(elementId, connected) {
    const element = document.getElementById(elementId);
    if (element) {
        if (connected) {
            element.classList.add('connected');
        } else {
            element.classList.remove('connected');
        }
    }
}

// Update gauge (RPM, Speed, Throttle)
function updateGauge(gaugeName, value, min, max) {
    const valueElement = document.getElementById(`${gaugeName}-value`);
    const fillElement = document.getElementById(`${gaugeName}-fill`);

    if (!valueElement || !fillElement) return;

    // Update value display
    let displayValue = Math.round(value);

    if (gaugeName === 'throttle') {
        valueElement.innerHTML = displayValue + '<span class="unit">%</span>';
    } else if (gaugeName === 'speed') {
        valueElement.innerHTML = displayValue + '<span class="unit">mph</span>';
    } else {
        valueElement.textContent = displayValue;
    }

    // Update fill bar
    const percentage = Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100));
    fillElement.style.width = percentage + '%';

    // Change color based on value
    if (gaugeName === 'rpm') {
        if (value > 7000) {
            valueElement.style.color = 'var(--gauge-danger)';
        } else if (value > 6000) {
            valueElement.style.color = 'var(--gauge-warning)';
        } else {
            valueElement.style.color = 'var(--accent-blue)';
        }
    }
}

// Update G-force display
function updateGForce(gaugeName, value, min, max) {
    const valueElement = document.getElementById(gaugeName);
    const fillElement = document.getElementById(`${gaugeName}-fill`);

    if (!valueElement) return;

    // Update value display
    valueElement.innerHTML = value.toFixed(2) + '<span class="unit">g</span>';

    // Color code by value
    if (Math.abs(value) > 0.8) {
        valueElement.style.color = 'var(--gauge-danger)';
    } else if (Math.abs(value) > 0.5) {
        valueElement.style.color = 'var(--gauge-warning)';
    } else {
        valueElement.style.color = 'var(--accent-green)';
    }

    if (value < 0) {
        valueElement.classList.add('negative');
    } else {
        valueElement.classList.remove('negative');
    }

    // Update fill bar (centered at 50% for bidirectional)
    if (fillElement) {
        const range = max - min;
        const normalized = (value - min) / range;
        const percentage = Math.max(0, Math.min(100, normalized * 100));
        fillElement.style.width = percentage + '%';

        // Change color based on direction
        if (value > 0) {
            fillElement.style.background = 'var(--accent-green)';
        } else {
            fillElement.style.background = 'var(--accent-red)';
        }
    }
}

// Update temperature display
function updateTemperature(elementId, value, warningThreshold, criticalThreshold) {
    const element = document.getElementById(elementId);
    if (!element || value === undefined || value === null) {
        if (element) {
            element.innerHTML = '--<span class="unit">°F</span>';
        }
        return;
    }

    // Update value
    element.innerHTML = Math.round(value) + '<span class="unit">°F</span>';

    // Color code by threshold
    element.classList.remove('warning', 'critical');

    if (value >= criticalThreshold) {
        element.classList.add('critical');
    } else if (value >= warningThreshold) {
        element.classList.add('warning');
    }
}

// Request initial data on load
window.addEventListener('load', function() {
    console.log('Dashboard loaded');
    socket.emit('request_update');
});

// Request update every 5 seconds as fallback
setInterval(function() {
    socket.emit('request_update');
}, 5000);
