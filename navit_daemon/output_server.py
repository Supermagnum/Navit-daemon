"""
TCP server that streams NMEA sentences to clients (e.g. gpsd or Navit).
"""

import logging
import socket
import threading
from typing import List, Optional

logger = logging.getLogger(__name__)


class NmeaTcpServer:
    """
    Simple TCP server that sends NMEA lines to connected clients.

    Thread-safe: call send_nmea() from any thread.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 2948) -> None:
        self._host = host
        self._port = port
        self._sock: Optional[socket.socket] = None
        self._clients: List[socket.socket] = []
        self._lock = threading.Lock()

    def start(self) -> bool:
        """Bind and listen; return True on success."""
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.bind((self._host, self._port))
            self._sock.listen(4)
            self._sock.setblocking(False)
            logger.info("NMEA TCP server listening on %s:%s", self._host, self._port)
            return True
        except OSError as e:
            logger.error("NMEA server bind failed: %s", e)
            return False

    def stop(self) -> None:
        """Close server and all client connections."""
        with self._lock:
            for c in self._clients:
                try:
                    c.close()
                except OSError:
                    pass
            self._clients.clear()
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def accept_new(self) -> None:
        """Accept pending connections (non-blocking). Call from main loop."""
        if not self._sock:
            return
        try:
            client, _ = self._sock.accept()
            with self._lock:
                self._clients.append(client)
            logger.info("NMEA client connected (total %d)", len(self._clients))
        except BlockingIOError:
            pass
        except OSError as e:
            logger.debug("accept error: %s", e)

    def send_nmea(self, line: str) -> None:
        """
        Send one NMEA line to all connected clients.

        line should end with \\r\\n (e.g. from nmea.build_*).
        """
        if not line:
            return
        if not line.endswith("\n"):
            line = line.rstrip() + "\r\n"
        data = line.encode("ascii", errors="replace")
        with self._lock:
            dead = []
            for c in self._clients:
                try:
                    c.sendall(data)
                except OSError:
                    dead.append(c)
            for c in dead:
                self._clients.remove(c)

    def get_socket(self) -> Optional[socket.socket]:
        """Return the server socket for select()."""
        return self._sock
