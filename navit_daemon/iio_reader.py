"""
Read accelerometer, gyroscope, and magnetometer from Linux IIO sysfs.

Discovers IIO devices under /sys/bus/iio/devices/ and reads raw channels
with scale/offset to produce physical units: m/s^2 for accel, deg/s for gyro,
microtesla (uT) for magnetometer.
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

IIO_BASE = Path("/sys/bus/iio/devices")


def _read_one(path: Path, default: float = 0.0) -> float:
    """Read a single value from sysfs; return default on error."""
    try:
        return float(path.read_text().strip())
    except (OSError, ValueError):
        return default


def _has_channels(device_path: Path, prefix: str) -> bool:
    """Return True if device has x,y,z raw and scale for the given prefix."""
    for axis in ("x", "y", "z"):
        raw = device_path / f"{prefix}_{axis}_raw"
        if not raw.exists():
            return False
    scale_path = device_path / f"{prefix}_scale"
    return scale_path.exists()


def discover_iio_devices() -> List[Path]:
    """Return list of IIO device sysfs paths (e.g. .../iio:device0)."""
    if not IIO_BASE.exists():
        return []
    devices = []
    for path in IIO_BASE.iterdir():
        if path.is_dir() and path.name.startswith("iio:device"):
            devices.append(path)
    return sorted(devices, key=lambda p: p.name)


def find_accel_device(accel_path: Optional[str] = None) -> Optional[Path]:
    """
    Return IIO sysfs path for accelerometer.

    If accel_path is set, use it if it exists and has accel channels.
    Otherwise search for first device with in_accel_* channels.
    """
    if accel_path:
        p = Path(accel_path)
        if p.exists() and _has_channels(p, "in_accel"):
            return p
        logger.warning("Accel path %s missing or invalid", accel_path)
    for dev in discover_iio_devices():
        if _has_channels(dev, "in_accel"):
            return dev
    return None


def find_gyro_device(
    gyro_path: Optional[str] = None,
    accel_path: Optional[Path] = None,
) -> Optional[Path]:
    """
    Return IIO sysfs path for gyroscope.

    If gyro_path is set, use it if valid. Otherwise prefer accel_path
    if it has gyro channels (e.g. LSM6DS0), then any device with in_anglvel.
    """
    if gyro_path:
        p = Path(gyro_path)
        if p.exists() and _has_channels(p, "in_anglvel"):
            return p
        logger.warning("Gyro path %s missing or invalid", gyro_path)
    if accel_path and _has_channels(accel_path, "in_anglvel"):
        return accel_path
    for dev in discover_iio_devices():
        if _has_channels(dev, "in_anglvel"):
            return dev
    return None


def find_magnetometer_device(
    magnetometer_path: Optional[str] = None,
    accel_path: Optional[Path] = None,
) -> Optional[Path]:
    """
    Return IIO sysfs path for magnetometer.

    If magnetometer_path is set, use it if valid. Otherwise search for
    any device with in_magn_* channels.
    """
    if magnetometer_path:
        p = Path(magnetometer_path)
        if p.exists() and _has_channels(p, "in_magn"):
            return p
        logger.warning("Magnetometer path %s missing or invalid", magnetometer_path)
    if accel_path and _has_channels(accel_path, "in_magn"):
        return accel_path
    for dev in discover_iio_devices():
        if _has_channels(dev, "in_magn"):
            return dev
    return None


class IIOReader:
    """
    Read accelerometer, gyroscope, and optionally magnetometer from IIO sysfs.

    Units: accelerometer m/s^2, gyroscope deg/s, magnetometer microtesla (uT).
    """

    def __init__(
        self,
        accel_path: Optional[Path] = None,
        gyro_path: Optional[Path] = None,
        magnetometer_path: Optional[Path] = None,
    ) -> None:
        self.accel_path = accel_path
        self.gyro_path = gyro_path
        self.magnetometer_path = magnetometer_path
        self._accel_scale = 1.0
        self._accel_offset: List[float] = [0.0, 0.0, 0.0]
        self._gyro_scale = 1.0
        self._gyro_offset: List[float] = [0.0, 0.0, 0.0]
        self._magnetometer_scale = 1.0
        self._magnetometer_offset: List[float] = [0.0, 0.0, 0.0]
        if accel_path:
            self._read_accel_calibration()
        if gyro_path:
            self._read_gyro_calibration()
        if magnetometer_path:
            self._read_magnetometer_calibration()

    def _read_accel_calibration(self) -> None:
        """Load scale and optional offset for accelerometer."""
        if not self.accel_path:
            return
        scale_path = self.accel_path / "in_accel_scale"
        if scale_path.exists():
            self._accel_scale = _read_one(scale_path, 1.0)
        for i, axis in enumerate(("x", "y", "z")):
            offset_path = self.accel_path / f"in_accel_{axis}_offset"
            if offset_path.exists():
                self._accel_offset[i] = _read_one(offset_path, 0.0)
        logger.debug(
            "Accel scale=%s offset=%s",
            self._accel_scale,
            self._accel_offset,
        )

    def _read_gyro_calibration(self) -> None:
        """Load scale and optional offset for gyroscope."""
        if not self.gyro_path:
            return
        scale_path = self.gyro_path / "in_anglvel_scale"
        if scale_path.exists():
            self._gyro_scale = _read_one(scale_path, 1.0)
        for i, axis in enumerate(("x", "y", "z")):
            offset_path = self.gyro_path / f"in_anglvel_{axis}_offset"
            if offset_path.exists():
                self._gyro_offset[i] = _read_one(offset_path, 0.0)
        logger.debug(
            "Gyro scale=%s offset=%s",
            self._gyro_scale,
            self._gyro_offset,
        )

    def _read_magnetometer_calibration(self) -> None:
        """Load scale and optional offset for magnetometer."""
        if not self.magnetometer_path:
            return
        scale_path = self.magnetometer_path / "in_magn_scale"
        if scale_path.exists():
            self._magnetometer_scale = _read_one(scale_path, 1.0)
        for i, axis in enumerate(("x", "y", "z")):
            offset_path = self.magnetometer_path / f"in_magn_{axis}_offset"
            if offset_path.exists():
                self._magnetometer_offset[i] = _read_one(offset_path, 0.0)
        logger.debug(
            "Magnetometer scale=%s offset=%s",
            self._magnetometer_scale,
            self._magnetometer_offset,
        )

    def read_accel(self) -> Optional[Tuple[float, float, float]]:
        """
        Read accelerometer in m/s^2 (x, y, z).

        Returns None if no accel device or read error.
        """
        if not self.accel_path:
            return None
        try:
            raw_x = _read_one(self.accel_path / "in_accel_x_raw")
            raw_y = _read_one(self.accel_path / "in_accel_y_raw")
            raw_z = _read_one(self.accel_path / "in_accel_z_raw")
        except OSError:
            return None
        x = (raw_x + self._accel_offset[0]) * self._accel_scale
        y = (raw_y + self._accel_offset[1]) * self._accel_scale
        z = (raw_z + self._accel_offset[2]) * self._accel_scale
        return (x, y, z)

    def read_gyro(self) -> Optional[Tuple[float, float, float]]:
        """
        Read gyroscope in deg/s (x, y, z).

        IIO anglvel is often in rad/s; we convert to deg/s for imufusion.
        """
        if not self.gyro_path:
            return None
        try:
            raw_x = _read_one(self.gyro_path / "in_anglvel_x_raw")
            raw_y = _read_one(self.gyro_path / "in_anglvel_y_raw")
            raw_z = _read_one(self.gyro_path / "in_anglvel_z_raw")
        except OSError:
            return None
        x = (raw_x + self._gyro_offset[0]) * self._gyro_scale
        y = (raw_y + self._gyro_offset[1]) * self._gyro_scale
        z = (raw_z + self._gyro_offset[2]) * self._gyro_scale
        rad_to_deg = 57.29577951308232
        if self._gyro_scale < 0.1:
            x *= rad_to_deg
            y *= rad_to_deg
            z *= rad_to_deg
        return (x, y, z)

    def read_magnetometer(self) -> Optional[Tuple[float, float, float]]:
        """
        Read magnetometer in microtesla (uT) (x, y, z).

        Returns None if no magnetometer device or read error.
        """
        if not self.magnetometer_path:
            return None
        try:
            raw_x = _read_one(self.magnetometer_path / "in_magn_x_raw")
            raw_y = _read_one(self.magnetometer_path / "in_magn_y_raw")
            raw_z = _read_one(self.magnetometer_path / "in_magn_z_raw")
        except OSError:
            return None
        x = (raw_x + self._magnetometer_offset[0]) * self._magnetometer_scale
        y = (raw_y + self._magnetometer_offset[1]) * self._magnetometer_scale
        z = (raw_z + self._magnetometer_offset[2]) * self._magnetometer_scale
        return (x, y, z)
