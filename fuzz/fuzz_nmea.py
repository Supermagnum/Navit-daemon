#!/usr/bin/env python3
"""
LibFuzzer harness for NMEA building (build_gga, build_rmc, _time_iso_to_nmea).

Feed raw bytes as JSON: {"lat":float,"lon":float,"alt":float,"time_iso":str,...}
Fuzzer exercises NMEA formatting with arbitrary numeric and string inputs.
Run: python fuzz/fuzz_nmea.py fuzz/corpus/nmea/ [options]
"""

import json
import sys

try:
    import atheris
except ImportError:
    print("Install atheris: pip install atheris")
    sys.exit(1)

with atheris.instrument_imports():
    from navit_daemon.nmea import build_gga, build_rmc


def test_one_input(data: bytes) -> None:
    """Single fuzz iteration: parse JSON and build NMEA sentences."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return
    if not isinstance(obj, dict):
        return
    try:
        lat = float(obj.get("lat", 0))
        lon = float(obj.get("lon", 0))
        alt = float(obj.get("alt", 0))
    except (TypeError, ValueError, OverflowError):
        return
    time_iso = obj.get("time_iso")
    if time_iso is not None and not isinstance(time_iso, str):
        time_iso = None
    date_iso = obj.get("date_iso")
    if date_iso is not None and not isinstance(date_iso, str):
        date_iso = None
    try:
        speed = float(obj.get("speed", 0)) if isinstance(obj.get("speed"), (int, float)) else 0.0
        track = float(obj.get("track", 0)) if isinstance(obj.get("track"), (int, float)) else 0.0
    except (TypeError, ValueError, OverflowError):
        speed, track = 0.0, 0.0
    try:
        fix_quality = int(obj.get("fix_quality", 1)) if isinstance(obj.get("fix_quality"), (int, float)) else 1
        num_sats = int(obj.get("num_sats", 0)) if isinstance(obj.get("num_sats"), (int, float)) else 0
        hdop = float(obj.get("hdop", 1.0)) if isinstance(obj.get("hdop"), (int, float)) else 1.0
    except (TypeError, ValueError, OverflowError):
        fix_quality, num_sats, hdop = 1, 0, 1.0
    valid = bool(obj.get("valid", True))
    try:
        build_gga(lat, lon, alt, fix_quality=fix_quality, num_sats=num_sats, hdop=hdop, time_iso=time_iso)
        build_rmc(lat, lon, speed, track, time_iso=time_iso, date_iso=date_iso, valid=valid)
    except (OverflowError, ValueError):
        return


def main() -> None:
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
