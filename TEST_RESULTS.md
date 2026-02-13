# Test Results

This document records the outcome of running the Navit-daemon test suite.

## Run Summary

- **Date:** 2025-02-12 (generated from test run)
- **Platform:** Linux, Python 3.12.3
- **Test framework:** pytest 9.0.2
- **Result:** 172 passed, 17 skipped
- **Duration:** ~0.14s

## Summary by Module

| Module | Passed | Skipped | Total |
|--------|--------|---------|-------|
| test_calibration.py | 15 | 0 | 15 |
| test_calibration_api.py | 22 | 0 | 22 |
| test_config.py | 28 | 0 | 28 |
| test_fusion_ahrs.py | 1 | 17 | 18 |
| test_iio_reader.py | 21 | 0 | 21 |
| test_nmea.py | 55 | 0 | 55 |
| test_sources_calibrated.py | 7 | 0 | 7 |
| test_sources_remote.py | 23 | 0 | 23 |
| **Total** | **172** | **17** | **189** |

## Why some tests are skipped

The 17 skipped tests are all in `test_fusion_ahrs.py`. They are skipped when the **imufusion** Python package is not installed.

- **Reason:** The daemon uses the `imufusion` library for AHRS (attitude/heading) fusion. The test file checks at import time whether `imufusion` is available. If not, the classes `TestFusionAhrsValid`, `TestFusionAhrsEdgeCases`, and `TestFusionAhrsInvalidAndMalformed` are marked with `@pytest.mark.skipif(not IMUFUSION_AVAILABLE, reason="imufusion not installed")`, so their tests are skipped.
- **When they run:** If you install the project with its full dependencies (`pip install .` or `imufusion` listed in requirements), imufusion is present and those 17 tests run. In minimal or CI environments where imufusion is not installed, they are skipped.
- **What still runs:** One test in `test_fusion_ahrs.py` runs only when imufusion is *not* installed: `TestFusionAhrsWithoutImufusion::test_init_raises_when_imufusion_missing`, which checks that the daemon raises a clear error instead of failing later. So you always get either the full fusion tests or the "missing library" test.

## Skipped Tests (summary)

The 17 skipped tests are in `test_fusion_ahrs.py`. When `imufusion` is installed, they run and exercise AHRS initialization, updates, yaw range, edge cases (zero gyro/accel, sample period, gain 0/1), and invalid/malformed data handling (negative/zero/large sample periods, extreme values, negative/large gain).

## Results by Test File

### tests/test_calibration.py (15 passed)

Tests the Calibration class that applies software-based bias/offset correction to IMU sensor readings.

- **TestCalibrationApply:** Verifies that `apply_gyro()`, `apply_accel()`, and `apply_magnetometer()` correctly subtract bias/offset values from sensor readings. Tests default (zero) calibration and explicit calibration values. Ensures calibration is applied element-wise to (x, y, z) tuples.
- **TestCalibrationFromDict:** Tests serialization/deserialization of calibration data. Verifies `from_dict()` handles valid dictionaries (including magnetometer_bias), partial dictionaries (only some fields), invalid input (non-dict returns default), and short lists (returns default). Tests `to_dict()` roundtrip preserves all calibration values.
- **TestLoadSaveCalibration:** Tests file I/O for calibration persistence. Verifies `load_calibration()` returns default calibration when file is missing or path is None. Tests `save_calibration()` and `load_calibration()` roundtrip preserves all values including magnetometer_bias. Verifies invalid JSON in file returns default calibration instead of crashing.

### tests/test_calibration_api.py (22 passed)

Tests the TCP calibration API that allows runtime calibration updates and automatic gyro bias collection.

- **TestHandleRequestGetCalibration:** Tests `get_calibration` request returns current calibration state including gyro_bias, accel_offset, magnetometer_bias, and calibration_status. Verifies status shows "collecting" when gyro calibration is in progress, with samples_collected and samples_needed counts.
- **TestHandleRequestSetCalibration:** Tests `set_calibration` request updates calibration values. Verifies setting gyro_bias, accel_offset, or magnetometer_bias individually or together. Tests invalid input (short lists, non-dict) returns error response. Tests extreme values are accepted. Tests empty dict is accepted (no-op update).
- **TestHandleRequestCalibrateGyro:** Tests `calibrate_gyro` request starts automatic gyro bias collection. Verifies response includes "collecting" status and correct samples_needed count based on seconds and sample_rate_hz. Tests default seconds (5s) and clamped values (minimum enforced). Tests negative seconds are clamped. Tests zero sample rate is handled. Tests very large seconds values.
- **TestHandleRequestInvalid:** Tests error handling for malformed requests. Verifies non-dict input returns error. Verifies unknown request keys return error. Verifies empty request dict returns error.
- **TestCalibrationManagerGyroCollection:** Tests automatic gyro bias calculation. Verifies `add_gyro_sample()` accumulates samples and calculates mean bias when collection completes. Verifies calibration file is automatically saved when save_path is set and collection finishes.

### tests/test_config.py (28 passed)

Tests command-line argument parsing and configuration object creation.

- **TestParseArgsDefaults:** Tests that when no arguments are provided, all configuration values use sensible defaults. Verifies source defaults to "linux", gpsd defaults to 127.0.0.1:2947, remote defaults to 0.0.0.0:2949, NMEA defaults to 127.0.0.1:2948, IMU rate defaults to 100 Hz, output rate defaults to 5 Hz, fusion gain defaults to 0.5, and optional paths default to None. Tests that --help flag causes SystemExit.
- **TestParseArgsValid:** Tests that all valid command-line arguments are correctly parsed. Verifies source can be "remote" or "auto", gpsd host/port can be customized, remote port can be set, NMEA bind address/port can be configured, IMU and output rates accept float values, fusion gain accepts float, accel/gyro/magnetometer paths accept string paths, calibration-file and calibration-port can be set, and debug flag enables debug mode.
- **TestParseArgsInvalidAndEdge:** Tests error handling and edge cases. Verifies invalid source value raises SystemExit. Verifies invalid port type (non-numeric) raises SystemExit. Tests that negative ports are accepted (may be used for special cases). Tests fusion gain 0 and 1 are valid. Tests very large ports (including beyond 65535) are accepted. Tests zero port is valid. Tests negative, zero, and very large IMU/output rates are accepted. Tests negative and very large fusion gain values are accepted. Tests empty path strings are accepted.

### tests/test_fusion_ahrs.py (1 passed, 17 skipped)

Tests the AHRS (Attitude and Heading Reference System) fusion wrapper that computes orientation from IMU sensor data.

- **TestFusionAhrsValid (skipped without imufusion):** Tests normal operation of AHRS fusion. Verifies `initialized` property is False before any updates. Verifies one `update()` call with accel and gyro data sets `initialized` to True. Verifies `yaw_deg` property returns values in [0, 360) range. Tests multiple sequential updates produce consistent orientation values.
- **TestFusionAhrsEdgeCases (skipped without imufusion):** Tests edge cases and boundary conditions. Verifies fusion handles zero gyro and zero accel inputs without crashing. Tests very small sample period (0.001s) and larger sample period (0.1s). Tests gain values of 0 and 1 (boundary values).
- **TestFusionAhrsInvalidAndMalformed (skipped without imufusion):** Tests error handling and invalid input. Verifies negative sample period handling (may raise error or be clamped). Tests zero sample period is accepted. Tests very large sample period (1000s) is handled. Tests extreme accel/gyro/magnetometer values (1000 m/s², 1000 deg/s, 1000 uT). Tests negative gain and very large gain (100.0) values.
- **TestFusionAhrsWithoutImufusion:** Tests that when imufusion library is not installed, FusionAhrs constructor raises RuntimeError with clear error message instead of failing silently later.

### tests/test_nmea.py (55 passed)

Tests NMEA 0183 sentence generation (GGA and RMC formats) used for GPS navigation output.

- **TestNmeaChecksum:** Tests that generated NMEA sentences follow the standard format. Verifies sentences start with "$" character, contain "*" checksum separator, and end with "\r\n" (CRLF). Verifies checksum is correctly calculated.
- **TestBuildGgaValid:** Tests GGA sentence building with valid GPS data. Verifies equator/prime meridian (0,0) produces correct NMEA format. Tests positive and negative latitude/longitude values. Tests time_iso parameter is correctly parsed and formatted. Tests malformed time_iso falls back to default. Tests None time_iso uses default. Tests empty string time_iso uses default. Tests incomplete time_iso formats are handled gracefully.
- **TestBuildGgaEdgeCases:** Tests boundary conditions for GGA sentences. Verifies latitude ±90 degrees (poles) are handled. Verifies longitude ±180 degrees (date line) are handled. Tests negative altitude (below sea level) is correctly formatted. Tests fix quality 0 (no fix) is included in output.
- **TestBuildGgaInvalidAndMalformed:** Tests error handling for invalid GGA inputs. Verifies latitude/longitude beyond ±90/±180 are handled (may be clamped or formatted anyway). Tests negative fix_quality is accepted. Tests large fix_quality (>9) is accepted. Tests negative num_sats is accepted. Tests large num_sats (>99) is accepted. Tests negative and zero HDOP (horizontal dilution of precision) are handled. Tests very large altitude values are formatted.
- **TestBuildRmcValid:** Tests RMC sentence building with valid data. Verifies basic RMC sentence format. Tests valid=False produces status "V" (invalid). Tests valid=True produces status "A" (active). Tests date_iso parameter is parsed and formatted as DDMMYYYY. Tests track (heading) values outside 0-360 range are clamped to valid range.
- **TestBuildRmcEdgeCases:** Tests boundary conditions for RMC sentences. Verifies negative track values are handled. Tests track value of 360 degrees is handled. Tests zero speed is correctly formatted.
- **TestBuildRmcInvalidAndMalformed:** Tests error handling for invalid RMC inputs. Verifies malformed date_iso falls back to default date. Tests incomplete date_iso formats use default. Tests empty date_iso uses default. Tests negative speed is formatted. Tests very large speed values are formatted. Tests very large track values (>360) are clamped. Tests very negative track values are handled.
- **TestFixToNmeaValid:** Tests conversion of GpsFix object to NMEA sentences. Verifies valid fix produces both GGA and RMC sentences. Tests fix.time_iso is used when available. Tests speed above threshold (0.5 m/s) uses GPS track instead of AHRS heading.
- **TestFixToNmeaInvalidAndEdge:** Tests edge cases for fix conversion. Verifies None fix returns (None, None) tuple. Verifies invalid fix (valid=False) returns (None, None) tuple. Tests speed below threshold uses AHRS heading instead of GPS track.
- **TestFixToNmeaInvalidAndMalformed:** Tests error handling for extreme fix values. Verifies extreme latitude/longitude values (200, 300) are handled. Tests negative heading is clamped. Tests heading beyond 360 degrees is clamped. Tests very large altitude is formatted. Tests negative altitude is formatted. Tests very large speed is handled.

### tests/test_sources_calibrated.py (7 passed)

Tests the CalibratedIMUSource wrapper that applies software calibration to IMU sensor readings.

- **test_calibrated_applies_bias_and_offset:** Tests that the wrapper correctly applies calibration (subtracts bias/offset) to accelerometer, gyroscope, and magnetometer readings from the inner IMU source. Verifies calibration is applied element-wise to (x, y, z) tuples.
- **test_calibrated_returns_none_when_inner_returns_none:** Tests that when the inner IMU source returns None (no data available), the wrapper passes through None without applying calibration.
- **test_calibrated_with_manager_feeds_gyro_on_read:** Tests integration with CalibrationManager. Verifies that when a manager is set, raw (uncalibrated) gyroscope data is fed to the manager for automatic bias collection. Verifies that after enough samples are collected, the manager's bias is updated and calibration file is saved.
- **test_calibrated_none_magnetometer_returns_none:** Tests that when magnetometer is None (not available), it remains None even when calibration has magnetometer_bias set. Ensures calibration is only applied when magnetometer data exists.
- **test_calibrated_extreme_bias_values:** Tests that calibration works correctly with extreme bias/offset values (e.g., 1000 deg/s bias, 100 m/s² offset, 1000 uT magnetometer bias). Verifies large corrections are applied correctly.
- **test_calibrated_zero_values:** Tests calibration with zero input sensor values. Verifies that bias/offset are still correctly subtracted, producing negative calibrated values when bias is positive.
- **test_calibrated_dynamic_calibration_change:** Tests that calibration changes (e.g., from calibration API) are immediately reflected in subsequent reads. Verifies the wrapper calls get_calibration() on each read, allowing runtime calibration updates.

### tests/test_iio_reader.py (21 passed)

Tests Linux IIO (Industrial I/O) subsystem integration for reading IMU sensors from sysfs.

- **TestDeviceIdentification:** Tests device name and IMU type identification. Verifies device name is read from "name" file in sysfs. Verifies device name falls back to "model" file if "name" doesn't exist. Tests empty string returned when neither file exists. Tests identification of common IMU devices (MPU6050, MPU9250, LSM6DS3, BNO055) by name pattern matching. Tests unknown devices return None. Tests get_device_info() returns complete device information including name, model, IMU type, description, and path.
- **TestDeviceDiscovery:** Tests discovery of IIO devices in /sys/bus/iio/devices/. Verifies devices matching "iio:device*" pattern are discovered and sorted. Tests empty list returned when IIO base directory doesn't exist.
- **TestFindDevices:** Tests finding accelerometer, gyroscope, and magnetometer devices. Verifies find_accel_device() accepts explicit path and validates it has accel channels. Tests invalid path returns None. Verifies find_gyro_device() prefers same device as accelerometer if it has gyro channels. Verifies find_magnetometer_device() prefers same device as accelerometer if it has magnetometer channels.
- **TestIIOReader:** Tests reading sensor data from IIO sysfs. Verifies read_accel() reads raw values, applies scale and offset, returns m/s². Verifies read_gyro() converts rad/s to deg/s when scale indicates radians. Verifies read_magnetometer() reads raw values, applies scale and offset, returns microtesla. Tests all read methods return None when device path is not set. Tests all read methods handle missing sysfs files gracefully.

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
