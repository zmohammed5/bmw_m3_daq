"""
Sensor Calibration Utilities
Tools for calibrating accelerometer, GPS, and temperature sensors.
"""

import logging
import time
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any

logger = logging.getLogger(__name__)


class AccelerometerCalibration:
    """
    Calibration tools for MPU6050 accelerometer.

    Performs zero-point calibration and coordinate frame rotation.
    """

    def __init__(self, accelerometer):
        """
        Initialize calibration tool.

        Args:
            accelerometer: Accelerometer instance to calibrate
        """
        self.accel = accelerometer

    def calibrate_zero_point(self, samples: int = 100, duration_seconds: float = 10) -> Dict[str, float]:
        """
        Calibrate accelerometer zero point (stationary, level vehicle).

        Vehicle must be on level ground, engine off, no movement.

        Args:
            samples: Number of samples to collect
            duration_seconds: Duration to collect samples

        Returns:
            Dictionary with calibration offsets
        """
        print("\n" + "=" * 60)
        print("ACCELEROMETER ZERO POINT CALIBRATION")
        print("=" * 60)
        print("\nInstructions:")
        print("1. Park vehicle on level ground")
        print("2. Turn off engine")
        print("3. Ensure no movement for entire calibration period")
        print(f"4. Will collect {samples} samples over {duration_seconds} seconds")
        print("\nPress Enter when ready...")
        input()

        print(f"\nCollecting samples (do not move vehicle)...")

        accel_samples = []
        gyro_samples = []

        interval = duration_seconds / samples

        for i in range(samples):
            accel, gyro = self.accel.read_raw()
            accel_samples.append(accel)
            gyro_samples.append(gyro)

            if (i + 1) % 10 == 0:
                print(f"  Sample {i+1}/{samples}")

            time.sleep(interval)

        # Calculate mean offsets
        accel_mean = np.mean(accel_samples, axis=0)
        gyro_mean = np.mean(gyro_samples, axis=0)

        # Expected: Z-axis should read +9.8 m/s² (gravity), X and Y should be ~0
        # Offsets are what we need to subtract to get to ideal values
        accel_offset = accel_mean - np.array([0, 0, 9.80665])
        gyro_offset = gyro_mean  # Gyro should read zero when stationary

        print("\n" + "-" * 60)
        print("Calibration Results:")
        print("-" * 60)
        print(f"Accelerometer offset (m/s²):")
        print(f"  X: {accel_offset[0]:.4f}")
        print(f"  Y: {accel_offset[1]:.4f}")
        print(f"  Z: {accel_offset[2]:.4f}")
        print(f"\nGyroscope offset (rad/s):")
        print(f"  X: {gyro_offset[0]:.4f}")
        print(f"  Y: {gyro_offset[1]:.4f}")
        print(f"  Z: {gyro_offset[2]:.4f}")

        # Calculate standard deviations to check stability
        accel_std = np.std(accel_samples, axis=0)
        print(f"\nStability (std dev):")
        print(f"  Accel: {np.linalg.norm(accel_std):.4f} m/s²")
        print(f"  Gyro: {np.linalg.norm(np.std(gyro_samples, axis=0)):.4f} rad/s")

        if np.linalg.norm(accel_std) > 0.5:
            print("\nWARNING: High standard deviation - vehicle may have moved during calibration")

        return {
            'accel_offset_x': float(accel_offset[0]),
            'accel_offset_y': float(accel_offset[1]),
            'accel_offset_z': float(accel_offset[2]),
            'gyro_offset_x': float(gyro_offset[0]),
            'gyro_offset_y': float(gyro_offset[1]),
            'gyro_offset_z': float(gyro_offset[2])
        }

    def determine_orientation(self, samples: int = 50) -> np.ndarray:
        """
        Determine sensor orientation relative to vehicle.

        Tests which sensor axis corresponds to vehicle forward/lateral/vertical.

        Args:
            samples: Number of samples for each test

        Returns:
            3x3 rotation matrix
        """
        print("\n" + "=" * 60)
        print("ACCELEROMETER ORIENTATION CALIBRATION")
        print("=" * 60)
        print("\nThis will determine how the sensor is mounted in the vehicle.")
        print("You'll need to accelerate, turn, and brake to identify axes.")

        # For now, return identity matrix
        # In practice, user would perform maneuvers and we'd detect which
        # axis shows the largest change for each maneuver
        print("\nNote: Automatic orientation detection requires driving maneuvers.")
        print("For now, manually determine orientation and update config file.")
        print("\nDefault: assuming sensor aligned with vehicle axes")

        return np.eye(3)

    def save_calibration(self, calibration_data: Dict[str, float], config_path: str):
        """
        Save calibration data to sensor config file.

        Args:
            calibration_data: Calibration parameters
            config_path: Path to sensor_config.json
        """
        config_path = Path(config_path)

        try:
            # Load existing config
            with open(config_path, 'r') as f:
                config = json.load(f)

            # Update accelerometer calibration
            if 'accelerometer' not in config:
                config['accelerometer'] = {}
            if 'calibration' not in config['accelerometer']:
                config['accelerometer']['calibration'] = {}

            config['accelerometer']['calibration'].update(calibration_data)

            # Save updated config
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            print(f"\nCalibration saved to {config_path}")

        except Exception as e:
            logger.error(f"Failed to save calibration: {e}")


class TemperatureCalibration:
    """
    Calibration tools for DS18B20 temperature sensors.

    Helps identify which sensor ID corresponds to which physical location.
    """

    def __init__(self, temp_sensors):
        """
        Initialize temperature calibration tool.

        Args:
            temp_sensors: TemperatureSensors instance
        """
        self.temp_sensors = temp_sensors

    def identify_sensors(self):
        """
        Interactive sensor identification tool.

        Heat up one sensor at a time to identify which ID is which location.
        """
        print("\n" + "=" * 60)
        print("TEMPERATURE SENSOR IDENTIFICATION")
        print("=" * 60)
        print("\nThis tool helps you identify which sensor ID is which location.")
        print("\nInstructions:")
        print("1. Heat up ONE sensor at a time (e.g., hold in warm water)")
        print("2. Watch the display to see which sensor ID shows high temperature")
        print("3. Record the ID and location")
        print("\nPress Enter to start monitoring...")
        input()

        print("\nMonitoring temperature sensors (Ctrl+C to stop):\n")

        try:
            while True:
                # Read all sensors
                sensor_ids = self.temp_sensors.identify_sensors()

                # Clear screen (simple version)
                print("\033[2J\033[H")  # ANSI escape codes
                print("=" * 60)
                print(f"Temperature Sensor Readings - {time.strftime('%H:%M:%S')}")
                print("=" * 60)

                # Display readings
                for sensor_id, temp in sensor_ids.items():
                    name = self.temp_sensors.sensors.get(sensor_id, {}).get('name', 'Unknown')
                    location = self.temp_sensors.sensors.get(sensor_id, {}).get('location', 'Unknown')
                    print(f"{sensor_id}")
                    print(f"  Name: {name}")
                    print(f"  Location: {location}")
                    print(f"  Temperature: {temp}")
                    print()

                time.sleep(1)

        except KeyboardInterrupt:
            print("\n\nMonitoring stopped.")

    def save_sensor_mapping(self, mapping: Dict[str, Dict[str, str]], config_path: str):
        """
        Save sensor ID to location mapping.

        Args:
            mapping: Dictionary mapping sensor IDs to names/locations
            config_path: Path to sensor_config.json
        """
        config_path = Path(config_path)

        try:
            # Load existing config
            with open(config_path, 'r') as f:
                config = json.load(f)

            # Update temperature sensor configuration
            if 'temperature' not in config:
                config['temperature'] = {}
            config['temperature']['sensors'] = mapping

            # Save updated config
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            print(f"\nSensor mapping saved to {config_path}")

        except Exception as e:
            logger.error(f"Failed to save sensor mapping: {e}")


class GPSCalibration:
    """
    GPS calibration utilities.

    Mainly for setting coordinate offsets for privacy.
    """

    def __init__(self, gps):
        """
        Initialize GPS calibration tool.

        Args:
            gps: GPS instance
        """
        self.gps = gps

    def set_coordinate_offset(self, offset_lat: float = 0.0, offset_lon: float = 0.0):
        """
        Set coordinate offset for privacy.

        This adds a fixed offset to all GPS coordinates, shifting the track
        to a different location while preserving the shape.

        Args:
            offset_lat: Latitude offset in degrees
            offset_lon: Longitude offset in degrees
        """
        print("\n" + "=" * 60)
        print("GPS COORDINATE OFFSET CONFIGURATION")
        print("=" * 60)
        print("\nCoordinate offset shifts all GPS data by a fixed amount.")
        print("This is useful for privacy when sharing data publicly.")
        print("\nExample: offset_lat=1.0, offset_lon=-1.0")
        print("  Will shift all coordinates by +1° lat, -1° lon")

        self.gps.coord_offset = (offset_lat, offset_lon)
        print(f"\nOffset set: lat={offset_lat}, lon={offset_lon}")

    def wait_for_valid_fix(self, timeout: float = 60):
        """
        Wait for valid GPS fix and display status.

        Args:
            timeout: Maximum time to wait in seconds
        """
        print("\n" + "=" * 60)
        print("GPS FIX ACQUISITION")
        print("=" * 60)
        print("\nWaiting for GPS fix...")
        print("This may take 30-60 seconds after cold start.")
        print("For best results, park vehicle with clear sky view.\n")

        start_time = time.time()

        while (time.time() - start_time) < timeout:
            gps_data = self.gps.read()

            satellites = gps_data.get('satellites', 0)
            fix_mode = gps_data.get('fix_mode', 0)
            valid = gps_data.get('valid', False)

            fix_type = {0: 'No fix', 2: '2D fix', 3: '3D fix'}.get(fix_mode, 'Unknown')

            print(f"\rSatellites: {satellites} | Fix: {fix_type} | Valid: {valid}   ", end='')

            if valid:
                print("\n\n✓ Valid GPS fix acquired!")
                print(f"  Position: {gps_data['latitude']:.6f}, {gps_data['longitude']:.6f}")
                print(f"  Altitude: {gps_data['altitude_m']:.1f}m")
                print(f"  Satellites: {satellites}")
                return True

            time.sleep(1)

        print("\n\n✗ GPS fix timeout")
        return False


def run_calibration_wizard():
    """
    Interactive calibration wizard.

    Guides user through calibrating all sensors.
    """
    print("\n" + "=" * 60)
    print("BMW M3 DAQ - SENSOR CALIBRATION WIZARD")
    print("=" * 60)

    print("\nThis wizard will help you calibrate:")
    print("1. Accelerometer (zero point and orientation)")
    print("2. Temperature sensors (identify sensor IDs)")
    print("3. GPS (coordinate offset and fix test)")

    print("\nWhich sensor would you like to calibrate?")
    print("1) Accelerometer")
    print("2) Temperature sensors")
    print("3) GPS")
    print("4) All sensors")
    print("0) Exit")

    choice = input("\nEnter choice (0-4): ")

    # Implementation would initialize sensors and run appropriate calibration
    print("\nNote: Import and initialize sensors in main application to run calibrations.")


if __name__ == "__main__":
    # Run calibration wizard
    logging.basicConfig(level=logging.INFO)
    run_calibration_wizard()
