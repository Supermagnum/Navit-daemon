"""
Remote data source: TCP server accepting JSON from Android/iOS or other clients.

Protocol: one JSON object per line (newline-delimited).
- IMU: {"accel":[x,y,z],"gyro":[x,y,z]}  (accel m/s^2, gyro deg/s)
- GPS: {"lat":float,"lon":float,"alt":float,"speed_ms":float,"track":float,
        "time_iso":str|null}
- Combined: both keys in one object.
"""

import json
import logging
import socket
import threading
from typing import Optional, Tuple

from navit_daemon.gps_reader import GpsFix
from navit_daemon.sources.base import GPSSource, IMUSource, IMUSample

logger = logging.getLogger(__name__)


class RemoteSource(IMUSource, GPSSource):
    """
    Single source that provides both IMU and GPS from a remote TCP client.

    Start the server with start(); then read() and get_fix() return the
    latest data received from the client.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 2949) -> None:
        self._host = host
        self._port = port
        self._lock = threading.Lock()
        self._last_accel: Optional[Tuple[float, float, float]] = None
        self._last_gyro: Optional[Tuple[float, float, float]] = None
        self._last_fix: Optional[GpsFix] = None
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._shutdown = False

    def start(self) -> bool:
        """Bind and start the listener thread. Return True on success."""
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.bind((self._host, self._port))
            self._sock.listen(1)
            self._sock.settimeout(1.0)
            self._thread = threading.Thread(target=self._accept_loop, daemon=True)
            self._thread.start()
            logger.info(
                "Remote source listening on %s:%s (Android/iOS clients)",
                self._host,
                self._port,
            )
            return True
        except OSError as e:
            logger.error("Remote source bind failed: %s", e)
            return False

    def stop(self) -> None:
        """Stop the listener and close the socket."""
        self._shutdown = True
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _accept_loop(self) -> None:  # noqa: C901
        while not self._shutdown and self._sock:
            try:
                client, addr = self._sock.accept()
                logger.info("Remote client connected from %s", addr)
                try:
                    client.settimeout(5.0)
                    with client.makefile(mode="r", encoding="utf-8") as f:
                        for line in f:
                            if self._shutdown:
                                break
                            line = line.strip()
                            if not line:
                                continue
                            self._parse_line(line)
                except (
                    ConnectionResetError,
                    BrokenPipeError,
                    json.JSONDecodeError,
                ) as e:
                    logger.debug("Remote client error: %s", e)
                finally:
                    try:
                        client.close()
                    except OSError:
                        pass
                    logger.info("Remote client disconnected")
            except socket.timeout:
                continue
            except OSError:
                if not self._shutdown:
                    logger.debug("Remote accept error")
                break

    def _parse_line(self, line: str) -> None:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return
        with self._lock:
            if "accel" in data and "gyro" in data:
                a = data["accel"]
                g = data["gyro"]
                if (
                    isinstance(a, (list, tuple))
                    and len(a) >= 3
                    and isinstance(g, (list, tuple))
                    and len(g) >= 3
                ):
                    self._last_accel = (float(a[0]), float(a[1]), float(a[2]))
                    self._last_gyro = (float(g[0]), float(g[1]), float(g[2]))
            if "lat" in data and "lon" in data:
                lat = float(data["lat"])
                lon = float(data["lon"])
                alt = float(data.get("alt", 0))
                speed_ms = float(data.get("speed_ms", 0))
                track = float(data.get("track", 0))
                time_iso = data.get("time_iso")
                if isinstance(time_iso, str):
                    pass
                else:
                    time_iso = None
                self._last_fix = GpsFix(
                    lat=lat,
                    lon=lon,
                    alt=alt,
                    speed_ms=speed_ms,
                    track=track,
                    valid=True,
                    mode=2,
                    time_iso=time_iso,
                )

    def read(self) -> IMUSample:
        with self._lock:
            if self._last_accel and self._last_gyro:
                return (self._last_accel, self._last_gyro)
        return None

    def get_fix(self) -> Optional[GpsFix]:
        with self._lock:
            return self._last_fix


def create_remote_source(host: str, port: int) -> Optional[RemoteSource]:
    """Create and start the remote source. Returns None on bind failure."""
    source = RemoteSource(host=host, port=port)
    if source.start():
        return source
    return None
