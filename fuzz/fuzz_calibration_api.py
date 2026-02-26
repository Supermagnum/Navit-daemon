#!/usr/bin/env python3
"""
LibFuzzer harness for calibration API request handling (_handle_request).

Feed raw bytes as JSON. Fuzzer exercises API request parsing and validation.
Run: python fuzz/fuzz_calibration_api.py fuzz/corpus/calibration_api/ [options]
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
    from navit_daemon.calibration_api import CalibrationManager, _handle_request


def test_one_input(data: bytes) -> None:
    """Single fuzz iteration: parse JSON and handle as calibration API request."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return
    try:
        request = json.loads(text)
    except json.JSONDecodeError:
        return
    cal = Calibration()
    manager = CalibrationManager(cal)
    _handle_request(manager, None, request, 100.0)


def main() -> None:
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
