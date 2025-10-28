#!/usr/bin/env python3
"""
Sensor Test Script
Test each sensor individually to verify hardware connections.
"""

import sys
import time
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import json
from sensors import OBDInterface, Accelerometer, GPS, TemperatureSensors

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_file: str) -> dict:
    """Load configuration file."""
    config_path = Path(__file__).parent.parent / "config" / config_file
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {config_file}: {e}")
        return {}


def test_obd():
    """Test OBD-II connection and data."""
    print("\n" + "=" * 60)
    print("TESTING OBD-II INTERFACE")
    print("=" * 60)

    config = load_config("sensor_config.json")
    obd_config = config.get('obd', {})

    print("\nInitializing OBD-II adapter...")
    obd = OBDInterface(obd_config, simulation_mode=False)

    if not obd.connect():
        print("✗ Failed to connect to OBD-II adapter")
        print("\nTroubleshooting:")
        print("- Ensure ELM327 adapter is plugged into OBD-II port")
        print("- Check Bluetooth pairing")
        print("- Verify car is on (ignition)")
        return False

    print(f"✓ Connected: {obd.get_protocol_name()}")
    print(f"  Port: {obd.get_port_name()}")

    print("\nReading PIDs...")
    for i in range(5):
        data = obd.read_all_fast_pids()
        print(f"  Sample {i+1}: RPM={data.get('RPM', 'N/A')}, "
              f"Speed={data.get('SPEED', 'N/A')}, "
              f"Throttle={data.get('THROTTLE_POS', 'N/A')}")
        time.sleep(1)

    obd.disconnect()
    print("\n✓ OBD-II test passed!")
    return True


def test_accelerometer():
    """Test MPU6050 accelerometer."""
    print("\n" + "=" * 60)
    print("TESTING ACCELEROMETER (MPU6050)")
    print("=" * 60)

    config = load_config("sensor_config.json")
    accel_config = config.get('accelerometer', {})

    print("\nInitializing accelerometer...")
    accel = Accelerometer(accel_config, simulation_mode=False)

    if not accel.connect():
        print("✗ Failed to connect to MPU6050")
        print("\nTroubleshooting:")
        print("- Check I2C wiring: SDA=GPIO2, SCL=GPIO3")
        print("- Verify I2C is enabled: sudo raspi-config")
        print("- Test I2C detection: sudo i2cdetect -y 1")
        return False

    print("✓ Connected")

    print("\nReading acceleration data...")
    print("(Keep sensor still for accurate zero-point reading)\n")

    for i in range(10):
        data = accel.read_all()
        print(f"  Sample {i+1}:")
        print(f"    Longitudinal: {data['longitudinal_g']:+.3f}g")
        print(f"    Lateral:      {data['lateral_g']:+.3f}g")
        print(f"    Vertical:     {data['vertical_g']:+.3f}g")
        print(f"    Total:        {data['total_g']:.3f}g")
        time.sleep(0.5)

    print("\n✓ Accelerometer test passed!")
    print("\nNote: If values seem off, run calibration:")
    print("  python src/utils/calibration.py")
    return True


def test_gps():
    """Test NEO-6M GPS module."""
    print("\n" + "=" * 60)
    print("TESTING GPS MODULE (NEO-6M)")
    print("=" * 60)

    config = load_config("sensor_config.json")
    gps_config = config.get('gps', {})

    print("\nInitializing GPS...")
    gps = GPS(gps_config, simulation_mode=False)

    if not gps.connect():
        print("✗ Failed to connect to GPS")
        print("\nTroubleshooting:")
        print("- Check UART wiring: TX=GPIO14, RX=GPIO15")
        print("- Verify UART is enabled in /boot/config.txt")
        print("- Check gpsd is running: sudo systemctl status gpsd")
        return False

    print("✓ Connected to gpsd")

    print("\nWaiting for GPS fix (this may take 30-60 seconds)...")
    print("For best results, ensure clear sky view\n")

    start_time = time.time()
    timeout = 60

    while (time.time() - start_time) < timeout:
        data = gps.read()

        print(f"\r  Satellites: {data.get('satellites', 0)} | "
              f"Fix: {'VALID' if data.get('valid') else 'SEARCHING'}   ",
              end='', flush=True)

        if data.get('valid'):
            print("\n\n✓ GPS fix acquired!")
            print(f"  Position: {data['latitude']:.6f}, {data['longitude']:.6f}")
            print(f"  Altitude: {data['altitude_m']:.1f}m")
            print(f"  Speed: {data['speed_mph']:.1f} mph")
            print(f"  Satellites: {data['satellites']}")
            return True

        time.sleep(1)

    print("\n\n✗ GPS fix timeout")
    print("  GPS may need more time or better sky visibility")
    return False


def test_temperature():
    """Test DS18B20 temperature sensors."""
    print("\n" + "=" * 60)
    print("TESTING TEMPERATURE SENSORS (DS18B20)")
    print("=" * 60)

    config = load_config("sensor_config.json")
    temp_config = config.get('temperature', {})

    print("\nInitializing temperature sensors...")
    temp = TemperatureSensors(temp_config, simulation_mode=False)

    if not temp.connect():
        print("✗ Failed to find temperature sensors")
        print("\nTroubleshooting:")
        print("- Check 1-Wire wiring: Data=GPIO4 with 4.7kΩ pullup")
        print("- Verify 1-Wire is enabled: add 'dtoverlay=w1-gpio' to /boot/config.txt")
        print("- Check sensor IDs: ls /sys/bus/w1/devices/")
        return False

    sensor_count = temp.get_count()
    print(f"✓ Found {sensor_count} sensor(s)")

    if sensor_count == 0:
        print("\n✗ No sensors detected")
        return False

    print("\nSensor configuration:")
    for info in temp.get_sensor_info():
        print(f"  {info['id']}: {info['name']} ({info['location']})")

    print("\nReading temperatures...")
    for i in range(5):
        temps = temp.read_all()
        print(f"\n  Reading {i+1}:")
        for name, value in temps.items():
            if value:
                print(f"    {name}: {value:.1f}°F")
            else:
                print(f"    {name}: ERROR")
        time.sleep(1)

    # Check thresholds
    alerts = temp.check_thresholds()
    if alerts['critical']:
        print(f"\n⚠ CRITICAL: {', '.join(alerts['critical'])}")
    elif alerts['warnings']:
        print(f"\n⚠ WARNING: {', '.join(alerts['warnings'])}")

    print("\n✓ Temperature sensors test passed!")
    return True


def main():
    """Run all sensor tests."""
    print("=" * 60)
    print("BMW M3 DAQ SYSTEM - SENSOR TEST")
    print("=" * 60)
    print("\nThis script will test each sensor individually.")
    print("Make sure all sensors are connected before proceeding.\n")

    tests = [
        ("OBD-II", test_obd),
        ("Accelerometer", test_accelerometer),
        ("GPS", test_gps),
        ("Temperature", test_temperature)
    ]

    results = {}

    for name, test_func in tests:
        try:
            results[name] = test_func()
        except KeyboardInterrupt:
            print("\n\nTest interrupted by user")
            sys.exit(1)
        except Exception as e:
            logger.error(f"{name} test failed with exception: {e}")
            results[name] = False

        time.sleep(1)

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n✓ All tests passed! System is ready to log data.")
        print("\nNext steps:")
        print("1. Calibrate sensors: python src/utils/calibration.py")
        print("2. Start logging: python src/main.py")
        return 0
    else:
        print("\n✗ Some tests failed. Please check hardware connections.")
        print("See troubleshooting notes above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
