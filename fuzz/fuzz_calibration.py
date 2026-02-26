#!/usr/bin/env python3
"""
LibFuzzer harness for calibration JSON (Calibration.from_dict).

Feed raw bytes as JSON. Fuzzer exercises from_dict and _to_triple with arbitrary JSON.
Run: python fuzz/fuzz_calibration.py fuzz/corpus/calibration/ [options]
"""

import json
import sys

try:
    import atheris
except ImportError:
    print("Install atheris: pip install atheris")
    sys.exit(1)

with atheris.instrument_imports():
    from navit_daemon.calibration import Calibration


def test_one_input(data: bytes) -> None:
    """Single fuzz iteration: parse JSON and build Calibration."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return
    cal = Calibration.from_dict(obj)
    cal.apply_gyro((0.0, 0.0, 0.0))
    cal.apply_accel((0.0, 0.0, 9.81))
    cal.apply_magnetometer((0.0, 0.0, 0.0))
    cal.to_dict()


def main() -> None:
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
