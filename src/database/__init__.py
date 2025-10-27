"""
Database package for TimescaleDB integration
"""

from .timescale_client import TimescaleClient, TimescaleConfig

__all__ = ['TimescaleClient', 'TimescaleConfig']
