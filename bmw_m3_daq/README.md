# BMW M3 Data Acquisition System

A professional-grade vehicle data acquisition system built on Raspberry Pi for the 2001 BMW M3 (E46). Logs real-time vehicle performance data including OBD-II parameters, GPS coordinates, 3-axis acceleration, and temperature sensors.

![DAQ System](docs/images/system_overview.jpg)

## Features

### Data Collection
- **OBD-II Interface**: RPM, speed, throttle position, coolant temperature, intake temperature, MAF, engine load, timing advance, fuel trim, and more
- **3-Axis Accelerometer**: Longitudinal, lateral, and vertical g-forces with complementary filtering
- **GPS Tracking**: Position, speed, altitude, and heading with lap detection
- **Temperature Monitoring**: Engine oil, intake air, brake fluid, transmission, and ambient temperatures

### Real-Time Dashboard
- Web-based interface accessible from phone/tablet
- Live sensor data updates via WebSocket
- Gauges for RPM, speed, throttle, g-forces, and temperatures
- Connection status indicators

### Analysis Tools
- **Performance Metrics**: 0-60 mph time, 60-0 braking distance, quarter-mile time
- **Lap Time Analysis**: Automatic lap detection and comparison
- **Power Curve Estimation**: Calculate HP/torque from acceleration data
- **Data Visualization**: Time-series plots, G-G diagrams, GPS tracks, temperature graphs
- **Export Formats**: CSV, Excel, JSON, KML (Google Earth)

### System Features
- 50 Hz sampling rate
- Buffered CSV logging
- Automatic session management
- Sensor calibration tools
- Auto-start on boot (systemd service)
- Simulation mode for testing without hardware

## Hardware Requirements

### Core Components
- Raspberry Pi 4 (4GB recommended) - $55
- 32GB microSD card (Class 10) - $10
- ELM327 Bluetooth OBD-II adapter (v1.5 chip) - $20
- MPU6050 accelerometer/gyroscope module - $5
- NEO-6M GPS module - $12
- DS18B20 waterproof temperature sensors (5-pack) - $8
- 12V to 5V 3A USB converter - $8
- Breadboard + jumper wires - $10
- Project enclosure (weatherproof, 6"x4"x2") - $12
- Resistor kit (need 4.7kΩ for temp sensors) - $8

**Total Cost: ~$150**

### Wiring Connections

#### MPU6050 (Accelerometer) - I2C
```
MPU6050         Raspberry Pi
VCC      --->   3.3V (Pin 1)
GND      --->   Ground (Pin 6)
SCL      --->   GPIO 3 / SCL (Pin 5)
SDA      --->   GPIO 2 / SDA (Pin 3)
```

#### NEO-6M (GPS) - UART
```
NEO-6M          Raspberry Pi
VCC      --->   5V (Pin 2)
GND      --->   Ground (Pin 6)
TX       --->   GPIO 15 / RX (Pin 10)
RX       --->   GPIO 14 / TX (Pin 8)
```

#### DS18B20 (Temperature) - 1-Wire
```
DS18B20         Raspberry Pi
VCC (red) --->  3.3V (Pin 1)
GND (black)->   Ground (Pin 6)
Data (yellow)-> GPIO 4 (Pin 7) + 4.7kΩ pullup resistor to 3.3V
```

#### ELM327 (OBD-II)
- Plug into vehicle's OBD-II port (under steering wheel)
- Pair via Bluetooth with Raspberry Pi

#### Power Supply
- Tap into 12V accessory circuit (cigarette lighter fuse)
- Add inline 5A fuse
- Connect to 12V→5V converter
- USB power to Raspberry Pi

## Software Installation

### 1. Flash Raspberry Pi OS
```bash
# Download Raspberry Pi Imager
# Flash Raspberry Pi OS Lite (64-bit) to microSD card
# Enable SSH and configure WiFi in imager settings
```

### 2. Initial Pi Setup
```bash
# SSH into Pi
ssh pi@raspberrypi.local

# Update system
sudo apt update && sudo apt upgrade -y

# Clone repository (or copy files to Pi)
git clone <your-repo-url>
cd bmw_m3_daq
```

### 3. Run Setup Script
```bash
# Run automated setup (configures I2C, 1-Wire, UART, installs dependencies)
sudo ./scripts/setup.sh

# Reboot
sudo reboot
```

### 4. Test Sensors
```bash
cd bmw_m3_daq

# Test all sensors
python3 scripts/test_sensors.py

# Test individual sensors
python3 -m src.sensors.obd
python3 -m src.sensors.accelerometer
python3 -m src.sensors.gps
python3 -m src.sensors.temperature
```

### 5. Calibrate Sensors
```bash
# Run calibration wizard
python3 src/utils/calibration.py

# Follow prompts to:
# - Calibrate accelerometer zero point
# - Identify temperature sensor IDs
# - Set GPS coordinate offset
```

## Usage

### Start Data Logging
```bash
# Activate virtual environment
source venv/bin/activate

# Start logging
python src/main.py

# Data will be saved to data/sessions/session_YYYYMMDD_HHMMSS/
```

### Access Dashboard
```bash
# Start web dashboard
python src/dashboard/app.py

# Access from phone/tablet:
# http://<raspberry-pi-ip>:5000

# To find Pi's IP address:
hostname -I
```

### Analyze Data
```bash
# Generate performance report
python src/analysis/performance.py data/sessions/session_20231125_143022

# Create visualizations
python src/analysis/visualization.py data/sessions/session_20231125_143022

# Export to all formats
python src/utils/data_export.py data/sessions/session_20231125_143022

# List all sessions
python src/analysis/session.py list
```

### Auto-Start on Boot
```bash
# Install systemd service
sudo ./scripts/install_service.sh

# Control service
sudo systemctl start daq      # Start
sudo systemctl stop daq       # Stop
sudo systemctl status daq     # Check status
sudo journalctl -u daq -f     # View logs
```

## Project Structure

```
bmw_m3_daq/
├── config/                      # Configuration files
│   ├── vehicle_config.json      # Vehicle parameters (weight, gear ratios, etc.)
│   ├── sensor_config.json       # Sensor settings and calibration
│   └── system_config.json       # System-wide settings
├── src/
│   ├── main.py                  # Main logging application
│   ├── sensors/                 # Sensor interface modules
│   │   ├── obd.py               # OBD-II interface
│   │   ├── accelerometer.py     # MPU6050 accelerometer
│   │   ├── gps.py               # GPS module
│   │   └── temperature.py       # DS18B20 temperature sensors
│   ├── dashboard/               # Web dashboard
│   │   ├── app.py               # Flask application
│   │   ├── templates/           # HTML templates
│   │   └── static/              # CSS/JS assets
│   ├── analysis/                # Data analysis tools
│   │   ├── performance.py       # Performance calculations
│   │   ├── visualization.py     # Plotting functions
│   │   └── session.py           # Session management
│   └── utils/                   # Utility scripts
│       ├── calibration.py       # Sensor calibration
│       └── data_export.py       # Data export tools
├── scripts/
│   ├── setup.sh                 # Initial setup script
│   ├── test_sensors.py          # Sensor testing
│   ├── install_service.sh       # Install systemd service
│   └── systemd/
│       └── daq.service          # Systemd service file
├── data/
│   └── sessions/                # Logged session data
└── logs/                        # Application logs
```

## Configuration

### Vehicle Parameters
Edit `config/vehicle_config.json` to match your vehicle:
- Weight, weight distribution
- Engine specifications
- Transmission gear ratios
- Wheel/tire dimensions
- Aerodynamic properties

### Sensor Calibration
Edit `config/sensor_config.json` to adjust:
- Accelerometer offsets and rotation matrix
- Temperature sensor IDs and thresholds
- GPS coordinate offset
- OBD-II PIDs to log

### System Settings
Edit `config/system_config.json` to configure:
- Sampling rates
- File buffer sizes
- Dashboard settings
- Logging levels
- Data retention

## Data Format

### CSV Output
Each session produces a `data.csv` file with columns:
```
timestamp, elapsed_time, rpm, speed_mph, throttle_pos, coolant_temp_f,
intake_temp_f, maf_gps, engine_load, timing_advance, fuel_trim_short,
fuel_trim_long, accel_long_g, accel_lat_g, accel_vert_g, accel_total_g,
pitch_deg, roll_deg, yaw_rate_dps, gps_lat, gps_lon, gps_alt_m,
gps_speed_mph, gps_heading, gps_satellites, gps_valid, temp_oil_f,
temp_intake_f, temp_brake_f, temp_trans_f, temp_ambient_f
```

### Session Summary
Each session includes a `session_summary.json` with:
- Start/end timestamps
- Duration and sample count
- Error counts
- Vehicle configuration

## Analysis Examples

### Calculate 0-60 Time
```python
from analysis import PerformanceAnalyzer

analyzer = PerformanceAnalyzer("data/sessions/session_20231125_143022")
results = analyzer.calculate_zero_to_sixty()

print(f"0-60 mph: {results['time_seconds']:.2f} seconds")
print(f"Average g-force: {results['avg_g_force']:.2f}g")
```

### Plot GPS Track
```python
from analysis import DataVisualizer

viz = DataVisualizer("data/sessions/session_20231125_143022")
viz.plot_gps_track(save=True)  # Saves to plots/gps_track.png
```

### Detect Lap Times
```python
from analysis import PerformanceAnalyzer

analyzer = PerformanceAnalyzer("data/sessions/session_20231125_143022")
laps = analyzer.detect_laps()

for lap in laps:
    print(f"Lap {lap['lap_number']}: {lap['lap_time_seconds']:.2f}s")
```

## Troubleshooting

### OBD-II Not Connecting
- Ensure adapter is plugged into OBD-II port
- Verify car is on (ignition)
- Check Bluetooth pairing: `bluetoothctl`
- Try different ELM327 adapter (some are incompatible)

### Accelerometer Not Found
- Verify I2C is enabled: `sudo raspi-config` → Interface Options → I2C
- Check wiring connections
- Test I2C detection: `sudo i2cdetect -y 1` (should show device at 0x68)

### GPS No Fix
- Ensure clear sky view (GPS needs line-of-sight to satellites)
- Allow 30-60 seconds for initial fix (cold start)
- Check gpsd is running: `sudo systemctl status gpsd`
- Verify UART is enabled in `/boot/config.txt`

### Temperature Sensors Not Found
- Verify 1-Wire is enabled: add `dtoverlay=w1-gpio` to `/boot/config.txt`
- Check 4.7kΩ pullup resistor is installed
- List detected sensors: `ls /sys/bus/w1/devices/`
- Update sensor IDs in `config/sensor_config.json`

### Dashboard Not Accessible
- Check Flask is running: `python src/dashboard/app.py`
- Find Pi's IP: `hostname -I`
- Try accessing from Pi's browser first
- Check firewall settings

## Performance Tips

- Use Class 10 or better microSD card for reliable write performance
- Set `csv_buffer_size` in config to balance memory vs. write frequency
- Enable file compression for old sessions to save space
- Monitor disk space: sessions can be 10-50 MB each

## Safety Notes

⚠️ **Important Safety Guidelines**

- NEVER operate the dashboard while driving
- Mount all components securely to prevent movement
- Ensure wiring doesn't interfere with pedals or steering
- Use proper fusing on all power connections
- Do not modify safety-critical vehicle systems
- Test thoroughly before track use

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please open an issue or pull request.

## Acknowledgments

- [python-obd](https://github.com/brendan-w/python-OBD) for OBD-II interface
- [Adafruit CircuitPython](https://github.com/adafruit/Adafruit_CircuitPython_MPU6050) for MPU6050 library
- BMW M3 (E46) community for specifications and inspiration

## Support

For issues, questions, or suggestions:
- Create an issue on GitHub
- Contribute improvements via pull request

## Photos

[Add photos of your installation here]

## Changelog

### v1.0.0 (2024-01-01)
- Initial release
- OBD-II, GPS, accelerometer, temperature sensor support
- Web dashboard
- Performance analysis tools
- Data visualization

---

Built with ❤️ for the BMW M3 E46

**Not affiliated with BMW AG**
