"""
Unit tests for config parsing: valid, invalid, and edge cases.
"""

import pytest

from navit_daemon.config import parse_args


class TestParseArgsDefaults:
    """Default values when no args given."""

    def test_empty_args_uses_defaults(self) -> None:
        config = parse_args([])
        assert config.source == "linux"
        assert config.gpsd_host == "127.0.0.1"
        assert config.gpsd_port == 2947
        assert config.remote_host == "0.0.0.0"
        assert config.remote_port == 2949
        assert config.nmea_host == "127.0.0.1"
        assert config.nmea_port == 2948
        assert config.imu_rate_hz == 100.0
        assert config.output_rate_hz == 5.0
        assert config.fusion_gain == 0.5
        assert config.accel_path is None
        assert config.gyro_path is None
        assert config.calibration_file is None
        assert config.calibration_port == 0
        assert config.debug is False

    def test_help_exits(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--help"])


class TestParseArgsValid:
    """Valid explicit arguments."""

    def test_source_remote(self) -> None:
        config = parse_args(["--source", "remote"])
        assert config.source == "remote"

    def test_source_auto(self) -> None:
        config = parse_args(["--source=auto"])
        assert config.source == "auto"

    def test_gpsd_host_port(self) -> None:
        config = parse_args(["--gpsd-host", "192.168.1.1", "--gpsd-port", "5000"])
        assert config.gpsd_host == "192.168.1.1"
        assert config.gpsd_port == 5000

    def test_remote_port(self) -> None:
        config = parse_args(["--remote-port", "3000"])
        assert config.remote_port == 3000

    def test_nmea_bind(self) -> None:
        config = parse_args(["--nmea-host", "0.0.0.0", "--nmea-port", "2950"])
        assert config.nmea_host == "0.0.0.0"
        assert config.nmea_port == 2950

    def test_imu_and_output_rate(self) -> None:
        config = parse_args(["--imu-rate", "200", "--output-rate", "10"])
        assert config.imu_rate_hz == 200.0
        assert config.output_rate_hz == 10.0

    def test_fusion_gain(self) -> None:
        config = parse_args(["--fusion-gain", "0.3"])
        assert config.fusion_gain == 0.3

    def test_accel_and_gyro_path(self) -> None:
        config = parse_args(
            [
                "--accel-path",
                "/sys/bus/iio/devices/iio:device0",
                "--gyro-path",
                "/sys/bus/iio/devices/iio:device1",
            ]
        )
        assert config.accel_path == "/sys/bus/iio/devices/iio:device0"
        assert config.gyro_path == "/sys/bus/iio/devices/iio:device1"

    def test_debug_flag(self) -> None:
        config = parse_args(["--debug"])
        assert config.debug is True

    def test_calibration_file_and_port(self) -> None:
        config = parse_args(
            ["--calibration-file", "/var/lib/cal.json", "--calibration-port", "2950"]
        )
        assert config.calibration_file == "/var/lib/cal.json"
        assert config.calibration_port == 2950


class TestParseArgsInvalidAndEdge:
    """Invalid and edge cases."""

    def test_invalid_source_rejected(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--source", "invalid"])

    def test_invalid_port_type(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--gpsd-port", "not_a_number"])

    def test_negative_port(self) -> None:
        config = parse_args(["--gpsd-port", "-1"])
        assert config.gpsd_port == -1

    def test_zero_fusion_gain(self) -> None:
        config = parse_args(["--fusion-gain", "0"])
        assert config.fusion_gain == 0.0

    def test_fusion_gain_one(self) -> None:
        config = parse_args(["--fusion-gain", "1"])
        assert config.fusion_gain == 1.0
