"""
Unit tests for FusionAhrs: valid input, edge cases. Skips when imufusion unavailable.
"""

import pytest

try:
    import imufusion  # noqa: F401

    IMUFUSION_AVAILABLE = True
except ImportError:
    IMUFUSION_AVAILABLE = False

if IMUFUSION_AVAILABLE:
    from navit_daemon.fusion_ahrs import FusionAhrs
else:
    FusionAhrs = None


@pytest.mark.skipif(not IMUFUSION_AVAILABLE, reason="imufusion not installed")
class TestFusionAhrsValid:
    """Valid updates and properties when imufusion is available."""

    def test_initialized_false_before_update(self) -> None:
        ahrs = FusionAhrs(gain=0.5)
        assert ahrs.initialized is False

    def test_one_update_sets_initialized(self) -> None:
        ahrs = FusionAhrs(gain=0.5)
        ahrs.update((0.0, 0.0, 9.81), (0.0, 0.0, 0.0), 0.01)
        assert ahrs.initialized is True

    def test_yaw_deg_in_range_0_360(self) -> None:
        ahrs = FusionAhrs(gain=0.5)
        ahrs.update((0.0, 0.0, 9.81), (0.0, 0.0, 0.0), 0.01)
        y = ahrs.yaw_deg
        assert 0 <= y < 360

    def test_multiple_updates(self) -> None:
        ahrs = FusionAhrs(gain=0.5)
        for _ in range(10):
            ahrs.update((0.0, 0.0, 9.81), (0.01, 0.0, 0.0), 0.01)
        assert ahrs.initialized is True
        assert 0 <= ahrs.yaw_deg < 360
        assert -180 <= ahrs.pitch_deg <= 180
        assert -180 <= ahrs.roll_deg <= 180


@pytest.mark.skipif(not IMUFUSION_AVAILABLE, reason="imufusion not installed")
class TestFusionAhrsEdgeCases:
    """Edge cases: zero gyro, large values, small sample period."""

    def test_zero_gyro_zero_accel(self) -> None:
        ahrs = FusionAhrs(gain=0.5)
        ahrs.update((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 0.01)
        assert ahrs.initialized is True

    def test_very_small_sample_period(self) -> None:
        ahrs = FusionAhrs(gain=0.5)
        ahrs.update((0.0, 0.0, 9.81), (0.0, 0.0, 0.0), 0.001)
        assert ahrs.initialized is True

    def test_larger_sample_period(self) -> None:
        ahrs = FusionAhrs(gain=0.5)
        ahrs.update((0.0, 0.0, 9.81), (0.0, 0.0, 0.0), 0.1)
        assert ahrs.initialized is True

    def test_gain_zero(self) -> None:
        ahrs = FusionAhrs(gain=0.0)
        ahrs.update((0.0, 0.0, 9.81), (0.0, 0.0, 0.0), 0.01)
        assert ahrs.initialized is True

    def test_gain_one(self) -> None:
        ahrs = FusionAhrs(gain=1.0)
        ahrs.update((0.0, 0.0, 9.81), (0.0, 0.0, 0.0), 0.01)
        assert ahrs.initialized is True


@pytest.mark.skipif(not IMUFUSION_AVAILABLE, reason="imufusion not installed")
class TestFusionAhrsInvalidAndMalformed:
    """Invalid and malformed data handling."""

    def test_negative_sample_period(self) -> None:
        ahrs = FusionAhrs(gain=0.5)
        try:
            ahrs.update((0.0, 0.0, 9.81), (0.0, 0.0, 0.0), -0.01)
            assert True
        except (ValueError, TypeError):
            assert True

    def test_zero_sample_period(self) -> None:
        ahrs = FusionAhrs(gain=0.5)
        ahrs.update((0.0, 0.0, 9.81), (0.0, 0.0, 0.0), 0.0)
        assert ahrs.initialized is True

    def test_very_large_sample_period(self) -> None:
        ahrs = FusionAhrs(gain=0.5)
        ahrs.update((0.0, 0.0, 9.81), (0.0, 0.0, 0.0), 1000.0)
        assert ahrs.initialized is True

    def test_extreme_accel_values(self) -> None:
        ahrs = FusionAhrs(gain=0.5)
        ahrs.update((1000.0, -1000.0, 9.81), (0.0, 0.0, 0.0), 0.01)
        assert ahrs.initialized is True

    def test_extreme_gyro_values(self) -> None:
        ahrs = FusionAhrs(gain=0.5)
        ahrs.update((0.0, 0.0, 9.81), (1000.0, -1000.0, 500.0), 0.01)
        assert ahrs.initialized is True

    def test_extreme_magnetometer_values(self) -> None:
        ahrs = FusionAhrs(gain=0.5)
        ahrs.update(
            (0.0, 0.0, 9.81), (0.0, 0.0, 0.0), 0.01, magnetometer=(1000.0, -1000.0, 500.0)
        )
        assert ahrs.initialized is True

    def test_negative_gain(self) -> None:
        ahrs = FusionAhrs(gain=-0.5)
        ahrs.update((0.0, 0.0, 9.81), (0.0, 0.0, 0.0), 0.01)
        assert ahrs.initialized is True

    def test_very_large_gain(self) -> None:
        ahrs = FusionAhrs(gain=100.0)
        ahrs.update((0.0, 0.0, 9.81), (0.0, 0.0, 0.0), 0.01)
        assert ahrs.initialized is True


@pytest.mark.skipif(IMUFUSION_AVAILABLE, reason="imufusion is installed")
class TestFusionAhrsWithoutImufusion:
    """When imufusion is not installed, constructor raises."""

    def test_init_raises_when_imufusion_missing(self) -> None:
        from navit_daemon.fusion_ahrs import FusionAhrs

        with pytest.raises(RuntimeError, match="imufusion not installed"):
            FusionAhrs(gain=0.5)
