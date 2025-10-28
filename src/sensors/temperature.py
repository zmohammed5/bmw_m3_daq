"""
Temperature Sensor Module
Handles DS18B20 1-Wire temperature sensors for monitoring oil, intake, brake, transmission temps.
"""

import logging
import time
import glob
from typing import Dict, List, Optional, Any
import random

logger = logging.getLogger(__name__)

try:
    from w1thermsensor import W1ThermSensor, Sensor
    HAS_W1 = True
except ImportError:
    HAS_W1 = False
    logger.warning("w1thermsensor not available - will run in simulation mode")


class TemperatureSensors:
    """
    Interface for DS18B20 1-Wire temperature sensors.

    Manages multiple temperature sensors with automatic discovery,
    threshold warnings, and sensor identification.
    """

    def __init__(self, config: Dict[str, Any], simulation_mode: bool = False):
        """
        Initialize temperature sensor interface.

        Args:
            config: Configuration dictionary with temperature sensor settings
            simulation_mode: If True, generate fake data for testing
        """
        self.config = config
        self.simulation_mode = simulation_mode or not HAS_W1
        self.sensors: Dict[str, Any] = {}
        self.sensor_config = config.get('sensors', {})
        self.connected = False

        # Simulation state
        self.sim_temps = {
            'engine_oil': 190.0,
            'intake_air': 80.0,
            'brake_fluid': 180.0,
            'transmission': 195.0,
            'ambient': 75.0
        }

    def connect(self) -> bool:
        """
        Discover and initialize all connected temperature sensors.

        Returns:
            True if at least one sensor found
        """
        if self.simulation_mode:
            logger.info("Temperature sensors: Running in simulation mode")
            self._setup_simulated_sensors()
            self.connected = True
            return True

        try:
            # Discover all DS18B20 sensors on the 1-Wire bus
            discovered = W1ThermSensor.get_available_sensors([Sensor.DS18B20])

            if not discovered:
                logger.warning("No DS18B20 sensors found")
                logger.info("Make sure 1-Wire is enabled: add 'dtoverlay=w1-gpio' to /boot/config.txt")
                self.simulation_mode = True
                self._setup_simulated_sensors()
                self.connected = True
                return True

            # Map discovered sensors to configured names
            for sensor in discovered:
                sensor_id = sensor.id
                logger.debug(f"Found sensor: {sensor_id}")

                # Check if this sensor is in our configuration
                if sensor_id in self.sensor_config:
                    config = self.sensor_config[sensor_id]
                    self.sensors[sensor_id] = {
                        'sensor': sensor,
                        'name': config['name'],
                        'location': config['location'],
                        'warning_threshold': config.get('warning_threshold_f', 999),
                        'critical_threshold': config.get('critical_threshold_f', 999)
                    }
                    logger.info(f"Registered sensor {config['name']}: {sensor_id}")
                else:
                    # Unknown sensor - add with generic name
                    self.sensors[sensor_id] = {
                        'sensor': sensor,
                        'name': f'unknown_{sensor_id[:8]}',
                        'location': 'Unknown',
                        'warning_threshold': 999,
                        'critical_threshold': 999
                    }
                    logger.warning(f"Unknown sensor found: {sensor_id} - add to config to name it")

            logger.info(f"Temperature sensors connected: {len(self.sensors)} sensors")
            self.connected = True
            return len(self.sensors) > 0

        except Exception as e:
            logger.error(f"Failed to initialize temperature sensors: {e}")
            self.simulation_mode = True
            self._setup_simulated_sensors()
            self.connected = True
            return True

    def _setup_simulated_sensors(self):
        """Set up simulated sensors for testing."""
        for sensor_id, config in self.sensor_config.items():
            self.sensors[sensor_id] = {
                'sensor': None,
                'name': config['name'],
                'location': config['location'],
                'warning_threshold': config.get('warning_threshold_f', 999),
                'critical_threshold': config.get('critical_threshold_f', 999)
            }

    def read_sensor(self, sensor_id: str, retries: int = 3) -> Optional[float]:
        """
        Read temperature from a specific sensor.

        Args:
            sensor_id: Sensor ID to read
            retries: Number of retries if read fails

        Returns:
            Temperature in Fahrenheit, or None if failed
        """
        if sensor_id not in self.sensors:
            logger.warning(f"Unknown sensor ID: {sensor_id}")
            return None

        if self.simulation_mode:
            sensor_info = self.sensors[sensor_id]
            name = sensor_info['name']
            return self._get_simulated_temp(name)

        sensor_info = self.sensors[sensor_id]
        sensor = sensor_info['sensor']

        for attempt in range(retries):
            try:
                # Read temperature in Celsius
                temp_c = sensor.get_temperature()

                # Convert to Fahrenheit
                temp_f = (temp_c * 9/5) + 32

                return temp_f

            except Exception as e:
                if attempt < retries - 1:
                    logger.debug(f"Sensor read failed (attempt {attempt+1}/{retries}): {e}")
                    time.sleep(0.1)
                else:
                    logger.error(f"Failed to read sensor {sensor_id}: {e}")
                    return None

        return None

    def read_all(self) -> Dict[str, Optional[float]]:
        """
        Read all temperature sensors.

        Returns:
            Dictionary mapping sensor names to temperatures in Fahrenheit
        """
        temps = {}

        for sensor_id, sensor_info in self.sensors.items():
            name = sensor_info['name']
            temp = self.read_sensor(sensor_id)
            temps[name] = temp

        return temps

    def check_thresholds(self) -> Dict[str, List[str]]:
        """
        Check all sensors against warning/critical thresholds.

        Returns:
            Dictionary with 'warnings' and 'critical' lists of sensor names
        """
        warnings = []
        critical = []

        temps = self.read_all()

        for sensor_id, sensor_info in self.sensors.items():
            name = sensor_info['name']
            temp = temps.get(name)

            if temp is None:
                continue

            # Check thresholds
            if temp >= sensor_info['critical_threshold']:
                critical.append(name)
                logger.error(f"CRITICAL: {name} = {temp:.1f}°F (limit: {sensor_info['critical_threshold']}°F)")
            elif temp >= sensor_info['warning_threshold']:
                warnings.append(name)
                logger.warning(f"WARNING: {name} = {temp:.1f}°F (limit: {sensor_info['warning_threshold']}°F)")

        return {
            'warnings': warnings,
            'critical': critical
        }

    def get_sensor_info(self) -> List[Dict[str, str]]:
        """
        Get information about all configured sensors.

        Returns:
            List of sensor info dictionaries
        """
        info = []
        for sensor_id, sensor_info in self.sensors.items():
            info.append({
                'id': sensor_id,
                'name': sensor_info['name'],
                'location': sensor_info['location'],
                'warning_threshold_f': sensor_info['warning_threshold'],
                'critical_threshold_f': sensor_info['critical_threshold']
            })
        return info

    def identify_sensors(self) -> Dict[str, str]:
        """
        Create a mapping of sensor IDs to names for calibration.

        This helps identify which physical sensor corresponds to which ID.
        Heat up each sensor one at a time and run this to see which ID shows high temp.

        Returns:
            Dictionary mapping sensor IDs to current temperatures
        """
        temps = {}

        for sensor_id in self.sensors.keys():
            temp = self.read_sensor(sensor_id)
            temps[sensor_id] = f"{temp:.1f}°F" if temp else "ERROR"

        return temps

    def _get_simulated_temp(self, sensor_name: str) -> float:
        """
        Generate simulated temperature for testing.

        Args:
            sensor_name: Name of sensor to simulate

        Returns:
            Simulated temperature in Fahrenheit
        """
        base_temp = self.sim_temps.get(sensor_name, 100.0)

        # Add random variation
        variation = random.uniform(-5, 10)

        # Slowly increase over time (simulating heat buildup)
        time_factor = (time.time() % 600) / 600  # 10-minute cycle
        heat_increase = time_factor * 20

        temp = base_temp + variation + heat_increase

        # Update base for next time
        self.sim_temps[sensor_name] = base_temp + 0.1

        return temp

    def is_connected(self) -> bool:
        """Check if temperature sensors are connected."""
        return self.connected

    def get_count(self) -> int:
        """Get number of connected sensors."""
        return len(self.sensors)


if __name__ == "__main__":
    # Test the temperature sensor interface in simulation mode
    logging.basicConfig(level=logging.INFO)

    test_config = {
        'sensors': {
            '28-000000000001': {
                'name': 'engine_oil',
                'location': 'Oil dipstick tube',
                'warning_threshold_f': 280,
                'critical_threshold_f': 300
            },
            '28-000000000002': {
                'name': 'intake_air',
                'location': 'Intake manifold',
                'warning_threshold_f': 140,
                'critical_threshold_f': 160
            },
            '28-000000000003': {
                'name': 'brake_fluid',
                'location': 'Brake reservoir',
                'warning_threshold_f': 250,
                'critical_threshold_f': 300
            },
            '28-000000000004': {
                'name': 'transmission',
                'location': 'Transmission pan',
                'warning_threshold_f': 240,
                'critical_threshold_f': 260
            },
            '28-000000000005': {
                'name': 'ambient',
                'location': 'Ambient air',
                'warning_threshold_f': 999,
                'critical_threshold_f': 999
            }
        },
        'sample_rate_hz': 1
    }

    temp_sensors = TemperatureSensors(test_config, simulation_mode=True)

    if temp_sensors.connect():
        print(f"Connected {temp_sensors.get_count()} temperature sensors")

        # Print sensor info
        print("\nConfigured sensors:")
        for info in temp_sensors.get_sensor_info():
            print(f"  {info['name']}: {info['location']}")

        # Test reading temperatures
        for i in range(10):
            print(f"\n--- Reading {i+1} ---")
            temps = temp_sensors.read_all()
            for name, temp in temps.items():
                if temp:
                    print(f"  {name}: {temp:.1f}°F")
                else:
                    print(f"  {name}: ERROR")

            # Check thresholds
            alerts = temp_sensors.check_thresholds()
            if alerts['warnings']:
                print(f"  WARNINGS: {', '.join(alerts['warnings'])}")
            if alerts['critical']:
                print(f"  CRITICAL: {', '.join(alerts['critical'])}")

            time.sleep(1)
    else:
        print("Failed to connect")
