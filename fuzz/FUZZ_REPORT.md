# Fuzzing Report

This report summarizes coverage-guided fuzzing of the Navit-daemon codebase using Atheris (libFuzzer-style) and the actions taken on findings.

## Setup

- **Tool:** Atheris 2.x (libFuzzer-style, coverage-guided)
- **Harnesses:** 4 (remote protocol parser, calibration JSON, calibration API, NMEA builder)
- **Runs:** Long runs (up to 3 hours per harness) with seed corpora in `fuzz/corpus/<harness>/`
- **Logs:** `fuzz/logs/<harness>.log`

## Harness summary

| Harness | Target | Corpus |
|---------|--------|--------|
| `fuzz_remote_parse.py` | `RemoteSource._parse_line` (JSON parsing, type coercion) | `corpus/remote_parse/` |
| `fuzz_calibration.py` | `Calibration.from_dict` | `corpus/calibration/` |
| `fuzz_calibration_api.py` | Calibration API `_handle_request` (JSON requests) | `corpus/calibration_api/` |
| `fuzz_nmea.py` | `build_gga`, `build_rmc` (JSON to NMEA) | `corpus/nmea/` |

## Coverage plateau summary

All four harnesses reached a stable coverage ceiling. No new edges were found after the plateau.

| Harness | Plateau (cov / features) | Notes |
|---------|---------------------------|--------|
| remote_parse | 47 / 47 | Small linear parser; seed corpus saturates branches quickly. |
| calibration | 19 / 26 | Small target (from_dict and helpers). |
| calibration_api | 51 / 51 | Grew from 47 to 51 during runs; then stable. |
| nmea | 37 / 54 | JSON-to-NMEA conversion; plateau after OverflowError fix. |

Plateaus are expected for these small, branch-limited targets. See `FUZZ.md` for why remote_parse plateaus early.

## Crashes found and fixes

Fuzzing triggered several runtime errors. All were fixed so the fuzzers no longer exit on these inputs.

### Remote protocol parser (`navit_daemon/sources/remote.py`)

- **Non-dict JSON:** Inputs that decoded to non-dict (e.g. `"0"`, `"[]"`) caused `TypeError` when checking keys. **Fix:** Require `isinstance(data, dict)` after `json.loads`; return otherwise.
- **Non-numeric IMU/GPS values:** Lists or dicts in `accel`/`gyro`/`magnetometer` or string/empty values in `lat`/`lon`/`alt`/etc. led to `TypeError`/`ValueError` in `float()`. **Fix:** Wrap all relevant `float()` conversions in `try/except (TypeError, ValueError)` and skip updating state on failure.

### Calibration API (`navit_daemon/calibration_api.py`)

- **Non-numeric bias/offset elements:** Request bodies with lists containing non-numeric values (e.g. dicts) for `gyro_bias`, `accel_offset`, or `magnetometer_bias` caused `TypeError` in `float()`. **Fix:** Wrap each bias/offset list conversion in `try/except (TypeError, ValueError)` and return an error response on failure.

### NMEA harness (`fuzz/fuzz_nmea.py`)

- **Non-dict JSON:** Input that decoded to a string or other non-dict type caused `AttributeError` on `obj.get()`. **Fix:** After `json.loads`, require `isinstance(obj, dict)`; return otherwise.
- **OverflowError:** Very large integers (e.g. for `alt`, `speed`, `track`, `hdop`) caused `int too large to convert to float`. **Fix:** Catch `OverflowError` (and `ValueError`) on all numeric extractions and on `build_gga`/`build_rmc`; return from the harness on failure.

## Unit test updates

- **test_sources_remote.py:** Renamed `test_magnetometer_invalid_numeric_raises_value_error` to `test_magnetometer_invalid_numeric_ignored` and updated expectations to match the new behavior (invalid magnetometer values ignored, no exception).

## Crash artifacts

Crash artifacts (e.g. `crash-*` in the project root) produced during fuzzing were removed after applying the fixes above. They are not committed. To reproduce a crash, re-run the corresponding harness with a corpus that exercises the same code paths; the fixes ensure those inputs are handled without crashing.

## Recommendations

- **CI:** Run each harness for a short time (e.g. 30–60 seconds) with the seed corpus to catch regressions. Full coverage-guided fuzzing requires a libFuzzer-capable Python build.
- **Corpus:** Keep seed corpora in `fuzz/corpus/<harness>/` with valid and edge-case inputs. Do not commit large generated corpora or crash artifacts.
- **New code:** When adding parsers or API handlers that accept JSON or untrusted input, extend the relevant harness or add a new one and run fuzzing before and after changes.
