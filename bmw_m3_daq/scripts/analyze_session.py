#!/usr/bin/env python3
"""
Complete Session Analysis Script

Analyzes a DAQ session and generates:
- Performance report (0-60, lap times, max values)
- All visualizations (plots, graphs, maps)
- Exported data (Excel, JSON, KML)
"""

import sys
import json
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from analysis import PerformanceAnalyzer, DataVisualizer, SessionManager
from utils import DataExporter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_vehicle_config():
    """Load vehicle configuration."""
    config_path = Path(__file__).parent.parent / "config" / "vehicle_config.json"
    try:
        with open(config_path) as f:
            config = json.load(f)
            return config.get('vehicle', {})
    except Exception as e:
        logger.warning(f"Could not load vehicle config: {e}")
        return {}


def analyze_session(session_dir: str):
    """
    Perform complete analysis of a session.

    Args:
        session_dir: Path to session directory
    """
    session_path = Path(session_dir)

    if not session_path.exists():
        print(f"Error: Session directory not found: {session_dir}")
        return False

    data_file = session_path / "data.csv"
    if not data_file.exists():
        print(f"Error: No data file found in session: {data_file}")
        return False

    print("\n" + "=" * 80)
    print(f"ANALYZING SESSION: {session_path.name}")
    print("=" * 80)

    # Load vehicle config
    vehicle_config = load_vehicle_config()

    # 1. Performance Analysis
    print("\n[1/4] Calculating Performance Metrics...")
    print("-" * 80)

    try:
        analyzer = PerformanceAnalyzer(str(session_path), vehicle_config)
        report = analyzer.generate_report()

        # Print summary
        print("\nSession Info:")
        print(f"  Duration: {report['session_info']['duration_seconds']:.1f} seconds "
              f"({report['session_info']['duration_seconds']/60:.1f} minutes)")
        print(f"  Samples: {report['session_info']['total_samples']:,}")

        # 0-60 time
        if report['zero_to_sixty'].get('found'):
            print(f"\n0-60 mph:")
            print(f"  Time: {report['zero_to_sixty']['time_seconds']:.2f} seconds")
            if 'avg_g_force' in report['zero_to_sixty']:
                print(f"  Avg G-force: {report['zero_to_sixty']['avg_g_force']:.2f}g")
            if 'num_runs' in report['zero_to_sixty']:
                print(f"  Runs found: {report['zero_to_sixty']['num_runs']}")

        # 60-0 braking
        if report['sixty_to_zero'].get('found'):
            print(f"\n60-0 mph Braking:")
            print(f"  Time: {report['sixty_to_zero']['time_seconds']:.2f} seconds")
            if 'distance_feet' in report['sixty_to_zero']:
                print(f"  Distance: {report['sixty_to_zero']['distance_feet']:.1f} feet")
            if 'max_g_force' in report['sixty_to_zero']:
                print(f"  Max G-force: {report['sixty_to_zero']['max_g_force']:.2f}g")

        # Max values
        print("\nMaximum Values:")
        max_vals = report['max_values']
        if 'max_speed_mph' in max_vals:
            print(f"  Speed: {max_vals['max_speed_mph']:.1f} mph")
        if 'max_rpm' in max_vals:
            print(f"  RPM: {max_vals['max_rpm']:.0f}")
        if 'max_accel_g' in max_vals:
            print(f"  Acceleration: {max_vals['max_accel_g']:.2f}g")
        if 'max_braking_g' in max_vals:
            print(f"  Braking: {max_vals['max_braking_g']:.2f}g")
        if 'max_lateral_g' in max_vals:
            print(f"  Lateral: {max_vals['max_lateral_g']:.2f}g")

        # Lap times
        if 'laps' in report:
            print(f"\nLap Times:")
            print(f"  Laps detected: {report['laps']['num_laps']}")
            print(f"  Best lap: {report['laps']['best_lap_time']:.2f} seconds")
            for lap in report['laps']['all_laps'][:5]:  # Show first 5
                print(f"    Lap {lap['lap_number']}: {lap['lap_time_seconds']:.2f}s "
                      f"(max: {lap['max_speed_mph']:.1f} mph)")

        # Save report
        report_path = session_path / "performance_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nSaved performance report: {report_path}")

    except Exception as e:
        logger.error(f"Performance analysis failed: {e}")
        return False

    # 2. Visualizations
    print("\n[2/4] Generating Visualizations...")
    print("-" * 80)

    try:
        visualizer = DataVisualizer(str(session_path))
        plots = visualizer.create_all_plots()
        print(f"Created {len(plots)} plots")

        # Try to create power curve if we have acceleration data
        try:
            power_curve = analyzer.estimate_power_curve()
            if not power_curve.empty:
                visualizer.plot_power_curve(power_curve, save=True)
                print("Created power curve plot")
        except Exception as e:
            logger.debug(f"Could not create power curve: {e}")

    except Exception as e:
        logger.error(f"Visualization failed: {e}")
        return False

    # 3. Data Export
    print("\n[3/4] Exporting Data...")
    print("-" * 80)

    try:
        exporter = DataExporter(str(session_path))

        # Export to Excel
        excel_path = exporter.to_excel()
        print(f"Excel: {excel_path}")

        # Export to JSON
        json_path = exporter.to_json()
        print(f"JSON: {json_path}")

        # Export GPS to KML
        kml_path = exporter.to_kml()
        if kml_path:
            print(f"KML: {kml_path}")

    except Exception as e:
        logger.error(f"Data export failed: {e}")
        return False

    # 4. Summary
    print("\n[4/4] Summary")
    print("-" * 80)

    summary = exporter.get_summary_statistics()
    print("\nSession Statistics:")
    for key, value in summary.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE!")
    print("=" * 80)
    print(f"\nAll results saved to: {session_path}")
    print("\nGenerated files:")
    print(f"  - performance_report.json  (performance metrics)")
    print(f"  - data.xlsx                (Excel export)")
    print(f"  - data.json                (JSON export)")
    print(f"  - track.kml                (GPS track for Google Earth)")
    print(f"  - plots/                   (all visualization plots)")
    print()

    return True


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        # No session specified - list available sessions
        print("Usage: python analyze_session.py <session_directory>")
        print("\nAvailable sessions:")

        manager = SessionManager()
        manager.print_session_list()

        # Offer to analyze latest
        latest = manager.get_latest_session()
        if latest:
            response = input(f"\nAnalyze latest session? (y/n): ")
            if response.lower() == 'y':
                return 0 if analyze_session(latest) else 1

        return 1

    session_dir = sys.argv[1]

    # If session name without path, prepend data/sessions/
    if not Path(session_dir).is_absolute() and not session_dir.startswith('data/'):
        session_dir = f"data/sessions/{session_dir}"

    success = analyze_session(session_dir)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
