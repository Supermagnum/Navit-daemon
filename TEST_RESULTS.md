# Test Results

This document records the outcome of running the Navit-daemon test suite.

## Run Summary

- **Date:** 2025-02-12 (generated from test run)
- **Platform:** Linux, Python 3.12.3
- **Test framework:** pytest 9.0.2
- **Result:** 93 passed, 9 skipped
- **Duration:** ~0.07s

## Summary by Module

| Module | Passed | Skipped | Total |
|--------|--------|---------|-------|
| test_calibration.py | 15 | 0 | 15 |
| test_calibration_api.py | 15 | 0 | 15 |
| test_config.py | 18 | 0 | 18 |
| test_fusion_ahrs.py | 1 | 9 | 10 |
| test_nmea.py | 28 | 0 | 28 |
| test_sources_calibrated.py | 3 | 0 | 3 |
| test_sources_remote.py | 15 | 0 | 15 |
| **Total** | **93** | **9** | **102** |

## Why some tests are skipped

The 9 skipped tests are all in `test_fusion_ahrs.py`. They are skipped when the **imufusion** Python package is not installed.

- **Reason:** The daemon uses the `imufusion` library for AHRS (attitude/heading) fusion. The test file checks at import time whether `imufusion` is available. If not, the classes `TestFusionAhrsValid` and `TestFusionAhrsEdgeCases` are marked with `@pytest.mark.skipif(not IMUFUSION_AVAILABLE, reason="imufusion not installed")`, so their tests are skipped.
- **When they run:** If you install the project with its full dependencies (`pip install .` or `imufusion` listed in requirements), imufusion is present and those 9 tests run. In minimal or CI environments where imufusion is not installed, they are skipped.
- **What still runs:** One test in `test_fusion_ahrs.py` runs only when imufusion is *not* installed: `TestFusionAhrsWithoutImufusion::test_init_raises_when_imufusion_missing`, which checks that the daemon raises a clear error instead of failing later. So you always get either the full fusion tests or the "missing library" test.

## Skipped Tests (summary)

The 9 skipped tests are in `test_fusion_ahrs.py`. When `imufusion` is installed, they run and exercise AHRS initialization, updates, yaw range, and edge cases (zero gyro/accel, sample period, gain 0/1).

## Results by Test File

### tests/test_calibration.py (15 passed)

- **TestCalibrationApply:** apply_gyro/apply_accel/apply_magnetometer with default and explicit bias/offset.
- **TestCalibrationFromDict:** from_dict valid (includes magnetometer_bias), partial, invalid; to_dict roundtrip.
- **TestLoadSaveCalibration:** load missing/None returns default; save and load roundtrip (includes magnetometer_bias); invalid JSON returns default.

### tests/test_calibration_api.py (15 passed)

- **TestHandleRequestGetCalibration:** get_calibration returns current (includes magnetometer_bias); status when collecting.
- **TestHandleRequestSetCalibration:** set gyro/accel/magnetometer; invalid input returns error.
- **TestHandleRequestCalibrateGyro:** calibrate_gyro returns collecting and samples_needed; default and clamped seconds.
- **TestHandleRequestInvalid:** not dict and unknown request return error.
- **TestCalibrationManagerGyroCollection:** add_gyro_sample until done sets bias; saves to file when save_path set.

### tests/test_config.py (18 passed)

- **TestParseArgsDefaults:** empty args use defaults (including calibration_file None, calibration_port 0, magnetometer_path None); --help exits.
- **TestParseArgsValid:** source (remote, auto), gpsd host/port, remote port, NMEA bind, IMU/output rate, fusion gain, accel/gyro/magnetometer paths, calibration-file and calibration-port, debug flag.
- **TestParseArgsInvalidAndEdge:** invalid source rejected; invalid port type; negative port; fusion gain 0 and 1 accepted.

### tests/test_fusion_ahrs.py (1 passed, 9 skipped)

- **TestFusionAhrsValid (skipped without imufusion):** initialized false before update; one update sets initialized; yaw_deg in [0, 360); multiple updates.
- **TestFusionAhrsEdgeCases (skipped without imufusion):** zero gyro/accel; very small/larger sample period; gain 0 and gain 1.
- **TestFusionAhrsWithoutImufusion:** init raises RuntimeError when imufusion is missing (passed).

### tests/test_nmea.py (28 passed)

- **TestNmeaChecksum:** GGA/RMC start with $ and end with CRLF.
- **TestBuildGgaValid:** equator/prime meridian; positive/negative lat/lon; time_iso used, malformed, or None.
- **TestBuildGgaEdgeCases:** lat +/-90, lon +/-180; negative altitude; fix quality 0.
- **TestBuildRmcValid:** basic RMC; valid false status V; date from ISO; track outside 0--360 clamped.
- **TestBuildRmcEdgeCases:** track negative, 360, speed zero.
- **TestFixToNmeaValid:** valid fix returns GGA and RMC; uses fix time_iso; speed above threshold uses fix track.
- **TestFixToNmeaInvalidAndEdge:** None fix returns None; invalid fix returns None; speed below threshold uses heading not fix track.

### tests/test_sources_calibrated.py (3 passed)

- **test_calibrated_applies_bias_and_offset:** wrapper applies calibration to sample (including magnetometer bias).
- **test_calibrated_returns_none_when_inner_returns_none:** pass-through None.
- **test_calibrated_with_manager_feeds_gyro_on_read:** when manager set, raw gyro fed to manager; after enough samples bias updated.

### tests/test_sources_remote.py (15 passed)

- **TestRemoteSourceParseLineValid:** IMU with magnetometer; IMU-only updates read(); GPS-only updates get_fix(); combined IMU+GPS; minimal GPS keys.
- **TestRemoteSourceParseLineInvalid:** empty line ignored; invalid/non-JSON ignored; IMU missing gyro or short list not stored; GPS missing lon ignored.
- **TestRemoteSourceParseLineEdgeCases:** numeric strings converted; time_iso non-string set to None; read before parse returns None; latest GPS/IMU overwrites previous.

## How to Reproduce

From the project root with the virtualenv activated:

```bash
.venv/bin/pytest tests -v --tb=short
```

To run including tests that require `imufusion`:

```bash
pip install imufusion
.venv/bin/pytest tests -v --tb=short
```
