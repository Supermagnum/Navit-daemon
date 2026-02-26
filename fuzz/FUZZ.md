# Fuzzing (libFuzzer via Atheris)

See [FUZZ_REPORT.md](FUZZ_REPORT.md) for a summary of fuzz runs, coverage plateaus, crashes found and fixed, and recommendations.

This project uses [Atheris](https://github.com/google/atheris) for coverage-guided fuzzing with a libFuzzer-style interface. Atheris instruments Python code and feeds mutated inputs to harnesses to find crashes and assertion failures.

## Install

Install the package with fuzz dependencies:

```bash
pip install -e ".[fuzz]"
# Or with dev deps as well:
pip install -e ".[dev,fuzz]"
```

Atheris ships with a built-in libFuzzer in its [prebuilt wheels](https://pypi.org/project/atheris/); `pip install atheris` is enough for coverage-guided fuzzing of Python code. A custom Python or Clang build is only needed if you fuzz native C/C++ extensions with sanitizers (see [Atheris installation](https://github.com/google/atheris#installation)).

## Harnesses

| Harness | Target | Corpus |
|---------|--------|--------|
| `fuzz_remote_parse.py` | Remote protocol JSON parsing (`RemoteSource._parse_line`) | `corpus/remote_parse/` |
| `fuzz_calibration.py` | Calibration JSON (`Calibration.from_dict`) | `corpus/calibration/` |
| `fuzz_calibration_api.py` | Calibration API requests (`_handle_request`) | `corpus/calibration_api/` |
| `fuzz_nmea.py` | NMEA sentence building (build_gga, build_rmc) | `corpus/nmea/` |

## Run

From the project root:

```bash
# Remote protocol parser (UTF-8 JSON lines)
python fuzz/fuzz_remote_parse.py fuzz/corpus/remote_parse/ -max_total_time=60

# Calibration JSON
python fuzz/fuzz_calibration.py fuzz/corpus/calibration/ -max_total_time=60

# Calibration API requests
python fuzz/fuzz_calibration_api.py fuzz/corpus/calibration_api/ -max_total_time=60

# NMEA builder (JSON with lat, lon, alt, time_iso, etc.)
python fuzz/fuzz_nmea.py fuzz/corpus/nmea/ -max_total_time=60
```

Useful options:

- `-max_total_time=N`  Run for N seconds.
- `-max_len=N`         Cap input size (default often 4096).
- `-timeout=N`         Per-input timeout in seconds (default 1200).
- `-print_final_stats=1` Print coverage stats at exit.

Crashes are written to the current directory or to `-artifact_prefix=./` (e.g. `./crash-...`). Reproduce a crash:

```bash
python fuzz/fuzz_remote_parse.py ./crash-...
```

## Corpora

Seed corpora are in `fuzz/corpus/<harness>/`. Each file is one fuzz input (e.g. one JSON line for remote/NMEA, one JSON object for calibration/API). Add valid and edge-case inputs to improve coverage. Do not commit large generated corpora under `fuzz/corpus_artifacts/` or under `fuzz/crashes/`, `fuzz/timeouts/`, `fuzz/leaks/` (they are gitignored).

## Long runs (nohup, 3 hours)

From the project root with a venv activated:

```bash
mkdir -p fuzz/logs
MAX=10800   # 3 hours in seconds

nohup bash -c "source .venv/bin/activate && timeout $MAX python fuzz/fuzz_remote_parse.py fuzz/corpus/remote_parse/ -max_total_time=$MAX -print_final_stats=1" > fuzz/logs/remote_parse.log 2>&1 &
nohup bash -c "source .venv/bin/activate && timeout $MAX python fuzz/fuzz_calibration.py fuzz/corpus/calibration/ -max_total_time=$MAX -print_final_stats=1" > fuzz/logs/calibration.log 2>&1 &
nohup bash -c "source .venv/bin/activate && timeout $MAX python fuzz/fuzz_calibration_api.py fuzz/corpus/calibration_api/ -max_total_time=$MAX -print_final_stats=1" > fuzz/logs/calibration_api.log 2>&1 &
nohup bash -c "source .venv/bin/activate && timeout $MAX python fuzz/fuzz_nmea.py fuzz/corpus/nmea/ -max_total_time=$MAX -print_final_stats=1" > fuzz/logs/nmea.log 2>&1 &
```

Check with `ps aux | grep fuzz`. Tail logs: `tail -f fuzz/logs/remote_parse.log`. Crashes (if any) go to the current directory or `-artifact_prefix=./` (e.g. `./crash-*`).

## Why remote_parse plateaus early (cov 47)

The remote_parse fuzzer often reaches **cov 47** and then stops finding new edges. Reasons:

1. **Small target**  
   `_parse_line` is a single function with a few branches: `isinstance(data, dict)`, presence of `accel`/`gyro`, type and length checks for lists, optional `magnetometer`, optional `lat`/`lon`, and `float()` conversions. There are no loops or variable-depth logic, so the number of reachable edges is limited.

2. **Seed corpus already saturates**  
   The initial seeds (IMU-only, IMU+mag, GPS-only, combined, minimal GPS, numeric strings) already trigger the main paths. LibFuzzer merges in new inputs only when they increase coverage; after a few runs the corpus (often 10–50 files) already covers all branches in the parser, so mutations rarely find new edges.

3. **Heavy instrumentation**  
   Atheris instruments all imported code (e.g. `json`, `navit_daemon.sources.base`, `gps_reader`). The 47 edges are for the whole process; the parser itself is only a subset. So "47" is not a low percentage of the parser—it can be full coverage of the parser plus a fixed amount of JSON and helpers.

4. **Early returns**  
   Many mutated inputs are invalid JSON, non-dict, or missing keys, so execution hits `json.loads` and the first checks then returns. Those paths are found quickly; the only additional edges are the success paths (valid IMU and/or GPS), which the seeds already exercise.

**Conclusion:** Plateau at 47 is expected for this small, linear parser. It does not indicate a broken fuzzer or missing corpus. To confirm, run the unit tests for the remote parser; they already cover the same branches. For more growth you would need a larger or more branching target (e.g. a parser with more message types or deeper validation).

## CI

To run a short fuzz run in CI (e.g. 30–60 seconds per harness), run the harness with the corpus directory. For long runs, use `-max_total_time=N`; the prebuilt Atheris wheels provide full coverage-guided fuzzing.
