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


def test_calibrated_none_magnetometer_returns_none() -> None:
    """Test that None magnetometer is preserved even when calibration has bias."""
    inner = FixedIMUSource((0.0, 0.0, 9.81), (1.0, 2.0, 3.0), None)
    cal = Calibration(magnetometer_bias=(1.0, 2.0, 3.0))
    source = CalibratedIMUSource(inner, lambda: cal)
    sample = source.read()
    assert sample is not None
    accel, gyro, magnetometer = sample
    assert magnetometer is None


def test_calibrated_extreme_bias_values() -> None:
    """Test calibration with extreme bias/offset values."""
    inner = FixedIMUSource((0.0, 0.0, 9.81), (1.0, 2.0, 3.0), (10.0, 20.0, 30.0))
    cal = Calibration(
        gyro_bias=(1000.0, -1000.0, 500.0),
        accel_offset=(100.0, -100.0, 50.0),
        magnetometer_bias=(1000.0, -1000.0, 500.0),
    )
    source = CalibratedIMUSource(inner, lambda: cal)
    sample = source.read()
    assert sample is not None
    accel, gyro, magnetometer = sample
    assert gyro == (-999.0, 1002.0, -497.0)
    assert accel == (-100.0, 100.0, -40.19)
    assert magnetometer == (-990.0, 1020.0, -470.0)


def test_calibrated_zero_values() -> None:
    """Test calibration with zero input values."""
    inner = FixedIMUSource((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    cal = Calibration(
        gyro_bias=(0.1, 0.2, 0.3),
        accel_offset=(0.1, 0.2, 0.3),
        magnetometer_bias=(0.1, 0.2, 0.3),
    )
    source = CalibratedIMUSource(inner, lambda: cal)
    sample = source.read()
    assert sample is not None
    accel, gyro, magnetometer = sample
    assert gyro == (-0.1, -0.2, -0.3)
    assert accel == (-0.1, -0.2, -0.3)
    assert magnetometer == (-0.1, -0.2, -0.3)


def test_calibrated_dynamic_calibration_change() -> None:
    """Test that calibration changes are reflected immediately."""
    inner = FixedIMUSource((1.0, 2.0, 3.0), (1.0, 2.0, 3.0), (10.0, 20.0, 30.0))
    cal = Calibration()
    source = CalibratedIMUSource(inner, lambda: cal)
    sample1 = source.read()
    assert sample1 is not None
    assert sample1[0] == (1.0, 2.0, 3.0)
    cal.accel_offset = (0.5, 0.5, 0.5)
    sample2 = source.read()
    assert sample2 is not None
    assert sample2[0] == (0.5, 1.5, 2.5)
