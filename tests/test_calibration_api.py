"""
Unit tests for calibration API: request handling and CalibrationManager.
"""

import json
import tempfile
from pathlib import Path

from navit_daemon.calibration import Calibration
from navit_daemon.calibration_api import (
    CalibrationManager,
    _handle_request,
)


class TestHandleRequestGetCalibration:
    """get_calibration returns status dict."""

    def test_get_calibration_returns_current(self) -> None:
        cal = Calibration(gyro_bias=(0.1, 0.2, 0.3), accel_offset=(0.0, 0.0, 0.1))
        manager = CalibrationManager(cal)
        resp = _handle_request(manager, None, {"get_calibration": True}, 100.0)
        assert resp["gyro_bias"] == [0.1, 0.2, 0.3]
        assert resp["accel_offset"] == [0.0, 0.0, 0.1]
        assert resp["calibration_status"] == "idle"

    def test_get_calibration_when_collecting(self) -> None:
        cal = Calibration()
        manager = CalibrationManager(cal)
        manager.start_gyro_calibration(1.0, 10.0)
        resp = _handle_request(manager, None, {"get_calibration": True}, 10.0)
        assert resp["calibration_status"] == "collecting"
        assert resp["samples_needed"] == 10


class TestHandleRequestSetCalibration:
    """set_calibration updates manager and optionally saves file."""

    def test_set_calibration_gyro_only(self) -> None:
        cal = Calibration()
        manager = CalibrationManager(cal)
        resp = _handle_request(
            manager,
            None,
            {"set_calibration": {"gyro_bias": [0.5, -0.5, 0.0]}},
            100.0,
        )
        assert resp == {"ok": True}
        assert manager.get_calibration().gyro_bias == (0.5, -0.5, 0.0)

    def test_set_calibration_accel_only(self) -> None:
        cal = Calibration()
        manager = CalibrationManager(cal)
        resp = _handle_request(
            manager,
            None,
            {"set_calibration": {"accel_offset": [0.1, 0.0, 0.0]}},
            100.0,
        )
        assert resp == {"ok": True}
        assert manager.get_calibration().accel_offset == (0.1, 0.0, 0.0)

    def test_set_calibration_invalid_gyro_returns_error(self) -> None:
        cal = Calibration()
        manager = CalibrationManager(cal)
        resp = _handle_request(
            manager,
            None,
            {"set_calibration": {"gyro_bias": [1, 2]}},
            100.0,
        )
        assert "error" in resp

    def test_set_calibration_not_dict_returns_error(self) -> None:
        cal = Calibration()
        manager = CalibrationManager(cal)
        resp = _handle_request(manager, None, {"set_calibration": "x"}, 100.0)
        assert "error" in resp


class TestHandleRequestCalibrateGyro:
    """calibrate_gyro starts collection and returns samples_needed."""

    def test_calibrate_gyro_returns_collecting(self) -> None:
        cal = Calibration()
        manager = CalibrationManager(cal)
        resp = _handle_request(
            manager,
            None,
            {"calibrate_gyro": {"seconds": 2.0}},
            100.0,
        )
        assert resp["status"] == "collecting"
        assert resp["samples_needed"] == 200

    def test_calibrate_gyro_default_seconds(self) -> None:
        cal = Calibration()
        manager = CalibrationManager(cal)
        resp = _handle_request(manager, None, {"calibrate_gyro": {}}, 10.0)
        assert resp["samples_needed"] == 50

    def test_calibrate_gyro_clamped(self) -> None:
        cal = Calibration()
        manager = CalibrationManager(cal)
        resp = _handle_request(
            manager,
            None,
            {"calibrate_gyro": {"seconds": 0.1}},
            100.0,
        )
        assert resp["samples_needed"] >= 1


class TestHandleRequestInvalid:
    """Unknown or invalid requests return error."""

    def test_not_dict_returns_error(self) -> None:
        cal = Calibration()
        manager = CalibrationManager(cal)
        resp = _handle_request(manager, None, "string", 100.0)
        assert resp == {"error": "invalid request"}

    def test_unknown_request_returns_error(self) -> None:
        cal = Calibration()
        manager = CalibrationManager(cal)
        resp = _handle_request(manager, None, {"foo": "bar"}, 100.0)
        assert "error" in resp


class TestCalibrationManagerGyroCollection:
    """add_gyro_sample accumulates and sets bias when done."""

    def test_add_gyro_sample_until_done_sets_bias(self) -> None:
        cal = Calibration()
        manager = CalibrationManager(cal)
        manager.start_gyro_calibration(seconds=0.1, sample_rate_hz=10.0)
        for _ in range(10):
            manager.add_gyro_sample((0.1, 0.2, 0.3))
        assert manager.get_calibration().gyro_bias == (0.1, 0.2, 0.3)
        assert manager.get_status()["calibration_status"] == "idle"

    def test_add_gyro_sample_saves_to_file_when_set(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "cal.json"
            cal = Calibration()
            manager = CalibrationManager(cal, save_path=path)
            manager.start_gyro_calibration(seconds=0.1, sample_rate_hz=10.0)
            for _ in range(10):
                manager.add_gyro_sample((0.01, -0.01, 0.02))
            assert path.exists()
            data = json.loads(path.read_text())
            assert data["gyro_bias"] == [0.01, -0.01, 0.02]
