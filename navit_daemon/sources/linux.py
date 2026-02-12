"""
Linux data sources: IIO sysfs (IMU) and gpsd (GPS).
"""

import logging
from typing import Optional, Tuple

from navit_daemon.gps_reader import GpsFix, connect_gpsd, get_current_fix
from navit_daemon.iio_reader import (
    IIOReader,
    find_accel_device,
    find_gyro_device,
)
from navit_daemon.sources.base import GPSSource, IMUSource, IMUSample

logger = logging.getLogger(__name__)


class LinuxIMUSource(IMUSource):
    """IMU from Linux IIO sysfs."""

    def __init__(self, reader: IIOReader) -> None:
        self._reader = reader

    def read(self) -> IMUSample:
        accel = self._reader.read_accel()
        gyro = self._reader.read_gyro()
        if accel and gyro:
            return (accel, gyro)
        return None


class LinuxGPSSource(GPSSource):
    """GPS from gpsd."""

    def __init__(self, gpsd_module: Optional[object]) -> None:
        self._gpsd = gpsd_module

    def get_fix(self) -> Optional[GpsFix]:
        return get_current_fix(self._gpsd)


def create_linux_sources(
    gpsd_host: str,
    gpsd_port: int,
    accel_path_str: Optional[str] = None,
    gyro_path_str: Optional[str] = None,
) -> Optional[Tuple[LinuxIMUSource, LinuxGPSSource]]:
    """
    Create Linux IIO + gpsd sources.

    Returns (IMUSource, GPSSource) or None if IIO accel/gyro not found.
    gpsd may be unavailable; GPSSource will then return None from get_fix().
    """
    gpsd = connect_gpsd(gpsd_host, gpsd_port)
    if gpsd is None:
        logger.warning("gpsd not available; position will be unavailable.")
    accel_path = find_accel_device(accel_path_str)
    gyro_path = find_gyro_device(gyro_path_str, accel_path)
    if not accel_path or not gyro_path:
        return None
    reader = IIOReader(accel_path=accel_path, gyro_path=gyro_path)
    return (LinuxIMUSource(reader), LinuxGPSSource(gpsd))
