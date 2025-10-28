"""
Data Visualization Module
Create plots and graphs from logged data.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

# Set style
sns.set_style("darkgrid")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 10


class DataVisualizer:
    """
    Create visualizations from DAQ data.

    Generates plots for time series, GPS tracks, g-g diagrams,
    power curves, and more.
    """

    def __init__(self, session_dir: str):
        """
        Initialize visualizer.

        Args:
            session_dir: Path to session directory containing data.csv
        """
        self.session_dir = Path(session_dir)
        self.csv_path = self.session_dir / "data.csv"
        self.plots_dir = self.session_dir / "plots"
        self.plots_dir.mkdir(exist_ok=True)

        if not self.csv_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.csv_path}")

        # Load data
        self.data = pd.read_csv(self.csv_path)
        logger.info(f"Loaded {len(self.data)} samples for visualization")

    def plot_rpm_and_speed(self, save: bool = True) -> Optional[str]:
        """
        Plot RPM and speed over time.

        Args:
            save: If True, save plot to file

        Returns:
            Path to saved plot if save=True
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))

        time = self.data['elapsed_time']

        # RPM plot
        if 'rpm' in self.data.columns:
            ax1.plot(time, self.data['rpm'], 'b-', linewidth=1, label='RPM')
            ax1.fill_between(time, 0, self.data['rpm'], alpha=0.3)
            ax1.axhline(y=8000, color='r', linestyle='--', alpha=0.5, label='Redline')
            ax1.set_ylabel('RPM', fontsize=12)
            ax1.set_title('Engine RPM vs Time', fontsize=14, fontweight='bold')
            ax1.legend()
            ax1.grid(True, alpha=0.3)

        # Speed plot
        if 'speed_mph' in self.data.columns:
            ax2.plot(time, self.data['speed_mph'], 'g-', linewidth=1, label='Speed')
            ax2.fill_between(time, 0, self.data['speed_mph'], alpha=0.3, color='green')
            ax2.set_xlabel('Time (seconds)', fontsize=12)
            ax2.set_ylabel('Speed (mph)', fontsize=12)
            ax2.set_title('Vehicle Speed vs Time', fontsize=14, fontweight='bold')
            ax2.legend()
            ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        if save:
            output_path = self.plots_dir / "rpm_and_speed.png"
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            logger.info(f"Saved plot: {output_path}")
            plt.close()
            return str(output_path)

        plt.show()
        return None

    def plot_acceleration(self, save: bool = True) -> Optional[str]:
        """
        Plot 3-axis acceleration over time.

        Args:
            save: If True, save plot to file

        Returns:
            Path to saved plot if save=True
        """
        fig, ax = plt.subplots(figsize=(14, 6))

        time = self.data['elapsed_time']

        # Plot each axis
        if 'accel_long_g' in self.data.columns:
            ax.plot(time, self.data['accel_long_g'], 'r-', label='Longitudinal', alpha=0.8)

        if 'accel_lat_g' in self.data.columns:
            ax.plot(time, self.data['accel_lat_g'], 'b-', label='Lateral', alpha=0.8)

        if 'accel_vert_g' in self.data.columns:
            ax.plot(time, self.data['accel_vert_g'], 'g-', label='Vertical', alpha=0.8)

        ax.axhline(y=0, color='k', linestyle='-', alpha=0.3, linewidth=0.5)
        ax.axhline(y=1.0, color='r', linestyle='--', alpha=0.3, label='1g Reference')
        ax.axhline(y=-1.0, color='r', linestyle='--', alpha=0.3)

        ax.set_xlabel('Time (seconds)', fontsize=12)
        ax.set_ylabel('Acceleration (g)', fontsize=12)
        ax.set_title('Acceleration vs Time', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save:
            output_path = self.plots_dir / "acceleration.png"
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            logger.info(f"Saved plot: {output_path}")
            plt.close()
            return str(output_path)

        plt.show()
        return None

    def plot_gg_diagram(self, save: bool = True) -> Optional[str]:
        """
        Create G-G diagram (lateral vs longitudinal acceleration).

        Args:
            save: If True, save plot to file

        Returns:
            Path to saved plot if save=True
        """
        if 'accel_long_g' not in self.data.columns or 'accel_lat_g' not in self.data.columns:
            logger.error("Acceleration data not available for G-G diagram")
            return None

        fig, ax = plt.subplots(figsize=(10, 10))

        # Create scatter plot colored by speed
        if 'speed_mph' in self.data.columns:
            scatter = ax.scatter(
                self.data['accel_lat_g'],
                self.data['accel_long_g'],
                c=self.data['speed_mph'],
                cmap='viridis',
                s=10,
                alpha=0.6
            )
            cbar = plt.colorbar(scatter, ax=ax)
            cbar.set_label('Speed (mph)', fontsize=12)
        else:
            ax.scatter(
                self.data['accel_lat_g'],
                self.data['accel_long_g'],
                s=10,
                alpha=0.6
            )

        # Draw circles for reference
        circle_1g = plt.Circle((0, 0), 1.0, fill=False, color='r', linestyle='--', alpha=0.5, label='1.0g')
        ax.add_patch(circle_1g)

        # Axes
        ax.axhline(y=0, color='k', linestyle='-', alpha=0.3, linewidth=0.5)
        ax.axvline(x=0, color='k', linestyle='-', alpha=0.3, linewidth=0.5)

        ax.set_xlabel('Lateral Acceleration (g)', fontsize=12)
        ax.set_ylabel('Longitudinal Acceleration (g)', fontsize=12)
        ax.set_title('G-G Diagram', fontsize=14, fontweight='bold')
        ax.set_aspect('equal')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Set limits
        max_g = max(
            abs(self.data['accel_lat_g'].max()),
            abs(self.data['accel_lat_g'].min()),
            abs(self.data['accel_long_g'].max()),
            abs(self.data['accel_long_g'].min())
        )
        limit = max(1.5, max_g * 1.1)
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)

        plt.tight_layout()

        if save:
            output_path = self.plots_dir / "gg_diagram.png"
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            logger.info(f"Saved plot: {output_path}")
            plt.close()
            return str(output_path)

        plt.show()
        return None

    def plot_gps_track(self, save: bool = True) -> Optional[str]:
        """
        Plot GPS track on 2D map.

        Args:
            save: If True, save plot to file

        Returns:
            Path to saved plot if save=True
        """
        if 'gps_lat' not in self.data.columns or 'gps_lon' not in self.data.columns:
            logger.error("GPS data not available")
            return None

        # Filter valid GPS data
        valid_gps = self.data[self.data['gps_valid'] == True]

        if len(valid_gps) == 0:
            logger.error("No valid GPS data")
            return None

        fig, ax = plt.subplots(figsize=(12, 12))

        # Plot track colored by speed
        if 'speed_mph' in valid_gps.columns:
            scatter = ax.scatter(
                valid_gps['gps_lon'],
                valid_gps['gps_lat'],
                c=valid_gps['speed_mph'],
                cmap='jet',
                s=20,
                alpha=0.7
            )
            cbar = plt.colorbar(scatter, ax=ax)
            cbar.set_label('Speed (mph)', fontsize=12)
        else:
            ax.plot(valid_gps['gps_lon'], valid_gps['gps_lat'], 'b-', linewidth=2)

        # Mark start and end
        ax.plot(valid_gps.iloc[0]['gps_lon'], valid_gps.iloc[0]['gps_lat'],
                'go', markersize=15, label='Start', markeredgecolor='black', markeredgewidth=2)
        ax.plot(valid_gps.iloc[-1]['gps_lon'], valid_gps.iloc[-1]['gps_lat'],
                'ro', markersize=15, label='End', markeredgecolor='black', markeredgewidth=2)

        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)
        ax.set_title('GPS Track', fontsize=14, fontweight='bold')
        ax.set_aspect('equal')
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save:
            output_path = self.plots_dir / "gps_track.png"
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            logger.info(f"Saved plot: {output_path}")
            plt.close()
            return str(output_path)

        plt.show()
        return None

    def plot_temperatures(self, save: bool = True) -> Optional[str]:
        """
        Plot all temperature sensors over time.

        Args:
            save: If True, save plot to file

        Returns:
            Path to saved plot if save=True
        """
        temp_cols = [col for col in self.data.columns if 'temp_' in col and col != 'temp_ambient_f']

        if not temp_cols:
            logger.error("No temperature data available")
            return None

        fig, ax = plt.subplots(figsize=(14, 6))

        time = self.data['elapsed_time']
        colors = ['red', 'blue', 'green', 'orange', 'purple']

        for i, col in enumerate(temp_cols):
            label = col.replace('temp_', '').replace('_f', '').title()
            ax.plot(time, self.data[col], label=label, linewidth=2, color=colors[i % len(colors)])

        ax.set_xlabel('Time (seconds)', fontsize=12)
        ax.set_ylabel('Temperature (°F)', fontsize=12)
        ax.set_title('Temperature vs Time', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save:
            output_path = self.plots_dir / "temperatures.png"
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            logger.info(f"Saved plot: {output_path}")
            plt.close()
            return str(output_path)

        plt.show()
        return None

    def plot_power_curve(self, power_data: pd.DataFrame, save: bool = True) -> Optional[str]:
        """
        Plot estimated power and torque curves.

        Args:
            power_data: DataFrame from PerformanceAnalyzer.estimate_power_curve()
            save: If True, save plot to file

        Returns:
            Path to saved plot if save=True
        """
        if power_data.empty:
            logger.error("No power curve data provided")
            return None

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

        rpm = power_data['rpm']

        # Power plot
        if 'power_hp' in power_data.columns:
            ax1.plot(rpm, power_data['power_hp'], 'r-', linewidth=2, marker='o')
            ax1.fill_between(rpm, 0, power_data['power_hp'], alpha=0.3, color='red')
            ax1.set_ylabel('Power (HP)', fontsize=12, color='red')
            ax1.set_title('Estimated Power Curve', fontsize=14, fontweight='bold')
            ax1.grid(True, alpha=0.3)
            ax1.tick_params(axis='y', labelcolor='red')

        # Torque plot
        if 'torque_lbft' in power_data.columns:
            ax2.plot(rpm, power_data['torque_lbft'], 'b-', linewidth=2, marker='o')
            ax2.fill_between(rpm, 0, power_data['torque_lbft'], alpha=0.3, color='blue')
            ax2.set_xlabel('RPM', fontsize=12)
            ax2.set_ylabel('Torque (lb-ft)', fontsize=12, color='blue')
            ax2.set_title('Estimated Torque Curve', fontsize=14, fontweight='bold')
            ax2.grid(True, alpha=0.3)
            ax2.tick_params(axis='y', labelcolor='blue')

        plt.tight_layout()

        if save:
            output_path = self.plots_dir / "power_curve.png"
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            logger.info(f"Saved plot: {output_path}")
            plt.close()
            return str(output_path)

        plt.show()
        return None

    def plot_throttle_and_load(self, save: bool = True) -> Optional[str]:
        """
        Plot throttle position and engine load over time.

        Args:
            save: If True, save plot to file

        Returns:
            Path to saved plot if save=True
        """
        if 'throttle_pos' not in self.data.columns:
            logger.error("Throttle data not available")
            return None

        fig, ax = plt.subplots(figsize=(14, 6))

        time = self.data['elapsed_time']

        # Throttle position
        ax.plot(time, self.data['throttle_pos'], 'b-', label='Throttle Position', linewidth=1)
        ax.fill_between(time, 0, self.data['throttle_pos'], alpha=0.3, color='blue')

        # Engine load (if available)
        if 'engine_load' in self.data.columns:
            ax.plot(time, self.data['engine_load'], 'r-', label='Engine Load', linewidth=1, alpha=0.7)

        ax.set_xlabel('Time (seconds)', fontsize=12)
        ax.set_ylabel('Percentage (%)', fontsize=12)
        ax.set_title('Throttle Position and Engine Load vs Time', fontsize=14, fontweight='bold')
        ax.set_ylim(0, 100)
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save:
            output_path = self.plots_dir / "throttle_and_load.png"
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            logger.info(f"Saved plot: {output_path}")
            plt.close()
            return str(output_path)

        plt.show()
        return None

    def create_all_plots(self):
        """Generate all standard plots for the session."""
        print(f"\nGenerating plots for session: {self.session_dir.name}\n")

        plots_created = []

        # RPM and Speed
        try:
            path = self.plot_rpm_and_speed(save=True)
            if path:
                plots_created.append(path)
                print(f"✓ RPM and Speed: {path}")
        except Exception as e:
            print(f"✗ RPM and Speed failed: {e}")

        # Acceleration
        try:
            path = self.plot_acceleration(save=True)
            if path:
                plots_created.append(path)
                print(f"✓ Acceleration: {path}")
        except Exception as e:
            print(f"✗ Acceleration failed: {e}")

        # G-G Diagram
        try:
            path = self.plot_gg_diagram(save=True)
            if path:
                plots_created.append(path)
                print(f"✓ G-G Diagram: {path}")
        except Exception as e:
            print(f"✗ G-G Diagram failed: {e}")

        # GPS Track
        try:
            path = self.plot_gps_track(save=True)
            if path:
                plots_created.append(path)
                print(f"✓ GPS Track: {path}")
        except Exception as e:
            print(f"✗ GPS Track failed: {e}")

        # Temperatures
        try:
            path = self.plot_temperatures(save=True)
            if path:
                plots_created.append(path)
                print(f"✓ Temperatures: {path}")
        except Exception as e:
            print(f"✗ Temperatures failed: {e}")

        # Throttle and Load
        try:
            path = self.plot_throttle_and_load(save=True)
            if path:
                plots_created.append(path)
                print(f"✓ Throttle and Load: {path}")
        except Exception as e:
            print(f"✗ Throttle and Load failed: {e}")

        print(f"\nCreated {len(plots_created)} plots in {self.plots_dir}")

        return plots_created


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python visualization.py <session_directory>")
        sys.exit(1)

    session_dir = sys.argv[1]

    visualizer = DataVisualizer(session_dir)
    visualizer.create_all_plots()
