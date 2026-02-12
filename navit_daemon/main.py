"""
Main loop: fuse GPS and IMU from pluggable sources, output NMEA with AHRS heading.
"""

import logging
import select
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from navit_daemon.calibration import load_calibration
from navit_daemon.calibration_api import CalibrationManager, run_calibration_server
from navit_daemon.config import Config, parse_args
from navit_daemon.fusion_ahrs import FusionAhrs
from navit_daemon.gps_reader import GpsFix
from navit_daemon.nmea import fix_to_nmea
from navit_daemon.output_server import NmeaTcpServer
from navit_daemon.sources import create_linux_sources, create_remote_source
from navit_daemon.sources.base import GPSSource, IMUSource
from navit_daemon.sources.calibrated import CalibratedIMUSource

logger = logging.getLogger(__name__)

_shutdown = False


def _signal_handler(signum: int, frame: Optional[object]) -> None:
    global _shutdown
    _shutdown = True


def run(config: Config) -> int:  # noqa: C901
    """
    Run the daemon: IMU fusion + GPS, output NMEA on TCP.

    Returns exit code (0 = success).
    """
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    log_level = logging.DEBUG if config.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    imu_source: Optional[IMUSource] = None
    gps_source: Optional[GPSSource] = None
    remote_source = None

    source_mode = config.source
    if source_mode == "auto":
        sources = create_linux_sources(
            config.gpsd_host,
            config.gpsd_port,
            config.accel_path,
            config.gyro_path,
        )
        if sources:
            source_mode = "linux"
            imu_source, gps_source = sources
            logger.info("Using Linux source (IIO + gpsd)")
        else:
            remote_source = create_remote_source(config.remote_host, config.remote_port)
            if remote_source:
                source_mode = "remote"
                imu_source = gps_source = remote_source
                logger.info("Using remote source (waiting for Android/iOS client)")
            else:
                logger.error("Auto: no Linux IIO and remote bind failed")
                return 1
    elif source_mode == "linux":
        sources = create_linux_sources(
            config.gpsd_host,
            config.gpsd_port,
            config.accel_path,
            config.gyro_path,
        )
        if not sources:
            logger.error(
                "IIO accel or gyro not found. Use --source=remote for Android/iOS."
            )
            return 1
        imu_source, gps_source = sources
    else:
        remote_source = create_remote_source(config.remote_host, config.remote_port)
        if not remote_source:
            logger.error("Remote source bind failed")
            return 1
        imu_source = gps_source = remote_source

    cal_path = Path(config.calibration_file) if config.calibration_file else None
    calibration = load_calibration(cal_path)
    cal_manager = CalibrationManager(calibration, save_path=cal_path)
    imu_source = CalibratedIMUSource(
        imu_source,
        cal_manager.get_calibration,
        manager=cal_manager,
    )

    cal_thread = None
    if config.calibration_port > 0:
        cal_thread = threading.Thread(
            target=run_calibration_server,
            args=(
                cal_manager,
                "127.0.0.1",
                config.calibration_port,
                cal_path,
                config.imu_rate_hz,
                lambda: _shutdown,
            ),
            daemon=True,
        )
        cal_thread.start()

    try:
        fusion = FusionAhrs(gain=config.fusion_gain)
    except RuntimeError as e:
        logger.error("%s", e)
        if remote_source:
            remote_source.stop()
        return 1

    server = NmeaTcpServer(host=config.nmea_host, port=config.nmea_port)
    if not server.start():
        if remote_source:
            remote_source.stop()
        return 1

    imu_dt = 1.0 / config.imu_rate_hz
    output_interval = 1.0 / config.output_rate_hz
    last_output_time = 0.0
    last_imu_time = time.monotonic()
    current_fix: Optional[GpsFix] = None

    try:
        while not _shutdown:
            now = time.monotonic()

            if server.get_socket():
                r, _, _ = select.select(
                    [server.get_socket()],
                    [],
                    [],
                    min(imu_dt, output_interval, 0.1),
                )
                if r:
                    server.accept_new()

            while (time.monotonic() - last_imu_time) >= imu_dt and not _shutdown:
                sample = imu_source.read() if imu_source else None
                if sample:
                    accel, gyro = sample
                    fusion.update(accel, gyro, imu_dt)
                last_imu_time += imu_dt
            if last_imu_time < now:
                last_imu_time = now

            if (now - last_output_time) >= output_interval:
                last_output_time = now
                if gps_source:
                    current_fix = gps_source.get_fix()
                heading = fusion.yaw_deg if fusion.initialized else 0.0
                if current_fix and current_fix.valid:
                    gga, rmc = fix_to_nmea(
                        current_fix,
                        heading,
                        time_iso=current_fix.time_iso,
                    )
                    if gga:
                        server.send_nmea(gga)
                    if rmc:
                        server.send_nmea(rmc)

    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
        if remote_source:
            remote_source.stop()

    return 0


def main() -> None:
    """Entry point for the navit-daemon script."""
    config = parse_args()
    sys.exit(run(config))


if __name__ == "__main__":
    main()
