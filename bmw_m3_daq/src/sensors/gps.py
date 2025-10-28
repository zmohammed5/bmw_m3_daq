"""
GPS Module
Handles NEO-6M GPS module for position, speed, and track logging.
"""

import logging
import time
import math
from typing import Dict, Optional, Tuple, Any
import random

logger = logging.getLogger(__name__)

try:
    from gpsdclient import GPSDClient
    HAS_GPS = True
except ImportError:
    HAS_GPS = False
    logger.warning("GPS libraries not available - will run in simulation mode")


class GPS:
    """
    Interface for NEO-6M GPS module via gpsd daemon.

    Provides position, speed, altitude, and track logging with
    lap detection and coordinate smoothing.
    """

    # Earth radius in meters (for distance calculations)
    EARTH_RADIUS = 6371000

    def __init__(self, config: Dict[str, Any], simulation_mode: bool = False):
        """
        Initialize GPS interface.

        Args:
            config: Configuration dictionary with GPS settings
            simulation_mode: If True, generate fake data for testing
        """
        self.config = config
        self.simulation_mode = simulation_mode or not HAS_GPS
        self.client = None
        self.connected = False

        # Coordinate offset for privacy/calibration
        self.coord_offset = (
            config.get('coordinate_offset', {}).get('latitude', 0.0),
            config.get('coordinate_offset', {}).get('longitude', 0.0)
        )

        # Minimum satellites for valid fix
        self.min_satellites = config.get('min_satellites', 4)

        # Track detection
        self.track_start_pos: Optional[Tuple[float, float]] = None
        self.track_threshold_meters = 50  # Distance to consider "same location"

        # Simulation state
        self.sim_time = time.time()
        self.sim_lat = 37.7749  # Default: San Francisco
        self.sim_lon = -122.4194
        self.sim_speed = 0.0
        self.sim_heading = 0.0

    def connect(self) -> bool:
        """
        Connect to gpsd daemon.

        Returns:
            True if connected successfully, False otherwise
        """
        if self.simulation_mode:
            logger.info("GPS: Running in simulation mode")
            self.connected = True
            return True

        try:
            # Connect to gpsd (should be running as daemon)
            self.client = GPSDClient(host="localhost")
            logger.info("GPS connected to gpsd daemon")
            self.connected = True
            return True

        except Exception as e:
            logger.error(f"Failed to connect to gpsd: {e}")
            logger.info("Make sure gpsd is running: sudo systemctl start gpsd")
            self.simulation_mode = True
            self.connected = True
            return True

    def read(self) -> Dict[str, Any]:
        """
        Read current GPS data.

        Returns:
            Dictionary with GPS data (lat, lon, speed, altitude, etc.)
        """
        if self.simulation_mode:
            return self._get_simulated_data()

        try:
            # Get current fix from gpsd
            for result in self.client.dict_stream(convert_datetime=True):
                if result.get('class') == 'TPV':  # Time-Position-Velocity report
                    # Extract data
                    data = {
                        'latitude': result.get('lat', 0.0) + self.coord_offset[0],
                        'longitude': result.get('lon', 0.0) + self.coord_offset[1],
                        'altitude_m': result.get('alt', 0.0),
                        'speed_mps': result.get('speed', 0.0),
                        'speed_mph': result.get('speed', 0.0) * 2.23694,
                        'track_deg': result.get('track', 0.0),
                        'climb_mps': result.get('climb', 0.0),
                        'satellites': result.get('satellites_used', 0),
                        'fix_mode': result.get('mode', 0),  # 0=no fix, 2=2D, 3=3D
                        'timestamp': result.get('time', time.time()),
                        'valid': result.get('mode', 0) >= 2 and result.get('satellites_used', 0) >= self.min_satellites
                    }
                    return data

            # If no TPV message received, return invalid data
            return self._get_invalid_data()

        except Exception as e:
            logger.error(f"Error reading GPS: {e}")
            return self._get_invalid_data()

    def get_position(self) -> Tuple[float, float, float]:
        """
        Get current position.

        Returns:
            Tuple of (latitude, longitude, altitude)
        """
        data = self.read()
        return (
            data.get('latitude', 0.0),
            data.get('longitude', 0.0),
            data.get('altitude_m', 0.0)
        )

    def get_speed(self) -> Dict[str, float]:
        """
        Get current speed in various units.

        Returns:
            Dictionary with speed in m/s, mph, km/h
        """
        data = self.read()
        speed_mps = data.get('speed_mps', 0.0)

        return {
            'speed_mps': speed_mps,
            'speed_mph': speed_mps * 2.23694,
            'speed_kph': speed_mps * 3.6
        }

    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two GPS coordinates using Haversine formula.

        Args:
            lat1, lon1: First coordinate
            lat2, lon2: Second coordinate

        Returns:
            Distance in meters
        """
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        return self.EARTH_RADIUS * c

    def set_track_start(self, lat: Optional[float] = None, lon: Optional[float] = None):
        """
        Set the track start/finish line position.

        Args:
            lat, lon: Start line coordinates (if None, uses current position)
        """
        if lat is None or lon is None:
            lat, lon, _ = self.get_position()

        self.track_start_pos = (lat, lon)
        logger.info(f"Track start set: {lat:.6f}, {lon:.6f}")

    def check_lap_complete(self) -> bool:
        """
        Check if vehicle has crossed the start/finish line.

        Returns:
            True if lap completed (crossed start line)
        """
        if self.track_start_pos is None:
            return False

        lat, lon, _ = self.get_position()
        distance = self.calculate_distance(
            lat, lon,
            self.track_start_pos[0], self.track_start_pos[1]
        )

        return distance < self.track_threshold_meters

    def is_valid_fix(self) -> bool:
        """
        Check if current GPS fix is valid.

        Returns:
            True if fix is valid and has enough satellites
        """
        data = self.read()
        return data.get('valid', False)

    def wait_for_fix(self, timeout: float = 60) -> bool:
        """
        Wait for valid GPS fix.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if valid fix acquired
        """
        logger.info("Waiting for GPS fix...")
        start_time = time.time()

        while (time.time() - start_time) < timeout:
            if self.is_valid_fix():
                data = self.read()
                logger.info(f"GPS fix acquired: {data['satellites']} satellites")
                return True

            time.sleep(1)

        logger.warning("GPS fix timeout")
        return False

    def _get_simulated_data(self) -> Dict[str, Any]:
        """
        Generate simulated GPS data for testing.

        Simulates movement in a circular track pattern.

        Returns:
            Dictionary with simulated GPS data
        """
        current_time = time.time()
        dt = current_time - self.sim_time
        self.sim_time = current_time

        # Simulate movement in a circle (like a track)
        # One lap every 120 seconds
        angular_velocity = 2 * math.pi / 120  # rad/s
        radius = 0.002  # degrees (~200m radius)

        # Update position
        angle = (current_time % 120) * angular_velocity
        self.sim_lat = 37.7749 + radius * math.cos(angle)
        self.sim_lon = -122.4194 + radius * math.sin(angle)

        # Simulate speed (faster in straightaways)
        self.sim_speed = 20 + 15 * abs(math.sin(angle * 2))  # 20-35 m/s (45-78 mph)

        # Heading follows circle
        self.sim_heading = math.degrees(angle) % 360

        return {
            'latitude': self.sim_lat + self.coord_offset[0],
            'longitude': self.sim_lon + self.coord_offset[1],
            'altitude_m': 50.0 + random.uniform(-5, 5),
            'speed_mps': self.sim_speed,
            'speed_mph': self.sim_speed * 2.23694,
            'track_deg': self.sim_heading,
            'climb_mps': random.uniform(-2, 2),
            'satellites': 8,
            'fix_mode': 3,
            'timestamp': current_time,
            'valid': True
        }

    def _get_invalid_data(self) -> Dict[str, Any]:
        """
        Return invalid/no-fix GPS data.

        Returns:
            Dictionary with zero/invalid values
        """
        return {
            'latitude': 0.0,
            'longitude': 0.0,
            'altitude_m': 0.0,
            'speed_mps': 0.0,
            'speed_mph': 0.0,
            'track_deg': 0.0,
            'climb_mps': 0.0,
            'satellites': 0,
            'fix_mode': 0,
            'timestamp': time.time(),
            'valid': False
        }

    def is_connected(self) -> bool:
        """Check if GPS is connected."""
        return self.connected

    def export_kml(self, coordinates: list, filename: str):
        """
        Export GPS track to KML file for Google Earth.

        Args:
            coordinates: List of (lat, lon, alt) tuples
            filename: Output KML filename
        """
        try:
            import simplekml

            kml = simplekml.Kml()
            kml.newlinestring(name="GPS Track", coords=coordinates)

            kml.save(filename)
            logger.info(f"Exported KML to {filename}")

        except ImportError:
            logger.error("simplekml not available - cannot export KML")
        except Exception as e:
            logger.error(f"Error exporting KML: {e}")


if __name__ == "__main__":
    # Test the GPS interface in simulation mode
    logging.basicConfig(level=logging.INFO)

    test_config = {
        'min_satellites': 4,
        'sample_rate_hz': 5,
        'coordinate_offset': {'latitude': 0.0, 'longitude': 0.0}
    }

    gps = GPS(test_config, simulation_mode=True)

    if gps.connect():
        print("GPS connected")

        # Set track start
        gps.set_track_start()

        # Test reading data
        coords = []
        for i in range(20):
            data = gps.read()
            print(f"\nSample {i+1}:")
            print(f"  Position: {data['latitude']:.6f}, {data['longitude']:.6f}")
            print(f"  Altitude: {data['altitude_m']:.1f}m")
            print(f"  Speed: {data['speed_mph']:.1f} mph")
            print(f"  Heading: {data['track_deg']:.1f}°")
            print(f"  Satellites: {data['satellites']}")
            print(f"  Valid: {data['valid']}")

            coords.append((data['longitude'], data['latitude'], data['altitude_m']))

            # Check for lap completion
            if i > 0 and gps.check_lap_complete():
                print("  *** LAP COMPLETE ***")

            time.sleep(0.2)

        # Export to KML
        gps.export_kml(coords, "/tmp/test_track.kml")
    else:
        print("Failed to connect")
