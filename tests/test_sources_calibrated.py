"""
Unit tests for CalibratedIMUSource: applies calibration, feeds manager when set.
"""

from typing import Optional

from navit_daemon.calibration import Calibration
from navit_daemon.sources.base import IMUSource, IMUSample
from navit_daemon.sources.calibrated import CalibratedIMUSource


class FixedIMUSource(IMUSource):
    """Returns a fixed sample."""

    def __init__(
        self, accel: tuple, gyro: tuple, magnetometer: Optional[tuple] = None
    ) -> None:
        self._accel = accel
        self._gyro = gyro
        self._magnetometer = magnetometer

    def read(self) -> IMUSample:
        return (self._accel, self._gyro, self._magnetometer)


def test_calibrated_applies_bias_and_offset() -> None:
    inner = FixedIMUSource((0.0, 0.0, 9.81), (1.0, 2.0, 3.0), (10.0, 20.0, 30.0))
    cal = Calibration(
        gyro_bias=(0.5, 0.5, 0.5),
        accel_offset=(0.0, 0.0, 0.1),
        magnetometer_bias=(1.0, 2.0, 3.0),
    )
    source = CalibratedIMUSource(inner, lambda: cal)
    sample = source.read()
    assert sample is not None
    accel, gyro, magnetometer = sample
    assert accel == (0.0, 0.0, 9.71)
    assert gyro == (0.5, 1.5, 2.5)
    assert magnetometer == (9.0, 18.0, 27.0)


def test_calibrated_returns_none_when_inner_returns_none() -> None:
    class NoneSource(IMUSource):
        def read(self) -> IMUSample:
            return None

    source = CalibratedIMUSource(NoneSource(), lambda: Calibration())
    assert source.read() is None


def test_calibrated_with_manager_feeds_gyro_on_read() -> None:
    from navit_daemon.calibration_api import CalibrationManager

    inner = FixedIMUSource((0.0, 0.0, 9.81), (0.1, 0.2, 0.3), None)
    cal = Calibration()
    manager = CalibrationManager(cal)
    manager.start_gyro_calibration(seconds=0.1, sample_rate_hz=10.0)
    source = CalibratedIMUSource(inner, lambda: cal, manager=manager)
    for _ in range(10):
        source.read()
    assert manager.get_status()["calibration_status"] == "idle"
    assert manager.get_status()["gyro_bias"] == [0.1, 0.2, 0.3]
