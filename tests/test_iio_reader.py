"""
Unit tests for IIO reader: device discovery, identification, and reading.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from navit_daemon.iio_reader import (
    COMMON_IMU_PATTERNS,
    discover_iio_devices,
    find_accel_device,
    find_gyro_device,
    find_magnetometer_device,
    get_device_info,
    get_device_name,
    identify_imu_device,
    IIOReader,
)


class TestDeviceIdentification:
    """Device name and IMU type identification."""

    def test_get_device_name_from_name_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            device_path = Path(d) / "iio:device0"
            device_path.mkdir()
            (device_path / "name").write_text("mpu6050\n")
            assert get_device_name(device_path) == "mpu6050"

    def test_get_device_name_from_model_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            device_path = Path(d) / "iio:device0"
            device_path.mkdir()
            (device_path / "model").write_text("MPU6050\n")
            assert get_device_name(device_path) == "mpu6050"

    def test_get_device_name_returns_empty_if_missing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            device_path = Path(d) / "iio:device0"
            device_path.mkdir()
            assert get_device_name(device_path) == ""

    def test_identify_mpu6050(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            device_path = Path(d) / "iio:device0"
            device_path.mkdir()
            (device_path / "name").write_text("mpu6050\n")
            assert identify_imu_device(device_path) == "mpu6050"

    def test_identify_mpu9250(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            device_path = Path(d) / "iio:device0"
            device_path.mkdir()
            (device_path / "name").write_text("mpu9250\n")
            assert identify_imu_device(device_path) == "mpu9250"

    def test_identify_lsm6ds3(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            device_path = Path(d) / "iio:device0"
            device_path.mkdir()
            (device_path / "name").write_text("lsm6ds3\n")
            assert identify_imu_device(device_path) == "lsm6ds"

    def test_identify_bno055(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            device_path = Path(d) / "iio:device0"
            device_path.mkdir()
            (device_path / "name").write_text("bno055\n")
            assert identify_imu_device(device_path) == "bno055"

    def test_identify_unknown_device(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            device_path = Path(d) / "iio:device0"
            device_path.mkdir()
            (device_path / "name").write_text("unknown_sensor\n")
            assert identify_imu_device(device_path) is None

    def test_get_device_info(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            device_path = Path(d) / "iio:device0"
            device_path.mkdir()
            (device_path / "name").write_text("mpu6050\n")
            info = get_device_info(device_path)
            assert info["name"] == "mpu6050"
            assert info["imu_type"] == "mpu6050"
            assert "MPU6050" in info["description"]
            assert "path" in info


class TestDeviceDiscovery:
    """IIO device discovery."""

    @patch("navit_daemon.iio_reader.IIO_BASE")
    def test_discover_iio_devices(self, mock_base: Path) -> None:
        with tempfile.TemporaryDirectory() as d:
            base_path = Path(d) / "iio" / "devices"
            base_path.mkdir(parents=True)
            (base_path / "iio:device0").mkdir()
            (base_path / "iio:device1").mkdir()
            (base_path / "not_a_device").mkdir()
            mock_base.__class__ = Path
            mock_base.exists.return_value = True
            mock_base.iterdir.return_value = base_path.iterdir()
            devices = discover_iio_devices()
            assert len(devices) == 2
            assert any("iio:device0" in str(d) for d in devices)
            assert any("iio:device1" in str(d) for d in devices)

    @patch("navit_daemon.iio_reader.IIO_BASE")
    def test_discover_iio_devices_empty(self, mock_base: Path) -> None:
        mock_base.exists.return_value = False
        devices = discover_iio_devices()
        assert devices == []


class TestFindDevices:
    """Finding accel/gyro/magnetometer devices."""

    def test_find_accel_device_with_path(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            device_path = Path(d) / "iio:device0"
            device_path.mkdir()
            (device_path / "in_accel_x_raw").write_text("0\n")
            (device_path / "in_accel_y_raw").write_text("0\n")
            (device_path / "in_accel_z_raw").write_text("0\n")
            (device_path / "in_accel_scale").write_text("0.001\n")
            found = find_accel_device(str(device_path))
            assert found == device_path

    def test_find_accel_device_invalid_path(self) -> None:
        found = find_accel_device("/nonexistent/path")
        assert found is None

    def test_find_gyro_device_same_as_accel(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            device_path = Path(d) / "iio:device0"
            device_path.mkdir()
            (device_path / "in_accel_x_raw").write_text("0\n")
            (device_path / "in_accel_y_raw").write_text("0\n")
            (device_path / "in_accel_z_raw").write_text("0\n")
            (device_path / "in_accel_scale").write_text("0.001\n")
            (device_path / "in_anglvel_x_raw").write_text("0\n")
            (device_path / "in_anglvel_y_raw").write_text("0\n")
            (device_path / "in_anglvel_z_raw").write_text("0\n")
            (device_path / "in_anglvel_scale").write_text("0.001\n")
            found = find_gyro_device(None, device_path)
            assert found == device_path

    def test_find_magnetometer_device_same_as_accel(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            device_path = Path(d) / "iio:device0"
            device_path.mkdir()
            (device_path / "in_accel_x_raw").write_text("0\n")
            (device_path / "in_accel_y_raw").write_text("0\n")
            (device_path / "in_accel_z_raw").write_text("0\n")
            (device_path / "in_accel_scale").write_text("0.001\n")
            (device_path / "in_magn_x_raw").write_text("0\n")
            (device_path / "in_magn_y_raw").write_text("0\n")
            (device_path / "in_magn_z_raw").write_text("0\n")
            (device_path / "in_magn_scale").write_text("0.001\n")
            found = find_magnetometer_device(None, device_path)
            assert found == device_path


class TestIIOReader:
    """IIOReader reading and calibration."""

    def test_read_accel(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            device_path = Path(d) / "iio:device0"
            device_path.mkdir()
            (device_path / "in_accel_x_raw").write_text("1000\n")
            (device_path / "in_accel_y_raw").write_text("2000\n")
            (device_path / "in_accel_z_raw").write_text("3000\n")
            (device_path / "in_accel_scale").write_text("0.001\n")
            reader = IIOReader(accel_path=device_path)
            accel = reader.read_accel()
            assert accel is not None
            assert accel == (1.0, 2.0, 3.0)

    def test_read_gyro_converts_rad_to_deg(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            device_path = Path(d) / "iio:device0"
            device_path.mkdir()
            (device_path / "in_anglvel_x_raw").write_text("1000\n")
            (device_path / "in_anglvel_y_raw").write_text("2000\n")
            (device_path / "in_anglvel_z_raw").write_text("3000\n")
            (device_path / "in_anglvel_scale").write_text("0.001\n")
            reader = IIOReader(gyro_path=device_path)
            gyro = reader.read_gyro()
            assert gyro is not None
            rad_to_deg = 57.29577951308232
            assert gyro[0] == pytest.approx(1.0 * rad_to_deg)
            assert gyro[1] == pytest.approx(2.0 * rad_to_deg)
            assert gyro[2] == pytest.approx(3.0 * rad_to_deg)

    def test_read_magnetometer(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            device_path = Path(d) / "iio:device0"
            device_path.mkdir()
            (device_path / "in_magn_x_raw").write_text("1000\n")
            (device_path / "in_magn_y_raw").write_text("2000\n")
            (device_path / "in_magn_z_raw").write_text("3000\n")
            (device_path / "in_magn_scale").write_text("0.001\n")
            reader = IIOReader(magnetometer_path=device_path)
            mag = reader.read_magnetometer()
            assert mag is not None
            assert mag == (1.0, 2.0, 3.0)

    def test_read_accel_returns_none_if_no_device(self) -> None:
        reader = IIOReader()
        assert reader.read_accel() is None

    def test_read_gyro_returns_none_if_no_device(self) -> None:
        reader = IIOReader()
        assert reader.read_gyro() is None

    def test_read_magnetometer_returns_none_if_no_device(self) -> None:
        reader = IIOReader()
        assert reader.read_magnetometer() is None
