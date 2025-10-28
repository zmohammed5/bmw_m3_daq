"""
Main Data Acquisition Application
Coordinates all sensors and logs vehicle data to CSV files.
"""

import logging
import time
import json
import csv
import sys
import signal
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from threading import Thread, Event, Lock
import queue

# Import sensor modules
from sensors import OBDInterface, Accelerometer, GPS, TemperatureSensors

logger = logging.getLogger(__name__)


class DataLogger:
    """
    Main data acquisition and logging system.

    Coordinates all sensors, collects data at specified rate,
    and writes to CSV files with proper buffering and error handling.
    """

    def __init__(self, config_dir: str = "config", data_dir: str = "data/sessions"):
        """
        Initialize data logger.

        Args:
            config_dir: Directory containing configuration files
            data_dir: Directory for data storage
        """
        self.config_dir = Path(config_dir)
        self.data_dir = Path(data_dir)

        # Load configurations
        self.vehicle_config = self._load_config("vehicle_config.json")
        self.sensor_config = self._load_config("sensor_config.json")
        self.system_config = self._load_config("system_config.json")

        # Determine if running in simulation mode
        self.simulation_mode = self.system_config.get('system', {}).get('simulation_mode', False)

        # Initialize sensors
        self.obd: Optional[OBDInterface] = None
        self.accelerometer: Optional[Accelerometer] = None
        self.gps: Optional[GPS] = None
        self.temp_sensors: Optional[TemperatureSensors] = None

        # Session management
        self.session_dir: Optional[Path] = None
        self.csv_file = None
        self.csv_writer = None
        self.csv_buffer = []

        # Threading control
        self.running = Event()
        self.data_queue = queue.Queue()
        self.data_lock = Lock()

        # Statistics
        self.samples_collected = 0
        self.session_start_time = None
        self.errors = {
            'obd': 0,
            'accelerometer': 0,
            'gps': 0,
            'temperature': 0
        }

        # Setup logging
        self._setup_logging()

    def _load_config(self, filename: str) -> Dict[str, Any]:
        """Load JSON configuration file."""
        config_path = self.config_dir / filename
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {filename}: {e}")
            return {}

    def _setup_logging(self):
        """Configure logging system."""
        log_config = self.system_config.get('logging', {})
        log_level = getattr(logging, log_config.get('level', 'INFO'))

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Console handler
        if log_config.get('console_output', True):
            console = logging.StreamHandler()
            console.setLevel(log_level)
            console.setFormatter(formatter)
            logging.getLogger().addHandler(console)

        # File handler
        if log_config.get('file_output', True):
            log_dir = Path(self.system_config.get('data', {}).get('log_path', 'logs'))
            log_dir.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(
                log_dir / f'daq_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logging.getLogger().addHandler(file_handler)

        logging.getLogger().setLevel(log_level)

    def initialize_sensors(self) -> bool:
        """
        Initialize all sensor interfaces.

        Returns:
            True if all sensors initialized successfully
        """
        logger.info("Initializing sensors...")
        success = True

        # Initialize OBD-II
        try:
            self.obd = OBDInterface(
                self.sensor_config.get('obd', {}),
                simulation_mode=self.simulation_mode
            )
            if not self.obd.connect():
                logger.error("OBD-II initialization failed")
                success = False
            else:
                logger.info(f"OBD-II: {self.obd.get_protocol_name()}")
        except Exception as e:
            logger.error(f"OBD-II exception: {e}")
            success = False

        # Initialize Accelerometer
        try:
            self.accelerometer = Accelerometer(
                self.sensor_config.get('accelerometer', {}),
                simulation_mode=self.simulation_mode
            )
            if not self.accelerometer.connect():
                logger.error("Accelerometer initialization failed")
                success = False
            else:
                logger.info("Accelerometer connected")
        except Exception as e:
            logger.error(f"Accelerometer exception: {e}")
            success = False

        # Initialize GPS
        try:
            self.gps = GPS(
                self.sensor_config.get('gps', {}),
                simulation_mode=self.simulation_mode
            )
            if not self.gps.connect():
                logger.error("GPS initialization failed")
                success = False
            else:
                logger.info("GPS connected")
        except Exception as e:
            logger.error(f"GPS exception: {e}")
            success = False

        # Initialize Temperature Sensors
        try:
            self.temp_sensors = TemperatureSensors(
                self.sensor_config.get('temperature', {}),
                simulation_mode=self.simulation_mode
            )
            if not self.temp_sensors.connect():
                logger.error("Temperature sensors initialization failed")
                success = False
            else:
                logger.info(f"Temperature: {self.temp_sensors.get_count()} sensors")
        except Exception as e:
            logger.error(f"Temperature sensors exception: {e}")
            success = False

        return success

    def create_session(self) -> bool:
        """
        Create new logging session directory and CSV file.

        Returns:
            True if session created successfully
        """
        # Create session directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.data_dir / f"session_{timestamp}"
        self.session_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Created session: {self.session_dir}")

        # Create CSV file
        csv_path = self.session_dir / "data.csv"

        try:
            self.csv_file = open(csv_path, 'w', newline='')

            # Define CSV headers
            headers = [
                'timestamp',
                'elapsed_time',
                # OBD-II
                'rpm', 'speed_mph', 'throttle_pos', 'coolant_temp_f', 'intake_temp_f',
                'maf_gps', 'engine_load', 'timing_advance', 'fuel_trim_short', 'fuel_trim_long',
                # Accelerometer
                'accel_long_g', 'accel_lat_g', 'accel_vert_g', 'accel_total_g',
                'pitch_deg', 'roll_deg', 'yaw_rate_dps',
                # GPS
                'gps_lat', 'gps_lon', 'gps_alt_m', 'gps_speed_mph',
                'gps_heading', 'gps_satellites', 'gps_valid',
                # Temperature
                'temp_oil_f', 'temp_intake_f', 'temp_brake_f', 'temp_trans_f', 'temp_ambient_f'
            ]

            self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=headers)
            self.csv_writer.writeheader()
            self.csv_file.flush()

            logger.info(f"CSV file created: {csv_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to create CSV file: {e}")
            return False

    def collect_data(self) -> Dict[str, Any]:
        """
        Collect data from all sensors.

        Returns:
            Dictionary with all sensor data
        """
        data = {
            'timestamp': datetime.now().isoformat(),
            'elapsed_time': time.time() - self.session_start_time if self.session_start_time else 0
        }

        # Collect OBD-II data
        if self.obd and self.obd.is_connected():
            try:
                obd_data = self.obd.read_all_pids()
                data['rpm'] = self._extract_value(obd_data.get('RPM'))
                data['speed_mph'] = self._extract_value(obd_data.get('SPEED'))
                data['throttle_pos'] = self._extract_value(obd_data.get('THROTTLE_POS'))
                data['coolant_temp_f'] = self._extract_value(obd_data.get('COOLANT_TEMP'))
                data['intake_temp_f'] = self._extract_value(obd_data.get('INTAKE_TEMP'))
                data['maf_gps'] = self._extract_value(obd_data.get('MAF'))
                data['engine_load'] = self._extract_value(obd_data.get('ENGINE_LOAD'))
                data['timing_advance'] = self._extract_value(obd_data.get('TIMING_ADVANCE'))
                data['fuel_trim_short'] = self._extract_value(obd_data.get('SHORT_FUEL_TRIM_1'))
                data['fuel_trim_long'] = self._extract_value(obd_data.get('LONG_FUEL_TRIM_1'))
            except Exception as e:
                logger.error(f"Error collecting OBD data: {e}")
                self.errors['obd'] += 1

        # Collect Accelerometer data
        if self.accelerometer and self.accelerometer.is_connected():
            try:
                accel_data = self.accelerometer.read_all()
                data['accel_long_g'] = accel_data.get('longitudinal_g')
                data['accel_lat_g'] = accel_data.get('lateral_g')
                data['accel_vert_g'] = accel_data.get('vertical_g')
                data['accel_total_g'] = accel_data.get('total_g')
                data['pitch_deg'] = accel_data.get('pitch_deg')
                data['roll_deg'] = accel_data.get('roll_deg')
                data['yaw_rate_dps'] = accel_data.get('yaw_rate_dps')
            except Exception as e:
                logger.error(f"Error collecting accelerometer data: {e}")
                self.errors['accelerometer'] += 1

        # Collect GPS data
        if self.gps and self.gps.is_connected():
            try:
                gps_data = self.gps.read()
                data['gps_lat'] = gps_data.get('latitude')
                data['gps_lon'] = gps_data.get('longitude')
                data['gps_alt_m'] = gps_data.get('altitude_m')
                data['gps_speed_mph'] = gps_data.get('speed_mph')
                data['gps_heading'] = gps_data.get('track_deg')
                data['gps_satellites'] = gps_data.get('satellites')
                data['gps_valid'] = gps_data.get('valid')
            except Exception as e:
                logger.error(f"Error collecting GPS data: {e}")
                self.errors['gps'] += 1

        # Collect Temperature data
        if self.temp_sensors and self.temp_sensors.is_connected():
            try:
                temp_data = self.temp_sensors.read_all()
                data['temp_oil_f'] = temp_data.get('engine_oil')
                data['temp_intake_f'] = temp_data.get('intake_air')
                data['temp_brake_f'] = temp_data.get('brake_fluid')
                data['temp_trans_f'] = temp_data.get('transmission')
                data['temp_ambient_f'] = temp_data.get('ambient')

                # Check temperature thresholds
                alerts = self.temp_sensors.check_thresholds()
                if alerts['critical']:
                    logger.critical(f"CRITICAL TEMPERATURE: {', '.join(alerts['critical'])}")
                elif alerts['warnings']:
                    logger.warning(f"Temperature warning: {', '.join(alerts['warnings'])}")

            except Exception as e:
                logger.error(f"Error collecting temperature data: {e}")
                self.errors['temperature'] += 1

        return data

    def _extract_value(self, obj):
        """Extract numeric value from OBD response object."""
        if obj is None:
            return None
        if hasattr(obj, 'magnitude'):
            return obj.magnitude
        return obj

    def write_data(self, data: Dict[str, Any]):
        """
        Write data to CSV file with buffering.

        Args:
            data: Dictionary of sensor data
        """
        try:
            with self.data_lock:
                self.csv_buffer.append(data)
                self.samples_collected += 1

                # Flush buffer when it reaches configured size
                buffer_size = self.system_config.get('data', {}).get('csv_buffer_size', 100)
                if len(self.csv_buffer) >= buffer_size:
                    self._flush_buffer()

        except Exception as e:
            logger.error(f"Error writing data: {e}")

    def _flush_buffer(self):
        """Flush CSV buffer to file."""
        if not self.csv_buffer:
            return

        try:
            self.csv_writer.writerows(self.csv_buffer)
            self.csv_file.flush()
            logger.debug(f"Flushed {len(self.csv_buffer)} samples to CSV")
            self.csv_buffer.clear()
        except Exception as e:
            logger.error(f"Error flushing buffer: {e}")

    def run(self):
        """Main data collection loop."""
        logger.info("Starting data collection...")
        self.running.set()
        self.session_start_time = time.time()

        # Target loop rate from config
        target_rate_hz = self.system_config.get('performance', {}).get('main_loop_rate_hz', 50)
        target_period = 1.0 / target_rate_hz

        last_status_time = time.time()
        status_interval = 10  # Print status every 10 seconds

        while self.running.is_set():
            loop_start = time.time()

            try:
                # Collect data from all sensors
                data = self.collect_data()

                # Write to CSV
                self.write_data(data)

                # Print status periodically
                if time.time() - last_status_time >= status_interval:
                    self._print_status()
                    last_status_time = time.time()

            except Exception as e:
                logger.error(f"Error in main loop: {e}")

            # Sleep to maintain target rate
            loop_duration = time.time() - loop_start
            sleep_time = max(0, target_period - loop_duration)
            time.sleep(sleep_time)

        logger.info("Data collection stopped")

    def _print_status(self):
        """Print current status to console."""
        elapsed = time.time() - self.session_start_time if self.session_start_time else 0
        rate = self.samples_collected / elapsed if elapsed > 0 else 0

        logger.info(f"Session: {elapsed:.1f}s | Samples: {self.samples_collected} | Rate: {rate:.1f} Hz")
        logger.info(f"Errors - OBD: {self.errors['obd']} | Accel: {self.errors['accelerometer']} | "
                   f"GPS: {self.errors['gps']} | Temp: {self.errors['temperature']}")

    def stop(self):
        """Stop data collection and cleanup."""
        logger.info("Stopping data logger...")
        self.running.clear()

        # Flush remaining buffer
        with self.data_lock:
            self._flush_buffer()

        # Close CSV file
        if self.csv_file:
            self.csv_file.close()
            logger.info("CSV file closed")

        # Save session summary
        self._save_session_summary()

        # Disconnect sensors
        if self.obd:
            self.obd.disconnect()
        logger.info("Sensors disconnected")

    def _save_session_summary(self):
        """Save session summary JSON file."""
        if not self.session_dir:
            return

        summary = {
            'session_start': datetime.fromtimestamp(self.session_start_time).isoformat() if self.session_start_time else None,
            'session_end': datetime.now().isoformat(),
            'duration_seconds': time.time() - self.session_start_time if self.session_start_time else 0,
            'samples_collected': self.samples_collected,
            'errors': self.errors,
            'vehicle': self.vehicle_config.get('vehicle', {}),
            'simulation_mode': self.simulation_mode
        }

        summary_path = self.session_dir / "session_summary.json"
        try:
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2)
            logger.info(f"Session summary saved: {summary_path}")
        except Exception as e:
            logger.error(f"Failed to save session summary: {e}")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Received shutdown signal")
    if hasattr(signal_handler, 'logger_instance'):
        signal_handler.logger_instance.stop()
    sys.exit(0)


def main():
    """Main entry point."""
    print("=" * 60)
    print("BMW M3 Data Acquisition System")
    print("=" * 60)

    # Create data logger
    logger_instance = DataLogger()

    # Register signal handlers for graceful shutdown
    signal_handler.logger_instance = logger_instance
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Initialize sensors
    if not logger_instance.initialize_sensors():
        logger.error("Sensor initialization failed - check connections")
        if not logger_instance.simulation_mode:
            sys.exit(1)

    # Create session
    if not logger_instance.create_session():
        logger.error("Failed to create session")
        sys.exit(1)

    # Run data collection
    try:
        logger_instance.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        logger_instance.stop()

    print("\nSession complete!")
    print(f"Data saved to: {logger_instance.session_dir}")


if __name__ == "__main__":
    main()
