"""
Data Export Utilities
Export session data to various formats (Excel, KML, JSON).
"""

import logging
import pandas as pd
from pathlib import Path
from typing import Optional
import json

logger = logging.getLogger(__name__)


class DataExporter:
    """
    Export session data to various formats.

    Supports CSV, Excel, JSON, and KML (GPS tracks).
    """

    def __init__(self, session_dir: str):
        """
        Initialize data exporter.

        Args:
            session_dir: Path to session directory containing data.csv
        """
        self.session_dir = Path(session_dir)
        self.csv_path = self.session_dir / "data.csv"

        if not self.csv_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.csv_path}")

        # Load data
        self.data = pd.read_csv(self.csv_path)
        logger.info(f"Loaded {len(self.data)} samples from {self.csv_path}")

    def to_excel(self, output_path: Optional[str] = None) -> str:
        """
        Export data to Excel format with multiple sheets.

        Args:
            output_path: Output file path (default: session_dir/data.xlsx)

        Returns:
            Path to exported file
        """
        if output_path is None:
            output_path = self.session_dir / "data.xlsx"
        else:
            output_path = Path(output_path)

        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Main data sheet
                self.data.to_excel(writer, sheet_name='All Data', index=False)

                # OBD-II data sheet
                obd_cols = [col for col in self.data.columns if any(x in col for x in
                    ['rpm', 'speed', 'throttle', 'coolant', 'intake', 'maf', 'load', 'timing', 'fuel'])]
                if obd_cols:
                    self.data[['timestamp', 'elapsed_time'] + obd_cols].to_excel(
                        writer, sheet_name='OBD-II', index=False
                    )

                # Acceleration data sheet
                accel_cols = [col for col in self.data.columns if 'accel' in col or 'pitch' in col or 'roll' in col]
                if accel_cols:
                    self.data[['timestamp', 'elapsed_time'] + accel_cols].to_excel(
                        writer, sheet_name='Acceleration', index=False
                    )

                # GPS data sheet
                gps_cols = [col for col in self.data.columns if 'gps' in col]
                if gps_cols:
                    self.data[['timestamp', 'elapsed_time'] + gps_cols].to_excel(
                        writer, sheet_name='GPS', index=False
                    )

                # Temperature data sheet
                temp_cols = [col for col in self.data.columns if 'temp' in col]
                if temp_cols:
                    self.data[['timestamp', 'elapsed_time'] + temp_cols].to_excel(
                        writer, sheet_name='Temperature', index=False
                    )

            logger.info(f"Exported to Excel: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Failed to export to Excel: {e}")
            raise

    def to_json(self, output_path: Optional[str] = None, pretty: bool = True) -> str:
        """
        Export data to JSON format.

        Args:
            output_path: Output file path (default: session_dir/data.json)
            pretty: If True, format JSON with indentation

        Returns:
            Path to exported file
        """
        if output_path is None:
            output_path = self.session_dir / "data.json"
        else:
            output_path = Path(output_path)

        try:
            # Convert to JSON (orient='records' for list of dictionaries)
            data_dict = self.data.to_dict(orient='records')

            with open(output_path, 'w') as f:
                if pretty:
                    json.dump(data_dict, f, indent=2)
                else:
                    json.dump(data_dict, f)

            logger.info(f"Exported to JSON: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")
            raise

    def to_kml(self, output_path: Optional[str] = None, color_by: str = 'speed') -> str:
        """
        Export GPS track to KML format for Google Earth.

        Args:
            output_path: Output file path (default: session_dir/track.kml)
            color_by: Color track by 'speed', 'accel', or 'rpm'

        Returns:
            Path to exported file
        """
        if output_path is None:
            output_path = self.session_dir / "track.kml"
        else:
            output_path = Path(output_path)

        try:
            import simplekml

            # Filter valid GPS points
            valid_gps = self.data[self.data['gps_valid'] == True].copy()

            if len(valid_gps) == 0:
                logger.warning("No valid GPS data to export")
                return None

            # Create KML
            kml = simplekml.Kml()

            # Create coordinates list (lon, lat, alt)
            coords = []
            for _, row in valid_gps.iterrows():
                coords.append((
                    row['gps_lon'],
                    row['gps_lat'],
                    row['gps_alt_m']
                ))

            # Create line string
            linestring = kml.newlinestring(name="GPS Track")
            linestring.coords = coords
            linestring.altitudemode = simplekml.AltitudeMode.absolute
            linestring.style.linestyle.width = 3
            linestring.style.linestyle.color = simplekml.Color.red

            # Add placemarks for start/end
            start = valid_gps.iloc[0]
            kml.newpoint(
                name="Start",
                coords=[(start['gps_lon'], start['gps_lat'], start['gps_alt_m'])]
            )

            end = valid_gps.iloc[-1]
            kml.newpoint(
                name="End",
                coords=[(end['gps_lon'], end['gps_lat'], end['gps_alt_m'])]
            )

            # Save KML
            kml.save(str(output_path))

            logger.info(f"Exported GPS track to KML: {output_path}")
            return str(output_path)

        except ImportError:
            logger.error("simplekml not available - cannot export KML")
            return None
        except Exception as e:
            logger.error(f"Failed to export to KML: {e}")
            raise

    def get_summary_statistics(self) -> dict:
        """
        Calculate summary statistics for the session.

        Returns:
            Dictionary with summary stats
        """
        summary = {
            'duration_seconds': self.data['elapsed_time'].max() if 'elapsed_time' in self.data.columns else 0,
            'samples': len(self.data),
            'distance_miles': 0,  # Would need to calculate from GPS
        }

        # OBD-II stats
        if 'rpm' in self.data.columns:
            summary['max_rpm'] = float(self.data['rpm'].max())
            summary['avg_rpm'] = float(self.data['rpm'].mean())

        if 'speed_mph' in self.data.columns:
            summary['max_speed_mph'] = float(self.data['speed_mph'].max())
            summary['avg_speed_mph'] = float(self.data['speed_mph'].mean())

        if 'throttle_pos' in self.data.columns:
            summary['max_throttle_pct'] = float(self.data['throttle_pos'].max())

        # Acceleration stats
        if 'accel_long_g' in self.data.columns:
            summary['max_accel_g'] = float(self.data['accel_long_g'].max())
            summary['max_braking_g'] = float(self.data['accel_long_g'].min())

        if 'accel_lat_g' in self.data.columns:
            summary['max_lateral_g'] = float(self.data['accel_lat_g'].abs().max())

        # Temperature stats
        temp_cols = [col for col in self.data.columns if 'temp_' in col]
        for col in temp_cols:
            summary[f'{col}_max'] = float(self.data[col].max())

        return summary

    def export_all(self):
        """Export data to all supported formats."""
        print(f"\nExporting session data from {self.session_dir.name}...\n")

        # Export to Excel
        try:
            excel_path = self.to_excel()
            print(f"✓ Excel: {excel_path}")
        except Exception as e:
            print(f"✗ Excel export failed: {e}")

        # Export to JSON
        try:
            json_path = self.to_json()
            print(f"✓ JSON: {json_path}")
        except Exception as e:
            print(f"✗ JSON export failed: {e}")

        # Export to KML
        try:
            kml_path = self.to_kml()
            if kml_path:
                print(f"✓ KML: {kml_path}")
        except Exception as e:
            print(f"✗ KML export failed: {e}")

        # Print summary
        print("\nSession Summary:")
        print("-" * 40)
        summary = self.get_summary_statistics()
        for key, value in summary.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python data_export.py <session_directory>")
        sys.exit(1)

    session_dir = sys.argv[1]

    try:
        exporter = DataExporter(session_dir)
        exporter.export_all()
    except Exception as e:
        print(f"Export failed: {e}")
        sys.exit(1)
