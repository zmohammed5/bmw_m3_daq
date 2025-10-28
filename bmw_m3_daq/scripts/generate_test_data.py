#!/usr/bin/env python3
"""
Generate Test Data

Creates a simulated DAQ session with realistic data for testing
analysis and visualization tools without hardware.
"""

import sys
import csv
import json
import math
import random
from pathlib import Path
from datetime import datetime
import numpy as np

def generate_session(duration_seconds=300, sample_rate_hz=50):
    """
    Generate simulated DAQ session data.

    Args:
        duration_seconds: Length of session in seconds
        sample_rate_hz: Sampling rate

    Returns:
        List of data dictionaries
    """
    print(f"Generating {duration_seconds}s of data at {sample_rate_hz}Hz...")

    data = []
    num_samples = int(duration_seconds * sample_rate_hz)
    dt = 1.0 / sample_rate_hz

    # Simulation state
    speed = 0.0  # mph
    rpm = 800.0
    position = 0.0  # meters
    heading = 0.0  # degrees
    lap_start_lat = 37.7749
    lap_start_lon = -122.4194

    # Track radius for circular track
    track_radius_m = 200
    track_circumference_m = 2 * math.pi * track_radius_m

    for i in range(num_samples):
        elapsed_time = i * dt

        # Driving scenario simulation
        # 0-60s: Acceleration run
        # 60-90s: Steady speed
        # 90-120s: Braking
        # 120-300s: Track lapping

        phase = elapsed_time % 120

        if phase < 15:  # Acceleration
            throttle = 100
            accel_long = 0.35 + random.uniform(-0.05, 0.05)
            speed += accel_long * 22 * dt  # ~22 mph per g per second
            rpm = min(8000, 800 + (speed / 155) * 7200 + random.uniform(-100, 100))

        elif phase < 25:  # Coasting
            throttle = 30
            accel_long = random.uniform(-0.1, 0.0)
            speed += accel_long * 22 * dt
            rpm = 800 + (speed / 155) * 7200

        elif phase < 35:  # Braking
            throttle = 0
            accel_long = -0.5 + random.uniform(-0.1, 0.1)
            speed = max(0, speed + accel_long * 22 * dt)
            rpm = max(800, 800 + (speed / 155) * 7200)

        else:  # Track lapping
            throttle = 60 + random.uniform(-10, 10)
            speed = 55 + 20 * math.sin(elapsed_time / 10) + random.uniform(-3, 3)
            rpm = 3000 + 2000 * math.sin(elapsed_time / 8)

            # Cornering lateral g-force
            corner_phase = (elapsed_time / 10) % (2 * math.pi)
            accel_lat = 0.8 * math.sin(corner_phase) + random.uniform(-0.1, 0.1)
            accel_long = 0.2 * math.cos(corner_phase) + random.uniform(-0.1, 0.1)

        # Keep values in realistic bounds
        speed = max(0, min(155, speed))
        rpm = max(800, min(8000, rpm))
        throttle = max(0, min(100, throttle))

        # Calculate position (GPS simulation)
        # Circular track pattern
        angular_velocity = speed * 0.44704 / track_radius_m  # rad/s
        heading = (heading + math.degrees(angular_velocity * dt)) % 360

        # Position on circle
        angle_rad = math.radians(heading)
        lat = lap_start_lat + (track_radius_m / 111000) * math.cos(angle_rad)
        lon = lap_start_lon + (track_radius_m / (111000 * math.cos(math.radians(lap_start_lat)))) * math.sin(angle_rad)

        # Other g-forces
        if phase < 35:
            accel_lat = random.uniform(-0.1, 0.1)

        accel_vert = random.uniform(-0.2, 0.2)  # Road bumps
        accel_total = math.sqrt(accel_long**2 + accel_lat**2 + accel_vert**2)

        # Temperatures (gradually increase)
        temp_oil = 190 + (elapsed_time / duration_seconds) * 30 + random.uniform(-3, 3)
        temp_intake = 80 + (elapsed_time / duration_seconds) * 30 + random.uniform(-2, 2)
        temp_brake = 180 + (elapsed_time / duration_seconds) * 40 + random.uniform(-5, 5)
        temp_trans = 195 + (elapsed_time / duration_seconds) * 25 + random.uniform(-3, 3)
        temp_ambient = 75 + random.uniform(-1, 1)

        # Create data sample
        sample = {
            'timestamp': datetime.now().isoformat(),
            'elapsed_time': round(elapsed_time, 3),
            'rpm': round(rpm, 0),
            'speed_mph': round(speed, 1),
            'throttle_pos': round(throttle, 1),
            'coolant_temp_f': round(185 + random.uniform(-2, 5), 1),
            'intake_temp_f': round(temp_intake, 1),
            'maf_gps': round(50 + (rpm / 100), 1),
            'engine_load': round(throttle * 0.8, 1),
            'timing_advance': round(15 + random.uniform(-2, 5), 1),
            'fuel_trim_short': round(random.uniform(-3, 3), 1),
            'fuel_trim_long': round(random.uniform(-2, 2), 1),
            'accel_long_g': round(accel_long, 3),
            'accel_lat_g': round(accel_lat, 3),
            'accel_vert_g': round(accel_vert, 3),
            'accel_total_g': round(accel_total, 3),
            'pitch_deg': round(accel_long * 2 + random.uniform(-0.5, 0.5), 2),
            'roll_deg': round(accel_lat * 2 + random.uniform(-0.5, 0.5), 2),
            'yaw_rate_dps': round(random.uniform(-5, 5), 2),
            'gps_lat': round(lat, 6),
            'gps_lon': round(lon, 6),
            'gps_alt_m': round(50 + random.uniform(-5, 5), 1),
            'gps_speed_mph': round(speed + random.uniform(-2, 2), 1),
            'gps_heading': round(heading, 1),
            'gps_satellites': random.randint(6, 10),
            'gps_valid': True,
            'temp_oil_f': round(temp_oil, 1),
            'temp_intake_f': round(temp_intake, 1),
            'temp_brake_f': round(temp_brake, 1),
            'temp_trans_f': round(temp_trans, 1),
            'temp_ambient_f': round(temp_ambient, 1)
        }

        data.append(sample)

        if (i + 1) % 1000 == 0:
            print(f"  Generated {i+1}/{num_samples} samples...")

    print(f"✓ Generated {len(data)} samples")
    return data


def save_session(data, output_dir=None):
    """
    Save generated data as a session.

    Args:
        data: List of data dictionaries
        output_dir: Output directory (default: create new session dir)
    """
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(__file__).parent.parent / "data" / "sessions" / f"session_{timestamp}_simulated"

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save CSV
    csv_path = output_dir / "data.csv"
    print(f"\nSaving to {csv_path}...")

    with open(csv_path, 'w', newline='') as f:
        if data:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

    print(f"✓ Saved {len(data)} samples to CSV")

    # Create session summary
    summary = {
        'session_start': data[0]['timestamp'] if data else None,
        'session_end': data[-1]['timestamp'] if data else None,
        'duration_seconds': data[-1]['elapsed_time'] if data else 0,
        'samples_collected': len(data),
        'errors': {'obd': 0, 'accelerometer': 0, 'gps': 0, 'temperature': 0},
        'vehicle': {
            'year': 2001,
            'make': 'BMW',
            'model': 'M3',
            'variant': 'E46'
        },
        'simulation_mode': True
    }

    summary_path = output_dir / "session_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"✓ Saved session summary")
    print(f"\nSession created: {output_dir}")
    print("\nYou can now analyze this session:")
    print(f"  python scripts/analyze_session.py {output_dir}")

    return output_dir


def main():
    """Main entry point."""
    print("=" * 60)
    print("BMW M3 DAQ - Test Data Generator")
    print("=" * 60)
    print()

    # Parse arguments
    duration = 300
    sample_rate = 50

    if len(sys.argv) > 1:
        duration = int(sys.argv[1])
    if len(sys.argv) > 2:
        sample_rate = int(sys.argv[2])

    print(f"Configuration:")
    print(f"  Duration: {duration} seconds ({duration/60:.1f} minutes)")
    print(f"  Sample rate: {sample_rate} Hz")
    print(f"  Total samples: {duration * sample_rate:,}")
    print()

    # Generate data
    data = generate_session(duration_seconds=duration, sample_rate_hz=sample_rate)

    # Save session
    session_dir = save_session(data)

    return 0


if __name__ == "__main__":
    sys.exit(main())
