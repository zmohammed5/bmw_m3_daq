"""
Performance Analysis Module
Calculate performance metrics from logged data: 0-60, lap times, max g-forces, power curves.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PerformanceAnalyzer:
    """
    Analyze vehicle performance from logged data.

    Calculates acceleration times, braking distances, lap times,
    and estimates power/torque curves.
    """

    def __init__(self, session_dir: str, vehicle_config: Dict = None):
        """
        Initialize performance analyzer.

        Args:
            session_dir: Path to session directory containing data.csv
            vehicle_config: Vehicle configuration dictionary
        """
        self.session_dir = Path(session_dir)
        self.csv_path = self.session_dir / "data.csv"

        if not self.csv_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.csv_path}")

        # Load data
        self.data = pd.read_csv(self.csv_path)
        logger.info(f"Loaded {len(self.data)} samples from {self.csv_path}")

        # Vehicle parameters
        self.vehicle = vehicle_config or {}
        self.vehicle_weight_kg = self.vehicle.get('weight_kg', 1549)
        self.vehicle_weight_lbs = self.vehicle.get('weight_lbs', 3415)

    def calculate_zero_to_sixty(self) -> Dict[str, float]:
        """
        Calculate 0-60 mph acceleration time.

        Uses both OBD speed and accelerometer data for accuracy.

        Returns:
            Dictionary with 0-60 results
        """
        if 'speed_mph' not in self.data.columns:
            logger.error("Speed data not available")
            return {}

        results = {}

        # Find all acceleration runs (speed goes from <10 mph to >60 mph)
        runs = []
        in_run = False
        run_start_idx = None

        for idx, row in self.data.iterrows():
            speed = row.get('speed_mph', 0)

            if not in_run and speed < 10:
                # Potential start of run
                run_start_idx = idx
                in_run = True
            elif in_run and speed >= 60:
                # End of run
                run_duration = row['elapsed_time'] - self.data.loc[run_start_idx, 'elapsed_time']
                runs.append({
                    'start_idx': run_start_idx,
                    'end_idx': idx,
                    'duration': run_duration,
                    'start_time': self.data.loc[run_start_idx, 'elapsed_time'],
                    'end_time': row['elapsed_time']
                })
                in_run = False
                logger.info(f"Found 0-60 run: {run_duration:.2f}s")

        if not runs:
            logger.warning("No complete 0-60 runs found in data")
            return {'found': False}

        # Use fastest run
        fastest_run = min(runs, key=lambda x: x['duration'])

        results = {
            'found': True,
            'time_seconds': fastest_run['duration'],
            'num_runs': len(runs),
            'all_times': [r['duration'] for r in runs]
        }

        # Calculate average g-force during run if available
        if 'accel_long_g' in self.data.columns:
            run_data = self.data.iloc[fastest_run['start_idx']:fastest_run['end_idx']]
            results['avg_g_force'] = run_data['accel_long_g'].mean()
            results['max_g_force'] = run_data['accel_long_g'].max()

        return results

    def calculate_sixty_to_zero(self) -> Dict[str, float]:
        """
        Calculate 60-0 mph braking distance and time.

        Returns:
            Dictionary with braking results
        """
        if 'speed_mph' not in self.data.columns:
            logger.error("Speed data not available")
            return {}

        results = {}

        # Find braking runs (speed goes from >60 mph to <5 mph)
        runs = []
        in_run = False
        run_start_idx = None

        for idx, row in self.data.iterrows():
            speed = row.get('speed_mph', 0)

            if not in_run and speed > 60:
                run_start_idx = idx
                in_run = True
            elif in_run and speed < 5:
                run_duration = row['elapsed_time'] - self.data.loc[run_start_idx, 'elapsed_time']
                runs.append({
                    'start_idx': run_start_idx,
                    'end_idx': idx,
                    'duration': run_duration
                })
                in_run = False
                logger.info(f"Found 60-0 braking run: {run_duration:.2f}s")

        if not runs:
            logger.warning("No complete 60-0 braking runs found")
            return {'found': False}

        # Use shortest (fastest) braking run
        fastest_run = min(runs, key=lambda x: x['duration'])

        results = {
            'found': True,
            'time_seconds': fastest_run['duration'],
            'num_runs': len(runs)
        }

        # Calculate braking g-force and distance
        if 'accel_long_g' in self.data.columns:
            run_data = self.data.iloc[fastest_run['start_idx']:fastest_run['end_idx']]
            results['avg_g_force'] = abs(run_data['accel_long_g'].mean())
            results['max_g_force'] = abs(run_data['accel_long_g'].min())

            # Estimate braking distance (using average deceleration)
            # d = v²/(2*a), where v = 60 mph = 26.82 m/s
            avg_decel_mps2 = abs(results['avg_g_force']) * 9.80665
            if avg_decel_mps2 > 0:
                distance_m = (26.82 ** 2) / (2 * avg_decel_mps2)
                results['distance_meters'] = distance_m
                results['distance_feet'] = distance_m * 3.28084

        return results

    def calculate_quarter_mile(self) -> Dict[str, float]:
        """
        Calculate quarter mile time and trap speed.

        Returns:
            Dictionary with quarter mile results
        """
        if 'gps_lat' not in self.data.columns or 'gps_lon' not in self.data.columns:
            logger.error("GPS data not available for distance calculation")
            return {}

        # Calculate distance traveled between each point
        self.data['distance_m'] = 0.0

        for i in range(1, len(self.data)):
            lat1 = self.data.loc[i-1, 'gps_lat']
            lon1 = self.data.loc[i-1, 'gps_lon']
            lat2 = self.data.loc[i, 'gps_lat']
            lon2 = self.data.loc[i, 'gps_lon']

            distance = self._haversine_distance(lat1, lon1, lat2, lon2)
            self.data.loc[i, 'distance_m'] = distance

        # Calculate cumulative distance
        self.data['cumulative_distance_m'] = self.data['distance_m'].cumsum()

        # Find quarter mile runs (402.336 meters)
        quarter_mile_m = 402.336
        runs = []

        for idx in range(len(self.data)):
            speed = self.data.loc[idx, 'speed_mph']

            # Look for start of run (low speed)
            if speed < 10:
                # Find where cumulative distance reaches quarter mile from this point
                start_distance = self.data.loc[idx, 'cumulative_distance_m']
                target_distance = start_distance + quarter_mile_m

                # Find end point
                end_data = self.data[self.data['cumulative_distance_m'] >= target_distance]
                if len(end_data) > 0:
                    end_idx = end_data.index[0]
                    duration = self.data.loc[end_idx, 'elapsed_time'] - self.data.loc[idx, 'elapsed_time']
                    trap_speed = self.data.loc[end_idx, 'speed_mph']

                    if duration < 30:  # Reasonable quarter mile time
                        runs.append({
                            'duration': duration,
                            'trap_speed': trap_speed
                        })

        if not runs:
            logger.warning("No quarter mile runs found")
            return {'found': False}

        fastest_run = min(runs, key=lambda x: x['duration'])

        return {
            'found': True,
            'time_seconds': fastest_run['duration'],
            'trap_speed_mph': fastest_run['trap_speed']
        }

    def calculate_max_values(self) -> Dict[str, float]:
        """
        Calculate maximum values for all metrics.

        Returns:
            Dictionary with max values
        """
        max_vals = {}

        # Speed
        if 'speed_mph' in self.data.columns:
            max_vals['max_speed_mph'] = self.data['speed_mph'].max()

        # RPM
        if 'rpm' in self.data.columns:
            max_vals['max_rpm'] = self.data['rpm'].max()

        # G-forces
        if 'accel_long_g' in self.data.columns:
            max_vals['max_accel_g'] = self.data['accel_long_g'].max()
            max_vals['max_braking_g'] = abs(self.data['accel_long_g'].min())

        if 'accel_lat_g' in self.data.columns:
            max_vals['max_lateral_g'] = self.data['accel_lat_g'].abs().max()

        if 'accel_total_g' in self.data.columns:
            max_vals['max_total_g'] = self.data['accel_total_g'].max()

        # Temperatures
        temp_cols = [col for col in self.data.columns if 'temp_' in col]
        for col in temp_cols:
            max_vals[f'{col}_max'] = self.data[col].max()

        return max_vals

    def estimate_power_curve(self) -> pd.DataFrame:
        """
        Estimate power and torque curves from acceleration data.

        Uses F = ma and power = force × velocity to estimate HP.

        Returns:
            DataFrame with RPM, estimated HP, and estimated torque
        """
        if 'rpm' not in self.data.columns or 'accel_long_g' not in self.data.columns:
            logger.error("RPM and acceleration data required for power estimation")
            return pd.DataFrame()

        # Filter data during acceleration (positive g-force, increasing RPM)
        accel_data = self.data[
            (self.data['accel_long_g'] > 0.1) &
            (self.data['rpm'] > 1000)
        ].copy()

        if len(accel_data) == 0:
            logger.warning("No suitable acceleration data for power estimation")
            return pd.DataFrame()

        # Calculate force = mass × acceleration
        mass_kg = self.vehicle_weight_kg
        accel_data['force_n'] = mass_kg * accel_data['accel_long_g'] * 9.80665

        # Calculate velocity (m/s) from speed
        accel_data['velocity_mps'] = accel_data['speed_mph'] * 0.44704

        # Calculate power = force × velocity (in Watts)
        accel_data['power_w'] = accel_data['force_n'] * accel_data['velocity_mps']

        # Convert to horsepower
        accel_data['power_hp'] = accel_data['power_w'] / 745.7

        # Calculate torque = power / angular_velocity
        # Torque (lb-ft) = (HP × 5252) / RPM
        accel_data['torque_lbft'] = (accel_data['power_hp'] * 5252) / accel_data['rpm']

        # Group by RPM bins and average
        rpm_bins = np.arange(1000, 8500, 500)
        accel_data['rpm_bin'] = pd.cut(accel_data['rpm'], bins=rpm_bins)

        power_curve = accel_data.groupby('rpm_bin').agg({
            'rpm': 'mean',
            'power_hp': 'mean',
            'torque_lbft': 'mean'
        }).dropna()

        return power_curve

    def detect_laps(self, start_lat: float = None, start_lon: float = None, threshold_m: float = 50) -> List[Dict]:
        """
        Detect laps from GPS data.

        Args:
            start_lat: Start/finish line latitude
            start_lon: Start/finish line longitude
            threshold_m: Distance threshold to consider crossing start line

        Returns:
            List of lap dictionaries with times and metadata
        """
        if 'gps_lat' not in self.data.columns or 'gps_lon' not in self.data.columns:
            logger.error("GPS data not available")
            return []

        # If no start position specified, use first valid GPS point
        if start_lat is None or start_lon is None:
            valid_gps = self.data[self.data['gps_valid'] == True]
            if len(valid_gps) == 0:
                logger.error("No valid GPS data")
                return []

            start_lat = valid_gps.iloc[0]['gps_lat']
            start_lon = valid_gps.iloc[0]['gps_lon']

        logger.info(f"Detecting laps using start position: {start_lat:.6f}, {start_lon:.6f}")

        # Calculate distance from start line for each point
        distances = []
        for _, row in self.data.iterrows():
            if row.get('gps_valid', False):
                dist = self._haversine_distance(start_lat, start_lon, row['gps_lat'], row['gps_lon'])
                distances.append(dist)
            else:
                distances.append(999999)  # Invalid

        self.data['distance_from_start'] = distances

        # Find crossings (distance < threshold)
        crossings = []
        for idx in range(1, len(self.data)):
            if (self.data.loc[idx, 'distance_from_start'] < threshold_m and
                self.data.loc[idx-1, 'distance_from_start'] >= threshold_m):
                crossings.append(idx)

        if len(crossings) < 2:
            logger.warning(f"Only {len(crossings)} start line crossings found - need at least 2 for lap time")
            return []

        # Calculate lap times
        laps = []
        for i in range(len(crossings) - 1):
            start_idx = crossings[i]
            end_idx = crossings[i + 1]

            lap_time = self.data.loc[end_idx, 'elapsed_time'] - self.data.loc[start_idx, 'elapsed_time']
            lap_data = self.data.iloc[start_idx:end_idx]

            laps.append({
                'lap_number': i + 1,
                'start_idx': start_idx,
                'end_idx': end_idx,
                'lap_time_seconds': lap_time,
                'max_speed_mph': lap_data['speed_mph'].max() if 'speed_mph' in lap_data.columns else 0,
                'avg_speed_mph': lap_data['speed_mph'].mean() if 'speed_mph' in lap_data.columns else 0,
                'max_g': lap_data['accel_total_g'].max() if 'accel_total_g' in lap_data.columns else 0
            })

            logger.info(f"Lap {i+1}: {lap_time:.2f}s")

        return laps

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two GPS coordinates using Haversine formula.

        Returns:
            Distance in meters
        """
        from math import radians, sin, cos, sqrt, asin

        # Convert to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))

        # Earth radius in meters
        r = 6371000

        return c * r

    def generate_report(self) -> Dict:
        """
        Generate comprehensive performance report.

        Returns:
            Dictionary with all performance metrics
        """
        logger.info("Generating performance report...")

        report = {
            'session_info': {
                'total_samples': len(self.data),
                'duration_seconds': self.data['elapsed_time'].max() if 'elapsed_time' in self.data.columns else 0
            }
        }

        # Calculate all metrics
        report['zero_to_sixty'] = self.calculate_zero_to_sixty()
        report['sixty_to_zero'] = self.calculate_sixty_to_zero()
        report['quarter_mile'] = self.calculate_quarter_mile()
        report['max_values'] = self.calculate_max_values()

        # Try to detect laps
        laps = self.detect_laps()
        if laps:
            report['laps'] = {
                'num_laps': len(laps),
                'best_lap_time': min(lap['lap_time_seconds'] for lap in laps),
                'all_laps': laps
            }

        return report


if __name__ == "__main__":
    import sys
    import json

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python performance.py <session_directory>")
        sys.exit(1)

    session_dir = sys.argv[1]

    # Load vehicle config if available
    vehicle_config_path = Path(session_dir).parent.parent / "config" / "vehicle_config.json"
    vehicle_config = {}
    if vehicle_config_path.exists():
        with open(vehicle_config_path) as f:
            config_data = json.load(f)
            vehicle_config = config_data.get('vehicle', {})

    analyzer = PerformanceAnalyzer(session_dir, vehicle_config)
    report = analyzer.generate_report()

    print("\n" + "=" * 60)
    print("PERFORMANCE ANALYSIS REPORT")
    print("=" * 60)
    print(json.dumps(report, indent=2))
