"""
Flask Web Dashboard
Real-time web interface for monitoring DAQ system.
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import logging
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
from threading import Thread, Event
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sensors import OBDInterface, Accelerometer, GPS, TemperatureSensors

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bmw_m3_daq_secret_key_change_in_production'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')


class DashboardServer:
    """
    Web dashboard server for real-time data display.

    Provides live sensor data via WebSocket and HTTP API.
    """

    def __init__(self, config_dir: str = "config"):
        """
        Initialize dashboard server.

        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)

        # Load configurations
        self.vehicle_config = self._load_config("vehicle_config.json")
        self.sensor_config = self._load_config("sensor_config.json")
        self.system_config = self._load_config("system_config.json")

        # Sensors
        self.obd: Optional[OBDInterface] = None
        self.accelerometer: Optional[Accelerometer] = None
        self.gps: Optional[GPS] = None
        self.temp_sensors: Optional[TemperatureSensors] = None

        # Dashboard state
        self.running = Event()
        self.logging_active = False
        self.simulation_mode = self.system_config.get('system', {}).get('simulation_mode', False)

        # Latest data
        self.latest_data: Dict[str, Any] = {}

        # Initialize sensors
        self.initialize_sensors()

    def _load_config(self, filename: str) -> Dict[str, Any]:
        """Load JSON configuration file."""
        config_path = self.config_dir / filename
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load {filename}: {e}")
            return {}

    def initialize_sensors(self):
        """Initialize all sensor interfaces."""
        logger.info("Initializing sensors for dashboard...")

        try:
            self.obd = OBDInterface(
                self.sensor_config.get('obd', {}),
                simulation_mode=self.simulation_mode
            )
            self.obd.connect()
        except Exception as e:
            logger.error(f"OBD initialization failed: {e}")

        try:
            self.accelerometer = Accelerometer(
                self.sensor_config.get('accelerometer', {}),
                simulation_mode=self.simulation_mode
            )
            self.accelerometer.connect()
        except Exception as e:
            logger.error(f"Accelerometer initialization failed: {e}")

        try:
            self.gps = GPS(
                self.sensor_config.get('gps', {}),
                simulation_mode=self.simulation_mode
            )
            self.gps.connect()
        except Exception as e:
            logger.error(f"GPS initialization failed: {e}")

        try:
            self.temp_sensors = TemperatureSensors(
                self.sensor_config.get('temperature', {}),
                simulation_mode=self.simulation_mode
            )
            self.temp_sensors.connect()
        except Exception as e:
            logger.error(f"Temperature sensors initialization failed: {e}")

    def collect_data(self) -> Dict[str, Any]:
        """
        Collect current data from all sensors.

        Returns:
            Dictionary with all sensor data
        """
        data = {
            'timestamp': time.time(),
            'connection_status': self.get_connection_status()
        }

        # OBD-II data
        if self.obd and self.obd.is_connected():
            try:
                obd_data = self.obd.read_all_fast_pids()
                data['rpm'] = self._extract_value(obd_data.get('RPM', 0))
                data['speed_mph'] = self._extract_value(obd_data.get('SPEED', 0))
                data['throttle_pos'] = self._extract_value(obd_data.get('THROTTLE_POS', 0))
            except Exception as e:
                logger.error(f"Error reading OBD: {e}")

        # Accelerometer data
        if self.accelerometer and self.accelerometer.is_connected():
            try:
                accel_data = self.accelerometer.read_all()
                data['accel_long_g'] = round(accel_data.get('longitudinal_g', 0), 3)
                data['accel_lat_g'] = round(accel_data.get('lateral_g', 0), 3)
                data['accel_total_g'] = round(accel_data.get('total_g', 0), 3)
            except Exception as e:
                logger.error(f"Error reading accelerometer: {e}")

        # GPS data
        if self.gps and self.gps.is_connected():
            try:
                gps_data = self.gps.read()
                data['gps_speed_mph'] = round(gps_data.get('speed_mph', 0), 1)
                data['gps_satellites'] = gps_data.get('satellites', 0)
                data['gps_valid'] = gps_data.get('valid', False)
            except Exception as e:
                logger.error(f"Error reading GPS: {e}")

        # Temperature data
        if self.temp_sensors and self.temp_sensors.is_connected():
            try:
                temp_data = self.temp_sensors.read_all()
                for name, temp in temp_data.items():
                    if temp:
                        data[f'temp_{name}'] = round(temp, 1)
            except Exception as e:
                logger.error(f"Error reading temperatures: {e}")

        self.latest_data = data
        return data

    def _extract_value(self, obj):
        """Extract numeric value from OBD response."""
        if obj is None:
            return 0
        if hasattr(obj, 'magnitude'):
            return obj.magnitude
        return obj

    def get_connection_status(self) -> Dict[str, bool]:
        """Get connection status of all sensors."""
        return {
            'obd': self.obd.is_connected() if self.obd else False,
            'accelerometer': self.accelerometer.is_connected() if self.accelerometer else False,
            'gps': self.gps.is_connected() if self.gps else False,
            'temperature': self.temp_sensors.is_connected() if self.temp_sensors else False
        }

    def start_updates(self):
        """Start background thread for sending updates."""
        self.running.set()

        def update_loop():
            update_rate_hz = self.system_config.get('dashboard', {}).get('update_rate_hz', 10)
            update_interval = 1.0 / update_rate_hz

            while self.running.is_set():
                try:
                    data = self.collect_data()
                    socketio.emit('sensor_update', data)
                    time.sleep(update_interval)
                except Exception as e:
                    logger.error(f"Error in update loop: {e}")
                    time.sleep(1)

        Thread(target=update_loop, daemon=True).start()

    def stop_updates(self):
        """Stop background updates."""
        self.running.clear()


# Global dashboard instance
dashboard = None


# Flask routes
@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html', vehicle=dashboard.vehicle_config.get('vehicle', {}))


@app.route('/api/data')
def get_data():
    """Get current sensor data (HTTP API)."""
    if dashboard:
        return jsonify(dashboard.latest_data)
    return jsonify({'error': 'Dashboard not initialized'}), 500


@app.route('/api/status')
def get_status():
    """Get system status."""
    if dashboard:
        return jsonify({
            'sensors': dashboard.get_connection_status(),
            'logging': dashboard.logging_active,
            'simulation_mode': dashboard.simulation_mode
        })
    return jsonify({'error': 'Dashboard not initialized'}), 500


# SocketIO events
@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info(f"Client connected: {request.sid}")
    if dashboard:
        emit('sensor_update', dashboard.latest_data)


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info(f"Client disconnected: {request.sid}")


@socketio.on('request_update')
def handle_update_request():
    """Handle manual update request."""
    if dashboard:
        data = dashboard.collect_data()
        emit('sensor_update', data)


def main():
    """Start dashboard server."""
    global dashboard

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 60)
    print("BMW M3 DAQ - Web Dashboard")
    print("=" * 60)

    # Create dashboard
    config_dir = Path(__file__).parent.parent.parent / "config"
    dashboard = DashboardServer(config_dir=str(config_dir))

    # Start background updates
    dashboard.start_updates()

    # Get dashboard config
    dash_config = dashboard.system_config.get('dashboard', {})
    host = dash_config.get('host', '0.0.0.0')
    port = dash_config.get('port', 5000)

    print(f"\nDashboard running on http://{host}:{port}")
    print(f"Access from phone: http://<pi_ip_address>:{port}")
    print("Press Ctrl+C to stop\n")

    # Run server
    try:
        socketio.run(app, host=host, port=port, debug=False)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        dashboard.stop_updates()


if __name__ == "__main__":
    main()
