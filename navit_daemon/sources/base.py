"""
Abstract interfaces for IMU and GPS data sources.
"""

from typing import Optional, Tuple

from navit_daemon.gps_reader import GpsFix

# (accel_xyz, gyro_xyz) or None
IMUSample = Optional[Tuple[Tuple[float, float, float], Tuple[float, float, float]]]


class IMUSource:
    """Source of accelerometer and gyroscope samples."""

    def read(self) -> IMUSample:
        """
        Return (accel_xyz, gyro_xyz) in m/s^2 and deg/s, or None.

        None means no sample available (non-blocking).
        """
        raise NotImplementedError


class GPSSource:
    """Source of GPS position and velocity."""

    def get_fix(self) -> Optional[GpsFix]:
        """Return current fix or None if unavailable."""
        raise NotImplementedError
