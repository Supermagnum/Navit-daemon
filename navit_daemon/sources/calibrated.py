"""
IMU source wrapper that applies calibration (gyro bias, accel offset).
"""

from typing import Callable, Optional, TYPE_CHECKING

from navit_daemon.calibration import Calibration
from navit_daemon.sources.base import IMUSource, IMUSample

if TYPE_CHECKING:
    from navit_daemon.calibration_api import CalibrationManager


class CalibratedIMUSource(IMUSource):
    """
    Wraps an IMUSource and applies calibration to each sample.

    The calibration object is read on each read(); updates (e.g. from
    the calibration API) take effect immediately.
    When manager is set and collecting gyro bias, raw gyro is fed to it.
    """

    def __init__(
        self,
        inner: IMUSource,
        get_calibration: Callable[[], Calibration],
        manager: Optional["CalibrationManager"] = None,
    ) -> None:
        self._inner = inner
        self._get_calibration = get_calibration
        self._manager = manager

    def read(self) -> IMUSample:
        sample = self._inner.read()
        if sample is None:
            return None
        accel, gyro = sample
        if self._manager:
            self._manager.add_gyro_sample(gyro)
        cal = self._get_calibration()
        return (cal.apply_accel(accel), cal.apply_gyro(gyro))
