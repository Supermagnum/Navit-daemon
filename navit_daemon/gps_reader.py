"""
GPS position and velocity from gpsd.
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class GpsFix:
    """Current GPS fix: position, speed, track (heading), and validity."""

    lat: float
    lon: float
    alt: float
    speed_ms: float
    track: float
    valid: bool
    mode: int  # 0=no fix, 1=2D, 2=3D
    time_iso: Optional[str] = None


def connect_gpsd(host: str = "127.0.0.1", port: int = 2947) -> Optional[object]:
    """
    Connect to gpsd and return a gpsd connection object.

    Returns None on failure. Caller should use gpsd-py3: gpsd.connect(host, port).
    """
    try:
        import gpsd  # type: ignore[import-untyped]

        gpsd.connect(host=host, port=port)
        return gpsd  # type: ignore[no-any-return]
    except Exception as e:
        logger.error("gpsd connect failed: %s", e)
        return None


def get_current_fix(gpsd_module: Optional[object]) -> Optional[GpsFix]:  # noqa: C901
    """
    Get current fix from gpsd.

    Returns a GpsFix or None if no fix / error.
    """
    if gpsd_module is None:
        return None
    try:
        packet = gpsd_module.get_current()  # type: ignore[attr-defined]
        if packet is None:
            return None
        if packet.mode < 1:
            return GpsFix(
                lat=0.0,
                lon=0.0,
                alt=0.0,
                speed_ms=0.0,
                track=0.0,
                valid=False,
                mode=0,
                time_iso=None,
            )
        lat, lon = packet.position()
        alt = getattr(packet, "alt", None) or 0.0
        speed = getattr(packet, "hspeed", None)
        if speed is None:
            speed = getattr(packet, "speed", None) or 0.0
        track = getattr(packet, "track", None) or 0.0
        time_iso = None
        if hasattr(packet, "time") and packet.time:
            try:
                from datetime import datetime

                t = packet.time
                if isinstance(t, (int, float)):
                    time_iso = datetime.utcfromtimestamp(t).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    )
                else:
                    time_iso = str(t)
            except Exception:
                pass
        return GpsFix(
            lat=lat,
            lon=lon,
            alt=alt,
            speed_ms=float(speed) if speed is not None else 0.0,
            track=float(track),
            valid=True,
            mode=packet.mode,
            time_iso=time_iso,
        )
    except Exception as e:
        logger.debug("get_current_fix error: %s", e)
        return None
