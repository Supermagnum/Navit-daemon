"""
Calibration control API: TCP server for get/set calibration and gyro bias.

Protocol: one JSON object per line.
- get_calibration: returns gyro_bias, accel_offset, calibration_status.
- set_calibration: sets bias/offset, optional file save.
- calibrate_gyro: start collection; when done bias is set from mean.
Main loop feeds gyro via manager.add_gyro_sample(gyro).
"""

import json
import logging
import socket
import threading
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from navit_daemon.calibration import Calibration, save_calibration

logger = logging.getLogger(__name__)


class CalibrationManager:
    """
    Thread-safe calibration state and gyro bias collection.

    When calibrate_gyro(seconds) is called, the main loop should call
    add_gyro_sample(gyro) each cycle; after enough samples the mean is
    set as gyro_bias and collection stops.
    """

    def __init__(
        self,
        calibration: Calibration,
        save_path: Optional[Path] = None,
    ) -> None:
        self._calibration = calibration
        self._save_path = save_path
        self._lock = threading.Lock()
        self._gyro_samples: List[Tuple[float, float, float]] = []
        self._samples_needed = 0

    def get_calibration(self) -> Calibration:
        return self._calibration

    def set_calibration(
        self,
        gyro_bias: Optional[Tuple[float, float, float]] = None,
        accel_offset: Optional[Tuple[float, float, float]] = None,
        magnetometer_bias: Optional[Tuple[float, float, float]] = None,
    ) -> None:
        with self._lock:
            if gyro_bias is not None:
                self._calibration.gyro_bias = gyro_bias
            if accel_offset is not None:
                self._calibration.accel_offset = accel_offset
            if magnetometer_bias is not None:
                self._calibration.magnetometer_bias = magnetometer_bias

    def start_gyro_calibration(self, seconds: float, sample_rate_hz: float) -> int:
        """
        Start collecting gyro samples for bias estimation.

        Returns number of samples needed (main loop should call add_gyro_sample
        until done).
        """
        with self._lock:
            self._gyro_samples = []
            self._samples_needed = max(1, int(seconds * sample_rate_hz))
            return self._samples_needed

    def add_gyro_sample(self, gyro: Tuple[float, float, float]) -> bool:
        """
        Add one gyro sample when collecting. When enough collected, set bias to mean.

        Returns True if calibration was just finished (bias updated).
        """
        with self._lock:
            if self._samples_needed <= 0:
                return False
            self._gyro_samples.append(gyro)
            if len(self._gyro_samples) >= self._samples_needed:
                n = len(self._gyro_samples)
                bx = sum(s[0] for s in self._gyro_samples) / n
                by = sum(s[1] for s in self._gyro_samples) / n
                bz = sum(s[2] for s in self._gyro_samples) / n
                self._calibration.gyro_bias = (bx, by, bz)
                self._gyro_samples = []
                self._samples_needed = 0
                logger.info(
                    "Gyro calibration done: bias=(%.4f, %.4f, %.4f) deg/s",
                    bx,
                    by,
                    bz,
                )
                if self._save_path:
                    save_calibration(self._save_path, self._calibration)
                return True
            return False

    def get_status(self) -> dict:
        """Current calibration and collection status for API response."""
        with self._lock:
            status: str = "collecting" if self._samples_needed > 0 else "idle"
            return {
                "gyro_bias": list(self._calibration.gyro_bias),
                "accel_offset": list(self._calibration.accel_offset),
                "magnetometer_bias": list(self._calibration.magnetometer_bias),
                "calibration_status": status,
                "samples_collected": len(self._gyro_samples),
                "samples_needed": self._samples_needed,
            }


def _handle_request(  # noqa: C901
    manager: CalibrationManager,
    save_path: Optional[Path],
    request: dict,
    sample_rate_hz: float,
) -> dict:
    """Process one API request; return response dict."""
    if not isinstance(request, dict):
        return {"error": "invalid request"}

    if request.get("get_calibration"):
        return manager.get_status()

    set_cal = request.get("set_calibration")
    if set_cal is not None:
        if not isinstance(set_cal, dict):
            return {"error": "set_calibration must be an object"}
        gyro_bias = set_cal.get("gyro_bias")
        accel_offset = set_cal.get("accel_offset")
        magnetometer_bias = set_cal.get("magnetometer_bias")
        if gyro_bias is not None:
            if not isinstance(gyro_bias, (list, tuple)) or len(gyro_bias) < 3:
                return {"error": "gyro_bias must be [x,y,z]"}
            try:
                gyro_bias = (float(gyro_bias[0]), float(gyro_bias[1]), float(gyro_bias[2]))
            except (TypeError, ValueError):
                return {"error": "gyro_bias must be [x,y,z]"}
        if accel_offset is not None:
            if not isinstance(accel_offset, (list, tuple)) or len(accel_offset) < 3:
                return {"error": "accel_offset must be [x,y,z]"}
            try:
                accel_offset = (
                    float(accel_offset[0]),
                    float(accel_offset[1]),
                    float(accel_offset[2]),
                )
            except (TypeError, ValueError):
                return {"error": "accel_offset must be [x,y,z]"}
        if magnetometer_bias is not None:
            if (
                not isinstance(magnetometer_bias, (list, tuple))
                or len(magnetometer_bias) < 3
            ):
                return {"error": "magnetometer_bias must be [x,y,z]"}
            try:
                magnetometer_bias = (
                    float(magnetometer_bias[0]),
                    float(magnetometer_bias[1]),
                    float(magnetometer_bias[2]),
                )
            except (TypeError, ValueError):
                return {"error": "magnetometer_bias must be [x,y,z]"}
        manager.set_calibration(
            gyro_bias=gyro_bias,
            accel_offset=accel_offset,
            magnetometer_bias=magnetometer_bias,
        )
        if save_path:
            save_calibration(save_path, manager.get_calibration())
        return {"ok": True}

    cal_gyro = request.get("calibrate_gyro")
    if cal_gyro is not None:
        if not isinstance(cal_gyro, dict):
            return {"error": "calibrate_gyro must be an object"}
        seconds = float(cal_gyro.get("seconds", 5.0))
        seconds = max(0.5, min(60.0, seconds))
        needed = manager.start_gyro_calibration(seconds, sample_rate_hz)
        return {"status": "collecting", "samples_needed": needed}

    return {"error": "unknown request"}


def run_calibration_server(  # noqa: C901
    manager: CalibrationManager,
    host: str,
    port: int,
    save_path: Optional[Path],
    sample_rate_hz: float,
    shutdown: Callable[[], bool],
) -> None:
    """
    Run TCP server that handles calibration API until shutdown() returns True.

    Call from a dedicated thread. Each client connection: one JSON line in,
    one JSON line out per request.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, port))
    except OSError as e:
        logger.error("Calibration API bind failed %s:%s: %s", host, port, e)
        return
    sock.listen(1)
    sock.settimeout(1.0)
    logger.info("Calibration API on %s:%s", host, port)

    while not shutdown():
        try:
            client, addr = sock.accept()
        except socket.timeout:
            continue
        except OSError:
            if shutdown():
                break
            continue
        try:
            client.settimeout(10.0)
            with client.makefile(mode="rw", encoding="utf-8") as f:
                for line in f:
                    if shutdown():
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        request = json.loads(line)
                    except json.JSONDecodeError:
                        response = {"error": "invalid JSON"}
                    else:
                        response = _handle_request(
                            manager, save_path, request, sample_rate_hz
                        )
                    f.write(json.dumps(response) + "\n")
                    f.flush()
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            logger.debug("Calibration API client error: %s", e)
        finally:
            try:
                client.close()
            except OSError:
                pass

    try:
        sock.close()
    except OSError:
        pass
