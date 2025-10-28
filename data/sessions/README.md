# DAQ Sessions

This directory contains logged data acquisition sessions from track days and test drives.

## Session Structure

Each session is stored in a timestamped directory:
```
session_YYYYMMDD_HHMMSS/
├── data.csv                    # Raw sensor data
├── session_summary.json        # Session metadata
├── performance_report.json     # Performance analysis results
├── data.xlsx                   # Excel export (multi-sheet)
├── track.kml                   # GPS track for Google Earth
├── plots/                      # Visualization graphs
│   ├── rpm_and_speed.png
│   ├── acceleration.png
│   ├── gg_diagram.png
│   ├── gps_track.png
│   ├── temperatures.png
│   └── throttle_and_load.png
└── NOTES.txt                   # Session notes (optional)
```

## Available Sessions

### session_20240315_143022
- **Date:** March 15, 2024
- **Location:** Buttonwillow Raceway Park (Config 13CW)
- **Duration:** 5 minutes (4 laps)
- **Best lap:** 87.3 seconds
- **Max speed:** 135 mph
- **Max lateral G:** 1.13g
- **Weather:** Clear, 78°F

## Analyzing Sessions

To analyze a session:
```bash
# Generate performance report and visualizations
python scripts/analyze_session.py data/sessions/session_20240315_143022

# Or use the analysis tools directly
python src/analysis/performance.py data/sessions/session_20240315_143022
python src/analysis/visualization.py data/sessions/session_20240315_143022
```

## Managing Sessions

List all sessions:
```bash
python src/analysis/session.py list
```

Load session data:
```bash
python src/analysis/session.py load session_20240315_143022
```

Compare two sessions:
```bash
python -c "
from src.analysis import SessionManager
mgr = SessionManager()
comparison = mgr.compare_sessions('session1', 'session2')
print(comparison)
"
```

## Data Format

CSV columns include:
- **Time:** timestamp, elapsed_time
- **OBD-II:** rpm, speed_mph, throttle_pos, coolant_temp_f, intake_temp_f, maf_gps, engine_load, timing_advance, fuel_trim_short, fuel_trim_long
- **Acceleration:** accel_long_g, accel_lat_g, accel_vert_g, accel_total_g, pitch_deg, roll_deg, yaw_rate_dps
- **GPS:** gps_lat, gps_lon, gps_alt_m, gps_speed_mph, gps_heading, gps_satellites, gps_valid
- **Temperature:** temp_oil_f, temp_intake_f, temp_brake_f, temp_trans_f, temp_ambient_f

## Storage Guidelines

- Each session is typically 2-5 MB (5 minutes at 50 Hz)
- Keep at least 2 GB free space on SD card
- Archive old sessions to external storage
- Sessions are automatically compressed if enabled in system_config.json

## Tips

- Add NOTES.txt to each session for context
- Export to Excel for sharing with crew/friends
- Open track.kml in Google Earth to visualize driving line
- Compare lap times across different sessions to track improvements
