"""
Build NMEA 0183 sentences (GGA, RMC) for Navit/gpsd.
"""

from typing import Optional

from navit_daemon.gps_reader import GpsFix


def _nmea_checksum(s: str) -> str:
    """Compute NMEA checksum (xor of bytes between $ and *)."""
    c = 0
    for ch in s:
        c ^= ord(ch)
    return f"{c:02X}"


def _lat_nmea(lat: float) -> str:
    """Format latitude as NMEA (DDDMM.MMMM,N/S)."""
    abs_lat = abs(lat)
    deg = int(abs_lat)
    minutes = (abs_lat - deg) * 60.0
    hem = "N" if lat >= 0 else "S"
    return f"{deg:02d}{minutes:07.4f},{hem}"


def _lon_nmea(lon: float) -> str:
    """Format longitude as NMEA (DDDMM.MMMM,E/W)."""
    abs_lon = abs(lon)
    deg = int(abs_lon)
    minutes = (abs_lon - deg) * 60.0
    hem = "E" if lon >= 0 else "W"
    return f"{deg:03d}{minutes:07.4f},{hem}"


def _time_iso_to_nmea(iso_str: Optional[str]) -> str:
    """Convert ISO8601 time to NMEA time (HHMMSS.ss)."""
    if not iso_str or "T" not in iso_str:
        return "000000.00"
    try:
        part = iso_str.split("T")[1].replace("Z", "").replace("-", "")
        if "." in part:
            t = part.split(".")[0]
        else:
            t = part[:8] if len(part) >= 8 else part
        t = t.replace(":", "")
        if len(t) >= 6:
            return t[:6] + ".00"
        return "000000.00"
    except Exception:
        return "000000.00"


def build_gga(
    lat: float,
    lon: float,
    alt_m: float,
    fix_quality: int = 1,
    num_sats: int = 0,
    hdop: float = 1.0,
    time_iso: Optional[str] = None,
) -> str:
    """
    Build NMEA GGA sentence (position, altitude, time).

    time_iso: optional ISO8601 timestamp for fix time.
    """
    time_nmea = _time_iso_to_nmea(time_iso)
    s = (
        f"GPGGA,{time_nmea},"
        f"{_lat_nmea(lat)},{_lon_nmea(lon)},"
        f"{fix_quality:1d},{num_sats:02d},{hdop:.1f},"
        f"{alt_m:.1f},M,0.0,M,,"
    )
    return f"${s}*{_nmea_checksum(s)}\r\n"


def build_rmc(
    lat: float,
    lon: float,
    speed_knots: float,
    track_deg: float,
    time_iso: Optional[str] = None,
    date_iso: Optional[str] = None,
    valid: bool = True,
) -> str:
    """
    Build NMEA RMC sentence (position, speed, track, date/time).

    track_deg: true heading in degrees 0-360.
    """
    time_nmea = _time_iso_to_nmea(time_iso)
    if date_iso and "T" in date_iso:
        d = date_iso.split("T")[0].replace("-", "")
        if len(d) == 8:
            date_nmea = d[6:8] + d[4:6] + d[0:4]
        else:
            date_nmea = "010100"
    else:
        date_nmea = "010100"
    status = "A" if valid else "V"
    track_str = f"{track_deg:.1f}" if 0 <= track_deg < 360 else "0.0"
    s = (
        f"GPRMC,{time_nmea},{status},"
        f"{_lat_nmea(lat)},{_lon_nmea(lon)},"
        f"{speed_knots:.1f},{track_str},{date_nmea},,,"
    )
    return f"${s}*{_nmea_checksum(s)}\r\n"


def fix_to_nmea(
    fix: Optional[GpsFix],
    heading_deg: float,
    time_iso: Optional[str] = None,
) -> tuple:
    """
    Build GGA and RMC from GpsFix and AHRS heading.

    If fix is None or invalid, returns (None, None).
    heading_deg: from fusion (yaw) or GPS track, 0-360.
    """
    if fix is None or not fix.valid:
        return (None, None)
    t_iso = time_iso if time_iso is not None else getattr(fix, "time_iso", None)
    lat, lon, alt = fix.lat, fix.lon, fix.alt
    speed_knots = fix.speed_ms * 1.943844  # m/s to knots
    track = heading_deg
    if fix.speed_ms > 0.5:
        track = fix.track
    gga = build_gga(lat, lon, alt, fix_quality=fix.mode, time_iso=t_iso)
    rmc = build_rmc(
        lat,
        lon,
        speed_knots,
        track,
        time_iso=t_iso,
        date_iso=t_iso,
        valid=True,
    )
    return (gga, rmc)
