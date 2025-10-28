# Quick Start Guide

Get up and running with the BMW M3 DAQ system in 30 minutes.

## Prerequisites

- Raspberry Pi 4 with Raspberry Pi OS installed
- All hardware connected (see README for wiring)
- Vehicle with OBD-II port
- SSH access to Pi

## Step 1: Install System (5 minutes)

```bash
# SSH into Pi
ssh pi@raspberrypi.local

# Clone repository or copy files to Pi
git clone <your-repo-url>
cd bmw_m3_daq

# Run setup script
sudo ./scripts/setup.sh

# Reboot
sudo reboot
```

## Step 2: Test Hardware (10 minutes)

```bash
cd bmw_m3_daq

# Test all sensors
python3 scripts/test_sensors.py
```

**Expected Results:**
- ✓ OBD-II: Connected, reading RPM/speed/throttle
- ✓ Accelerometer: Reading ~0g longitudinal/lateral, ~1g vertical
- ✓ GPS: Valid fix with 4+ satellites
- ✓ Temperature: Reading 5 sensors

**Troubleshooting:**
If any sensor fails, see the troubleshooting section in test output.

## Step 3: Calibrate Sensors (5 minutes)

```bash
# Run calibration for accelerometer
python3 src/utils/calibration.py
```

Follow prompts:
1. Park on level ground
2. Engine off, no movement
3. Collect calibration samples

## Step 4: Start Logging (1 minute)

```bash
# Method 1: Manual start
source venv/bin/activate
python src/main.py

# Method 2: Auto-start on boot
sudo ./scripts/install_service.sh
sudo systemctl start daq
```

Data will be saved to `data/sessions/session_YYYYMMDD_HHMMSS/`

## Step 5: View Dashboard (5 minutes)

```bash
# Start dashboard
python src/dashboard/app.py
```

Open on phone/tablet:
```
http://<raspberry-pi-ip>:5000
```

You should see:
- Live RPM, speed, throttle gauges
- G-force readings
- GPS status
- Temperature values

## Step 6: Analyze Data (5 minutes)

After logging a drive session:

```bash
# Find latest session
python src/analysis/session.py latest

# Generate performance report
python src/analysis/performance.py data/sessions/session_20231125_143022

# Create visualizations
python src/analysis/visualization.py data/sessions/session_20231125_143022

# Export to Excel
python src/utils/data_export.py data/sessions/session_20231125_143022
```

## Common Commands

```bash
# Start/stop logging service
sudo systemctl start daq
sudo systemctl stop daq
sudo systemctl status daq

# View live logs
sudo journalctl -u daq -f

# List all sessions
python src/analysis/session.py list

# Test individual sensor
python3 -m src.sensors.obd
python3 -m src.sensors.accelerometer
python3 -m src.sensors.gps
python3 -m src.sensors.temperature
```

## Next Steps

1. **Mount in Vehicle**: Secure Pi and sensors in weatherproof enclosure
2. **Power Setup**: Wire 12V→5V converter to accessory circuit
3. **Dashboard Access**: Set up Pi WiFi hotspot for phone access
4. **Track Day**: Collect data and analyze performance!

## Tips

- Always wait 30-60s for GPS fix before starting drive
- Check dashboard connection status indicators
- Monitor temperatures during spirited driving
- Export data after each session for backup

## Quick Troubleshooting

**No OBD-II data?**
- Check car is on (ignition)
- Verify Bluetooth pairing

**GPS not working?**
- Ensure clear sky view
- Check gpsd: `sudo systemctl status gpsd`

**Temperatures all showing error?**
- Verify 1-Wire enabled in `/boot/config.txt`
- Check 4.7kΩ pullup resistor

**Dashboard won't load?**
- Check Flask is running
- Find IP: `hostname -I`

For detailed troubleshooting, see full README.

---

**Ready to log data? Go for a drive and come back to analyze your results!**
