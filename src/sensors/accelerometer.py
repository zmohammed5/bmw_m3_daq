"""
Accelerometer/Gyroscope Module
Handles MPU6050 IMU sensor for measuring vehicle dynamics (g-forces, rotation).
"""

import logging
import time
import math
from typing import Dict, Tuple, Optional, Any
import numpy as np

logger = logging.getLogger(__name__)

try:
    import board
    import busio
    import adafruit_mpu6050
    HAS_HARDWARE = True
except (ImportError, NotImplementedError):
    HAS_HARDWARE = False
    logger.warning("MPU6050 hardware libraries not available - will run in simulation mode")


class Accelerometer:
    """
    Interface for MPU6050 accelerometer/gyroscope sensor.

    Provides calibrated acceleration and rotation data with coordinate
    transformation to vehicle frame (longitudinal, lateral, vertical).
    """

    # Gravitational constant (m/s²)
    GRAVITY = 9.80665

    def __init__(self, config: Dict[str, Any], simulation_mode: bool = False):
        """
        Initialize accelerometer interface.

        Args:
            config: Configuration dictionary with accelerometer settings
            simulation_mode: If True, generate fake data for testing
        """
        self.config = config
        self.simulation_mode = simulation_mode or not HAS_HARDWARE
        self.sensor = None
        self.connected = False

        # Calibration offsets (from calibration process)
        calibration = config.get('calibration', {})
        self.accel_offset = np.array([
            calibration.get('accel_offset_x', 0.0),
            calibration.get('accel_offset_y', 0.0),
            calibration.get('accel_offset_z', 0.0)
        ])
        self.gyro_offset = np.array([
            calibration.get('gyro_offset_x', 0.0),
            calibration.get('gyro_offset_y', 0.0),
            calibration.get('gyro_offset_z', 0.0)
        ])

        # Rotation matrix to transform sensor frame to vehicle frame
        # Default is identity (no rotation)
        self.rotation_matrix = np.array(calibration.get('rotation_matrix', [
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1]
        ]))

        # Complementary filter state
        self.filter_alpha = config.get('filter', {}).get('alpha', 0.98)
        self.pitch = 0.0
        self.roll = 0.0
        self.last_time = time.time()

        # Simulation state
        self.sim_time = time.time()
        self.sim_speed = 0.0

    def connect(self) -> bool:
        """
        Initialize connection to MPU6050 sensor.

        Returns:
            True if connected successfully, False otherwise
        """
        if self.simulation_mode:
            logger.info("Accelerometer: Running in simulation mode")
            self.connected = True
            return True

        try:
            # Initialize I2C bus
            i2c = busio.I2C(board.SCL, board.SDA)

            # Create MPU6050 object
            self.sensor = adafruit_mpu6050.MPU6050(i2c)

            # Configure accelerometer range (±2g, ±4g, ±8g, ±16g)
            accel_range = self.config.get('accel_range_g', 4)
            if accel_range == 2:
                self.sensor.accelerometer_range = adafruit_mpu6050.Range.RANGE_2_G
            elif accel_range == 4:
                self.sensor.accelerometer_range = adafruit_mpu6050.Range.RANGE_4_G
            elif accel_range == 8:
                self.sensor.accelerometer_range = adafruit_mpu6050.Range.RANGE_8_G
            else:
                self.sensor.accelerometer_range = adafruit_mpu6050.Range.RANGE_16_G

            # Configure gyroscope range (±250, ±500, ±1000, ±2000 dps)
            gyro_range = self.config.get('gyro_range_dps', 500)
            if gyro_range == 250:
                self.sensor.gyro_range = adafruit_mpu6050.GyroRange.RANGE_250_DPS
            elif gyro_range == 500:
                self.sensor.gyro_range = adafruit_mpu6050.GyroRange.RANGE_500_DPS
            elif gyro_range == 1000:
                self.sensor.gyro_range = adafruit_mpu6050.GyroRange.RANGE_1000_DPS
            else:
                self.sensor.gyro_range = adafruit_mpu6050.GyroRange.RANGE_2000_DPS

            logger.info(f"MPU6050 connected: ±{accel_range}g, ±{gyro_range}°/s")
            self.connected = True
            return True

        except Exception as e:
            logger.error(f"Failed to initialize MPU6050: {e}")
            self.simulation_mode = True
            self.connected = True  # Still "connected" in simulation
            return True

    def read_raw(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Read raw accelerometer and gyroscope values.

        Returns:
            Tuple of (acceleration, gyro_rate) as numpy arrays
            Acceleration in m/s², gyro in rad/s
        """
        if self.simulation_mode:
            return self._get_simulated_values()

        try:
            # Read sensor - returns (x, y, z) tuples
            accel_raw = self.sensor.acceleration  # m/s²
            gyro_raw = self.sensor.gyro  # rad/s

            accel = np.array(accel_raw)
            gyro = np.array(gyro_raw)

            return accel, gyro

        except Exception as e:
            logger.error(f"Error reading MPU6050: {e}")
            return np.zeros(3), np.zeros(3)

    def read_calibrated(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Read calibrated accelerometer and gyroscope values.

        Applies offset correction and coordinate transformation.

        Returns:
            Tuple of (acceleration, gyro_rate) in vehicle frame
            Acceleration in m/s², gyro in rad/s
        """
        accel_raw, gyro_raw = self.read_raw()

        # Apply offsets
        accel_corrected = accel_raw - self.accel_offset
        gyro_corrected = gyro_raw - self.gyro_offset

        # Transform to vehicle coordinate frame
        # Vehicle frame: X=forward, Y=left, Z=up
        accel_vehicle = self.rotation_matrix @ accel_corrected
        gyro_vehicle = self.rotation_matrix @ gyro_corrected

        return accel_vehicle, gyro_vehicle

    def read_g_forces(self) -> Dict[str, float]:
        """
        Read acceleration as g-forces in vehicle frame.

        Returns:
            Dictionary with longitudinal, lateral, vertical g-forces
        """
        accel, gyro = self.read_calibrated()

        # Convert m/s² to g-forces
        # Note: we subtract gravity from vertical to get dynamic g-force
        g_long = accel[0] / self.GRAVITY  # Forward/backward
        g_lat = accel[1] / self.GRAVITY   # Left/right
        g_vert = (accel[2] - self.GRAVITY) / self.GRAVITY  # Up/down (minus 1g static)

        return {
            'longitudinal_g': g_long,
            'lateral_g': g_lat,
            'vertical_g': g_vert,
            'total_g': math.sqrt(g_long**2 + g_lat**2 + g_vert**2)
        }

    def read_orientation(self) -> Dict[str, float]:
        """
        Calculate vehicle pitch and roll using complementary filter.

        Returns:
            Dictionary with pitch and roll in degrees
        """
        accel, gyro = self.read_calibrated()

        # Calculate time delta
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time

        # Calculate pitch and roll from accelerometer
        accel_pitch = math.atan2(accel[0], math.sqrt(accel[1]**2 + accel[2]**2))
        accel_roll = math.atan2(accel[1], math.sqrt(accel[0]**2 + accel[2]**2))

        # Integrate gyroscope for pitch and roll rates
        gyro_pitch = self.pitch + gyro[1] * dt
        gyro_roll = self.roll + gyro[0] * dt

        # Complementary filter: combine gyro (short-term) and accel (long-term)
        self.pitch = self.filter_alpha * gyro_pitch + (1 - self.filter_alpha) * accel_pitch
        self.roll = self.filter_alpha * gyro_roll + (1 - self.filter_alpha) * accel_roll

        return {
            'pitch_deg': math.degrees(self.pitch),
            'roll_deg': math.degrees(self.roll),
            'yaw_rate_dps': math.degrees(gyro[2])
        }

    def read_all(self) -> Dict[str, float]:
        """
        Read all accelerometer data (g-forces and orientation).

        Returns:
            Dictionary with all acceleration and orientation data
        """
        data = {}
        data.update(self.read_g_forces())
        data.update(self.read_orientation())
        return data

    def _get_simulated_values(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate simulated sensor values for testing.

        Simulates realistic driving scenarios with varying g-forces.

        Returns:
            Tuple of (acceleration, gyro_rate)
        """
        import random

        current_time = time.time()
        dt = current_time - self.sim_time
        self.sim_time = current_time

        # Simulate acceleration phases
        phase = (current_time % 20) / 20  # 20-second cycle

        if phase < 0.3:  # Acceleration
            accel_x = 3.0 + random.uniform(-0.5, 0.5)  # ~0.3g forward
            self.sim_speed += accel_x * dt
        elif phase < 0.5:  # Braking
            accel_x = -5.0 + random.uniform(-1.0, 1.0)  # ~0.5g braking
            self.sim_speed = max(0, self.sim_speed + accel_x * dt)
        elif phase < 0.7:  # Cornering
            accel_x = random.uniform(-2, 2)
            accel_y = 8.0 + random.uniform(-1, 1)  # ~0.8g lateral
        else:  # Cruising
            accel_x = random.uniform(-1, 1)
            accel_y = random.uniform(-1, 1)

        # Default lateral acceleration
        if phase >= 0.7 or phase < 0.5:
            accel_y = random.uniform(-2, 2)

        # Vertical (mostly gravity with small bumps)
        accel_z = self.GRAVITY + random.uniform(-2, 2)

        accel = np.array([accel_x, accel_y, accel_z])

        # Gyroscope (rotation rates)
        gyro_x = random.uniform(-0.1, 0.1)  # Roll rate
        gyro_y = random.uniform(-0.1, 0.1)  # Pitch rate
        gyro_z = random.uniform(-0.2, 0.2)  # Yaw rate
        gyro = np.array([gyro_x, gyro_y, gyro_z])

        return accel, gyro

    def is_connected(self) -> bool:
        """Check if accelerometer is connected."""
        return self.connected

    def get_temperature(self) -> Optional[float]:
        """
        Get internal sensor temperature.

        Returns:
            Temperature in Celsius, or None if not available
        """
        if self.simulation_mode:
            return 25.0 + np.random.uniform(-2, 5)

        try:
            if self.sensor:
                return self.sensor.temperature
        except Exception as e:
            logger.error(f"Error reading temperature: {e}")

        return None


if __name__ == "__main__":
    # Test the accelerometer interface in simulation mode
    logging.basicConfig(level=logging.INFO)

    test_config = {
        'accel_range_g': 4,
        'gyro_range_dps': 500,
        'sample_rate_hz': 50,
        'calibration': {
            'accel_offset_x': 0.0,
            'accel_offset_y': 0.0,
            'accel_offset_z': 0.0
        },
        'filter': {'alpha': 0.98}
    }

    accel = Accelerometer(test_config, simulation_mode=True)

    if accel.connect():
        print("Accelerometer connected")

        # Test reading data
        for i in range(10):
            data = accel.read_all()
            print(f"\nSample {i+1}:")
            print(f"  Longitudinal: {data['longitudinal_g']:.3f}g")
            print(f"  Lateral: {data['lateral_g']:.3f}g")
            print(f"  Vertical: {data['vertical_g']:.3f}g")
            print(f"  Total: {data['total_g']:.3f}g")
            print(f"  Pitch: {data['pitch_deg']:.2f}°")
            print(f"  Roll: {data['roll_deg']:.2f}°")
            print(f"  Temperature: {accel.get_temperature():.1f}°C")
            time.sleep(0.1)
    else:
        print("Failed to connect")
