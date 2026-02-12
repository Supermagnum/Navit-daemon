"""
Unit tests for calibration: apply, serialisation, load/save.
"""

import tempfile
from pathlib import Path

import pytest

from navit_daemon.calibration import (
    Calibration,
    load_calibration,
    save_calibration,
)


class TestCalibrationApply:
    """apply_gyro and apply_accel subtract bias/offset."""

    def test_apply_gyro_default_zero(self) -> None:
        cal = Calibration()
        assert cal.apply_gyro((1.0, 2.0, 3.0)) == (1.0, 2.0, 3.0)

    def test_apply_gyro_subtracts_bias(self) -> None:
        cal = Calibration(gyro_bias=(0.1, -0.2, 0.05))
        assert cal.apply_gyro((1.0, 2.0, 3.0)) == (0.9, 2.2, 2.95)

    def test_apply_accel_default_zero(self) -> None:
        cal = Calibration()
        assert cal.apply_accel((0.0, 0.0, 9.81)) == (0.0, 0.0, 9.81)

    def test_apply_accel_subtracts_offset(self) -> None:
        cal = Calibration(accel_offset=(0.1, 0.0, 0.2))
        out = cal.apply_accel((0.0, 0.0, 9.81))
        assert out[0] == -0.1 and out[1] == 0.0
        assert out[2] == pytest.approx(9.61)


class TestCalibrationFromDict:
    """from_dict and to_dict round-trip and handle invalid input."""

    def test_from_dict_valid(self) -> None:
        data = {"gyro_bias": [0.1, 0.2, 0.3], "accel_offset": [1.0, 0.0, 0.0]}
        cal = Calibration.from_dict(data)
        assert cal.gyro_bias == (0.1, 0.2, 0.3)
        assert cal.accel_offset == (1.0, 0.0, 0.0)

    def test_from_dict_partial(self) -> None:
        cal = Calibration.from_dict({"gyro_bias": [1, 2, 3]})
        assert cal.gyro_bias == (1.0, 2.0, 3.0)
        assert cal.accel_offset == (0.0, 0.0, 0.0)

    def test_from_dict_invalid_returns_default(self) -> None:
        cal = Calibration.from_dict("not a dict")
        assert cal.gyro_bias == (0.0, 0.0, 0.0)
        assert cal.accel_offset == (0.0, 0.0, 0.0)

    def test_from_dict_short_list_returns_default(self) -> None:
        cal = Calibration.from_dict({"gyro_bias": [1, 2]})
        assert cal.gyro_bias == (0.0, 0.0, 0.0)

    def test_to_dict_roundtrip(self) -> None:
        cal = Calibration(gyro_bias=(0.1, -0.1, 0.0), accel_offset=(0.0, 0.0, 0.1))
        data = cal.to_dict()
        cal2 = Calibration.from_dict(data)
        assert cal2.gyro_bias == cal.gyro_bias
        assert cal2.accel_offset == cal.accel_offset


class TestLoadSaveCalibration:
    """load_calibration and save_calibration with files."""

    def test_load_missing_path_returns_default(self) -> None:
        cal = load_calibration(Path("/nonexistent/path/cal.json"))
        assert cal.gyro_bias == (0.0, 0.0, 0.0)
        assert cal.accel_offset == (0.0, 0.0, 0.0)

    def test_load_none_returns_default(self) -> None:
        cal = load_calibration(None)
        assert cal.gyro_bias == (0.0, 0.0, 0.0)

    def test_save_and_load_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "cal.json"
            cal = Calibration(
                gyro_bias=(0.01, -0.02, 0.01), accel_offset=(0.0, 0.0, 0.0)
            )
            assert save_calibration(path, cal) is True
            loaded = load_calibration(path)
            assert loaded.gyro_bias == cal.gyro_bias
            assert loaded.accel_offset == cal.accel_offset

    def test_load_invalid_json_returns_default(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json")
            path = Path(f.name)
        try:
            cal = load_calibration(path)
            assert cal.gyro_bias == (0.0, 0.0, 0.0)
        finally:
            path.unlink()
