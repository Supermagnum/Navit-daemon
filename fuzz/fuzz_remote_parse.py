#!/usr/bin/env python3
"""
LibFuzzer harness for remote protocol JSON parsing (RemoteSource._parse_line).

Feed raw bytes (UTF-8). Fuzzer exercises JSON parsing and type coercion.
Run: python fuzz/fuzz_remote_parse.py fuzz/corpus/remote_parse/ [options]
"""

import sys

try:
    import atheris
except ImportError:
    print("Install atheris: pip install atheris")
    sys.exit(1)

with atheris.instrument_imports():
    from navit_daemon.sources.remote import RemoteSource


def test_one_input(data: bytes) -> None:
    """Single fuzz iteration: decode data as UTF-8 and parse as remote protocol line."""
    try:
        line = data.decode("utf-8").strip()
    except UnicodeDecodeError:
        return
    source = RemoteSource(host="127.0.0.1", port=0)
    source._parse_line(line)
    source.read()
    source.get_fix()


def main() -> None:
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
