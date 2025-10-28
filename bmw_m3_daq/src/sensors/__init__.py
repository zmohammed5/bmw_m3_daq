"""
Sensor modules for BMW M3 DAQ System.

Provides interfaces for:
- OBD-II (vehicle parameters)
- MPU6050 (accelerometer/gyroscope)
- NEO-6M GPS (position and speed)
- DS18B20 (temperature sensors)
"""

from .obd import OBDInterface
from .accelerometer import Accelerometer
from .gps import GPS
from .temperature import TemperatureSensors

__all__ = ['OBDInterface', 'Accelerometer', 'GPS', 'TemperatureSensors']
