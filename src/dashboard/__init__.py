"""
Dashboard module for BMW M3 DAQ System.

Provides real-time web interface for monitoring sensors.
"""

from .app import DashboardServer

__all__ = ['DashboardServer']
