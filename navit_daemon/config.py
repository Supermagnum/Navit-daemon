"""
Configuration defaults and parsing for navit-daemon.
"""

import argparse
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Runtime configuration."""

    source: str = "linux"
    gpsd_host: str = "127.0.0.1"
    gpsd_port: int = 2947
    remote_host: str = "0.0.0.0"
    remote_port: int = 2949
    nmea_host: str = "127.0.0.1"
    nmea_port: int = 2948
    imu_rate_hz: float = 100.0
    output_rate_hz: float = 5.0
    fusion_gain: float = 0.5
    accel_path: Optional[str] = None
    gyro_path: Optional[str] = None
    calibration_file: Optional[str] = None
    calibration_port: int = 0
    debug: bool = False


def parse_args(args: Optional[list] = None) -> Config:
    """Parse command-line arguments into Config."""
    parser = argparse.ArgumentParser(
        description="Fuse GPS (gpsd) and IMU (IIO) for Navit; output NMEA with heading."
    )
    parser.add_argument(
        "--source",
        choices=("linux", "remote", "auto"),
        default="linux",
        help="Source: linux (IIO+gpsd), remote (TCP), auto (default: linux)",
    )
    parser.add_argument(
        "--remote-port",
        type=int,
        default=2949,
        help="Port for remote source (default: 2949)",
    )
    parser.add_argument(
        "--remote-host",
        default="0.0.0.0",
        help="Bind address for remote source (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--gpsd-host",
        default="127.0.0.1",
        help="gpsd host (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--gpsd-port",
        type=int,
        default=2947,
        help="gpsd port (default: 2947)",
    )
    parser.add_argument(
        "--nmea-host",
        default="127.0.0.1",
        help="Bind address for NMEA TCP server (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--nmea-port",
        type=int,
        default=2948,
        help="Port for NMEA TCP server (default: 2948)",
    )
    parser.add_argument(
        "--imu-rate",
        type=float,
        default=100.0,
        help="IMU sample rate in Hz (default: 100)",
    )
    parser.add_argument(
        "--output-rate",
        type=float,
        default=5.0,
        help="NMEA output rate in Hz (default: 5)",
    )
    parser.add_argument(
        "--fusion-gain",
        type=float,
        default=0.5,
        help="AHRS fusion gain 0-1 (default: 0.5)",
    )
    parser.add_argument(
        "--accel-path",
        default=None,
        help="IIO sysfs path for accelerometer (e.g. /sys/bus/iio/devices/iio:device0)",
    )
    parser.add_argument(
        "--gyro-path",
        default=None,
        help="IIO sysfs path for gyroscope (default: auto-detect)",
    )
    parser.add_argument(
        "--calibration-file",
        default=None,
        help="Load/save calibration from JSON file (optional)",
    )
    parser.add_argument(
        "--calibration-port",
        type=int,
        default=0,
        help="TCP port for calibration API (0=disabled, default 0)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parsed = parser.parse_args(args)
    return Config(
        source=parsed.source,
        gpsd_host=parsed.gpsd_host,
        gpsd_port=parsed.gpsd_port,
        remote_host=parsed.remote_host,
        remote_port=parsed.remote_port,
        nmea_host=parsed.nmea_host,
        nmea_port=parsed.nmea_port,
        imu_rate_hz=parsed.imu_rate,
        output_rate_hz=parsed.output_rate,
        fusion_gain=parsed.fusion_gain,
        accel_path=parsed.accel_path,
        gyro_path=parsed.gyro_path,
        calibration_file=parsed.calibration_file,
        calibration_port=parsed.calibration_port,
        debug=parsed.debug,
    )
