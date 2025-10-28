"""
Session Management Module
List, load, and compare DAQ sessions.
"""

import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manage DAQ sessions.

    List available sessions, load session data, and compare sessions.
    """

    def __init__(self, data_dir: str = "data/sessions"):
        """
        Initialize session manager.

        Args:
            data_dir: Base directory containing session folders
        """
        self.data_dir = Path(data_dir)

        if not self.data_dir.exists():
            logger.warning(f"Data directory does not exist: {self.data_dir}")
            self.data_dir.mkdir(parents=True, exist_ok=True)

    def list_sessions(self) -> List[Dict]:
        """
        List all available sessions.

        Returns:
            List of session info dictionaries
        """
        sessions = []

        for session_path in sorted(self.data_dir.glob("session_*")):
            if not session_path.is_dir():
                continue

            session_info = {
                'path': str(session_path),
                'name': session_path.name,
                'timestamp': self._extract_timestamp(session_path.name)
            }

            # Load session summary if available
            summary_path = session_path / "session_summary.json"
            if summary_path.exists():
                try:
                    with open(summary_path, 'r') as f:
                        summary = json.load(f)
                        session_info['summary'] = summary
                        session_info['duration'] = summary.get('duration_seconds', 0)
                        session_info['samples'] = summary.get('samples_collected', 0)
                except Exception as e:
                    logger.error(f"Failed to load summary for {session_path.name}: {e}")

            # Check for data file
            data_path = session_path / "data.csv"
            session_info['has_data'] = data_path.exists()

            if session_info['has_data']:
                session_info['data_size_mb'] = data_path.stat().st_size / (1024 * 1024)

            sessions.append(session_info)

        return sessions

    def load_session(self, session_name: str) -> Optional[pd.DataFrame]:
        """
        Load session data.

        Args:
            session_name: Session folder name or full path

        Returns:
            DataFrame with session data, or None if not found
        """
        # Check if it's a full path or just name
        if Path(session_name).is_absolute():
            session_path = Path(session_name)
        else:
            session_path = self.data_dir / session_name

        data_path = session_path / "data.csv"

        if not data_path.exists():
            logger.error(f"Session data not found: {data_path}")
            return None

        try:
            data = pd.read_csv(data_path)
            logger.info(f"Loaded session {session_name}: {len(data)} samples")
            return data
        except Exception as e:
            logger.error(f"Failed to load session data: {e}")
            return None

    def get_latest_session(self) -> Optional[str]:
        """
        Get path to most recent session.

        Returns:
            Path to latest session directory, or None if no sessions
        """
        sessions = self.list_sessions()

        if not sessions:
            return None

        # Sort by timestamp descending
        sessions.sort(key=lambda x: x['timestamp'], reverse=True)

        return sessions[0]['path']

    def compare_sessions(self, session1: str, session2: str) -> Dict:
        """
        Compare two sessions.

        Args:
            session1: First session name/path
            session2: Second session name/path

        Returns:
            Dictionary with comparison results
        """
        data1 = self.load_session(session1)
        data2 = self.load_session(session2)

        if data1 is None or data2 is None:
            logger.error("Failed to load session data for comparison")
            return {}

        comparison = {
            'session1': session1,
            'session2': session2
        }

        # Compare basic stats
        comparison['duration_diff'] = data2['elapsed_time'].max() - data1['elapsed_time'].max()
        comparison['samples_diff'] = len(data2) - len(data1)

        # Compare max values
        metrics = ['rpm', 'speed_mph', 'accel_long_g', 'accel_lat_g', 'accel_total_g']

        for metric in metrics:
            if metric in data1.columns and metric in data2.columns:
                max1 = data1[metric].max()
                max2 = data2[metric].max()
                comparison[f'{metric}_max_diff'] = max2 - max1
                comparison[f'{metric}_max1'] = max1
                comparison[f'{metric}_max2'] = max2

        return comparison

    def delete_session(self, session_name: str) -> bool:
        """
        Delete a session.

        Args:
            session_name: Session name/path to delete

        Returns:
            True if deleted successfully
        """
        if Path(session_name).is_absolute():
            session_path = Path(session_name)
        else:
            session_path = self.data_dir / session_name

        if not session_path.exists():
            logger.error(f"Session not found: {session_path}")
            return False

        try:
            import shutil
            shutil.rmtree(session_path)
            logger.info(f"Deleted session: {session_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False

    def _extract_timestamp(self, session_name: str) -> datetime:
        """
        Extract timestamp from session name.

        Args:
            session_name: Session folder name (e.g., session_20231125_143022)

        Returns:
            datetime object
        """
        try:
            # Extract timestamp from name (format: session_YYYYMMDD_HHMMSS)
            timestamp_str = session_name.replace('session_', '')
            return datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
        except Exception:
            # If parsing fails, use file modification time
            return datetime.now()

    def print_session_list(self):
        """Print formatted list of all sessions."""
        sessions = self.list_sessions()

        if not sessions:
            print("No sessions found.")
            return

        print("\n" + "=" * 80)
        print("AVAILABLE SESSIONS")
        print("=" * 80)

        for i, session in enumerate(sessions, 1):
            print(f"\n{i}. {session['name']}")
            print(f"   Timestamp: {session['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")

            if 'duration' in session:
                duration_min = session['duration'] / 60
                print(f"   Duration: {duration_min:.1f} minutes")

            if 'samples' in session:
                print(f"   Samples: {session['samples']:,}")

            if 'data_size_mb' in session:
                print(f"   Data size: {session['data_size_mb']:.2f} MB")

            if not session['has_data']:
                print("   ⚠ Data file missing!")

        print("\n" + "=" * 80)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    manager = SessionManager()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "list":
            manager.print_session_list()

        elif command == "latest":
            latest = manager.get_latest_session()
            if latest:
                print(f"Latest session: {latest}")
            else:
                print("No sessions found")

        elif command == "load" and len(sys.argv) > 2:
            session_name = sys.argv[2]
            data = manager.load_session(session_name)
            if data is not None:
                print(f"Loaded {len(data)} samples")
                print(data.head())

        else:
            print("Usage:")
            print("  python session.py list")
            print("  python session.py latest")
            print("  python session.py load <session_name>")
    else:
        manager.print_session_list()
