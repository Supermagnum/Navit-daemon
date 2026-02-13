"""
Abstract interfaces for IMU and GPS data sources.
"""

from typing import Optional, Tuple

from navit_daemon.gps_reader import GpsFix

# (accel_xyz, gyro_xyz, magnetometer_xyz) or None
# magnetometer_xyz can be None if not available
IMUSample = Optional[
    Tuple[
        Tuple[float, float, float],  # accel m/s^2
        Tuple[float, float, float],  # gyro deg/s
        Optional[Tuple[float, float, float]],  # magnetometer microtesla (uT) or None
    ]
]


class IMUSource:
    """Source of accelerometer, gyroscope, and optionally magnetometer samples."""

    def read(self) -> IMUSample:
        """
        Return (accel_xyz, gyro_xyz, magnetometer_xyz) or None.

        accel: (x, y, z) in m/s^2
        gyro: (x, y, z) in deg/s
        magnetometer: (x, y, z) in microtesla (uT) or None if unavailable

        None means no sample available (non-blocking).
        """
        raise NotImplementedError


class GPSSource:
    """Source of GPS position and velocity."""

    def get_fix(self) -> Optional[GpsFix]:
        """Return current fix or None if unavailable."""
        raise NotImplementedError
