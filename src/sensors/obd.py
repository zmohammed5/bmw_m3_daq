"""
OBD-II Interface Module
Handles communication with ELM327 Bluetooth adapter to read vehicle parameters.
"""

import obd
import logging
from typing import Dict, Optional, List, Any
import time
from threading import Lock

logger = logging.getLogger(__name__)


class OBDInterface:
    """
    Interface for reading OBD-II data from vehicle via ELM327 adapter.

    Manages connection to OBD-II port, queries supported PIDs, and provides
    both synchronous and asynchronous data retrieval with priority-based polling.
    """

    def __init__(self, config: Dict[str, Any], simulation_mode: bool = False):
        """
        Initialize OBD-II interface.

        Args:
            config: Configuration dictionary with OBD settings
            simulation_mode: If True, generate fake data for testing
        """
        self.config = config
        self.simulation_mode = simulation_mode
        self.connection: Optional[obd.OBD] = None
        self.supported_pids: List[str] = []
        self.last_values: Dict[str, Any] = {}
        self.lock = Lock()
        self.connected = False

        # Simulated values for testing
        self.sim_rpm = 800
        self.sim_speed = 0
        self.sim_time = time.time()

    def connect(self) -> bool:
        """
        Establish connection to OBD-II adapter.

        Returns:
            True if connected successfully, False otherwise
        """
        if self.simulation_mode:
            logger.info("OBD-II: Running in simulation mode")
            self.connected = True
            self._setup_simulated_pids()
            return True

        try:
            timeout = self.config.get('connection_timeout_seconds', 10)
            logger.info(f"Connecting to OBD-II adapter (timeout: {timeout}s)...")

            # Try to connect - will auto-detect port
            self.connection = obd.OBD(timeout=timeout)

            if self.connection.is_connected():
                logger.info(f"OBD-II connected: {self.connection.port_name()}")
                self._query_supported_pids()
                self.connected = True
                return True
            else:
                logger.error("Failed to connect to OBD-II adapter")
                return False

        except Exception as e:
            logger.error(f"OBD-II connection error: {e}")
            return False

    def disconnect(self):
        """Close OBD-II connection."""
        if self.connection and not self.simulation_mode:
            self.connection.close()
            logger.info("OBD-II disconnected")
        self.connected = False

    def _query_supported_pids(self):
        """Query which PIDs are supported by the vehicle."""
        if self.simulation_mode:
            return

        logger.info("Querying supported PIDs...")

        # Get list of all available commands
        supported = self.connection.supported_commands

        self.supported_pids = [cmd.name for cmd in supported]
        logger.info(f"Found {len(self.supported_pids)} supported PIDs")
        logger.debug(f"Supported PIDs: {self.supported_pids}")

    def _setup_simulated_pids(self):
        """Set up list of simulated PIDs for testing."""
        self.supported_pids = [
            'RPM', 'SPEED', 'THROTTLE_POS', 'COOLANT_TEMP', 'INTAKE_TEMP',
            'MAF', 'ENGINE_LOAD', 'TIMING_ADVANCE', 'SHORT_FUEL_TRIM_1',
            'LONG_FUEL_TRIM_1', 'O2_B1S1', 'FUEL_STATUS', 'BAROMETRIC_PRESSURE',
            'INTAKE_PRESSURE', 'FUEL_PRESSURE'
        ]

    def read_pid(self, pid_name: str) -> Optional[Any]:
        """
        Read a single PID value.

        Args:
            pid_name: Name of the PID to read (e.g., 'RPM', 'SPEED')

        Returns:
            PID value with units, or None if failed
        """
        if not self.connected:
            return None

        if self.simulation_mode:
            return self._get_simulated_value(pid_name)

        try:
            cmd = obd.commands[pid_name]
            response = self.connection.query(cmd)

            if response.is_null():
                return None

            # Store last value
            with self.lock:
                self.last_values[pid_name] = response.value

            return response.value

        except KeyError:
            logger.warning(f"Unknown PID: {pid_name}")
            return None
        except Exception as e:
            logger.error(f"Error reading {pid_name}: {e}")
            return None

    def read_all_fast_pids(self) -> Dict[str, Any]:
        """
        Read all fast-polling PIDs (RPM, speed, throttle).

        Returns:
            Dictionary of PID values
        """
        fast_pids = self.config.get('fast_pids', ['RPM', 'SPEED', 'THROTTLE_POS'])
        data = {}

        for pid in fast_pids:
            value = self.read_pid(pid)
            if value is not None:
                data[pid] = value

        return data

    def read_all_slow_pids(self) -> Dict[str, Any]:
        """
        Read all slow-polling PIDs (temperatures, fuel trim, etc.).

        Returns:
            Dictionary of PID values
        """
        slow_pids = self.config.get('slow_pids', [])
        data = {}

        for pid in slow_pids:
            value = self.read_pid(pid)
            if value is not None:
                data[pid] = value

        return data

    def read_all_pids(self) -> Dict[str, Any]:
        """
        Read all configured PIDs.

        Returns:
            Dictionary of all PID values
        """
        data = {}
        data.update(self.read_all_fast_pids())
        data.update(self.read_all_slow_pids())
        return data

    def get_dtcs(self) -> List[str]:
        """
        Get diagnostic trouble codes.

        Returns:
            List of DTC codes
        """
        if not self.connected or self.simulation_mode:
            return []

        try:
            response = self.connection.query(obd.commands.GET_DTC)
            if not response.is_null():
                return [dtc[0] for dtc in response.value]
            return []
        except Exception as e:
            logger.error(f"Error reading DTCs: {e}")
            return []

    def clear_dtcs(self) -> bool:
        """
        Clear diagnostic trouble codes.

        Returns:
            True if successful
        """
        if not self.connected or self.simulation_mode:
            return False

        try:
            response = self.connection.query(obd.commands.CLEAR_DTC)
            return not response.is_null()
        except Exception as e:
            logger.error(f"Error clearing DTCs: {e}")
            return False

    def _get_simulated_value(self, pid_name: str) -> Any:
        """
        Generate simulated sensor values for testing.

        Args:
            pid_name: Name of PID to simulate

        Returns:
            Simulated value
        """
        import random

        # Update simulation state
        dt = time.time() - self.sim_time
        self.sim_time = time.time()

        # Simulate acceleration/deceleration
        if random.random() < 0.1:  # 10% chance to change
            self.sim_rpm += random.randint(-200, 500)
            self.sim_rpm = max(800, min(8000, self.sim_rpm))

            # Speed follows RPM roughly
            gear_ratio = 3.0  # Simplified
            self.sim_speed = (self.sim_rpm / 1000) * 10
            self.sim_speed = max(0, min(155, self.sim_speed))

        # Simulation values - return appropriate types/units
        simulations = {
            'RPM': self.sim_rpm,
            'SPEED': self.sim_speed,
            'THROTTLE_POS': min(100, (self.sim_rpm - 800) / 72),
            'COOLANT_TEMP': 85 + random.uniform(-2, 5),
            'INTAKE_TEMP': 30 + random.uniform(-5, 15),
            'MAF': (self.sim_rpm / 100) + random.uniform(-5, 5),
            'ENGINE_LOAD': min(100, (self.sim_rpm / 80)),
            'TIMING_ADVANCE': 15 + random.uniform(-3, 10),
            'SHORT_FUEL_TRIM_1': random.uniform(-5, 5),
            'LONG_FUEL_TRIM_1': random.uniform(-3, 3),
            'O2_B1S1': 0.5 + random.uniform(-0.2, 0.2),
            'FUEL_STATUS': 'Closed loop',
            'BAROMETRIC_PRESSURE': 101.3,
            'INTAKE_PRESSURE': 25 + (self.sim_rpm / 200),
            'FUEL_PRESSURE': 300 + random.uniform(-10, 10)
        }

        return simulations.get(pid_name, 0)

    def is_connected(self) -> bool:
        """Check if OBD-II is connected."""
        return self.connected

    def get_protocol_name(self) -> str:
        """Get the OBD protocol being used."""
        if self.simulation_mode:
            return "SIMULATION"
        if self.connection:
            return self.connection.protocol_name()
        return "NOT CONNECTED"

    def get_port_name(self) -> str:
        """Get the port/device name."""
        if self.simulation_mode:
            return "SIMULATION"
        if self.connection:
            return self.connection.port_name()
        return "NONE"


if __name__ == "__main__":
    # Test the OBD interface in simulation mode
    logging.basicConfig(level=logging.INFO)

    test_config = {
        'connection_timeout_seconds': 10,
        'fast_pids': ['RPM', 'SPEED', 'THROTTLE_POS'],
        'slow_pids': ['COOLANT_TEMP', 'INTAKE_TEMP', 'MAF']
    }

    obd_interface = OBDInterface(test_config, simulation_mode=True)

    if obd_interface.connect():
        print(f"Connected via {obd_interface.get_protocol_name()}")
        print(f"Port: {obd_interface.get_port_name()}")

        # Test reading PIDs
        for _ in range(5):
            data = obd_interface.read_all_pids()
            print(f"\nOBD Data: {data}")
            time.sleep(1)

        obd_interface.disconnect()
    else:
        print("Failed to connect")
