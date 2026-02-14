# Navit-daemon

A daemon that integrates accelerometer, gyroscope, magnetometer (digital compass), and GPS data into a unified NMEA output with AHRS-derived heading. It fuses inertial measurement unit (IMU) sensors with GPS position to provide continuous heading information even when GPS course-over-ground is unavailable or inaccurate (e.g., when stationary, in tunnels, or in urban canyons).

**Sensors integrated:**
- **Accelerometer** (3-axis): Provides gravity and motion acceleration in m/s²
- **Gyroscope** (3-axis): Provides angular velocity in deg/s
- **Magnetometer** (3-axis, digital compass): Provides magnetic field strength in microtesla (uT); optional but recommended for accurate heading and drift prevention
- **GPS**: Provides position (lat/lon/alt), speed, and course-over-ground

The daemon uses AHRS (Attitude and Heading Reference System) fusion to compute orientation (roll, pitch, yaw) from accelerometer, gyroscope, and optionally magnetometer data. When magnetometer is available, it improves heading accuracy and prevents drift. The yaw angle is used as heading and combined with GPS position to output standard NMEA sentences (GGA, RMC) over TCP for navigation applications like Navit.

**Magnetometer support:** Magnetometer is optional but recommended. If unavailable, the daemon falls back to gyroscope + accelerometer fusion (which may drift over time). On Linux, use `--magnetometer-path` to specify the IIO device, or it will be auto-detected. Android/iOS clients send magnetometer data when available. Magnetometer calibration (bias) can be set via the calibration API.

**Test results:** See [TEST_RESULTS.md](TEST_RESULTS.md) for comprehensive test coverage details (172 passed, 17 skipped).

## Install

### Requirements

- Python 3.8 or higher
- pip
- For Linux with local IMU: Linux kernel with IIO subsystem and (optionally) gpsd for GPS

### Install from source

```bash
# Clone the repository
git clone https://github.com/Supermagnum/Navit-daemon.git
cd Navit-daemon

# Create and activate a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# Install the package and its dependencies
pip install .

# Verify installation
navit-daemon --help
```

### Install in development mode (with dev tools)

```bash
pip install -e ".[dev]"
```

This installs the package in editable mode and adds dev dependencies (flake8, black, mypy, pytest). Run tests with:

```bash
pytest tests -v --tb=short
```

### Install from a built wheel

```bash
# Build wheel (from project root)
pip install build
python -m build

# Install the wheel
pip install dist/navit_daemon-*.whl
```

### Optional: system-wide install

```bash
sudo pip install .
# or
pip install --user .
```

The `navit-daemon` command will be available on your PATH.

**Build and packaging:** For full build instructions (Linux, Android client, iOS client), creating distribution packages, and systemd service setup, see [BUILD.md](BUILD.md).

## Sensor APIs by platform (compass, gyro, accelerometer)

How Android, iPhone, and the Toughpad FZ-G1 expose and use the digital compass (magnetometer), gyroscope, and accelerometer.

### Android

**Framework:** `android.hardware` (SensorManager, Sensor, SensorEvent, SensorEventListener).

| Sensor | Type constant | Data | Units |
|--------|----------------|------|--------|
| Accelerometer | `Sensor.TYPE_ACCELEROMETER` | `event.values[0..2]` = x, y, z | m/s2 (includes gravity) |
| Gyroscope | `Sensor.TYPE_GYROSCOPE` | `event.values[0..2]` = rate around x, y, z | rad/s |
| Magnetometer (compass) | `Sensor.TYPE_MAGNETIC_FIELD` | `event.values[0..2]` = field along x, y, z | microtesla (uT) |

Get `SensorManager` via `getSystemService(Context.SENSOR_SERVICE)`, then `getDefaultSensor(TYPE_...)` and `registerListener(listener, sensor, delay)`. Events arrive in `onSensorChanged(SensorEvent event)`.

For compass/orientation use accelerometer + magnetometer with `SensorManager.getRotationMatrix(rotationMatrix, null, accelerometerReading, magnetometerReading)` and `SensorManager.getOrientation(rotationMatrix, orientationAngles)` to get azimuth (compass), pitch, and roll. Alternatively use the fused `TYPE_ROTATION_VECTOR` (uses gyro + accel + magnetometer when available).

Accelerometer and gyroscope are always hardware-based; most devices have an accelerometer, many have a gyroscope. From API 31 these sensors can be rate-limited. Uncalibrated variants exist: `TYPE_ACCELEROMETER_UNCALIBRATED`, `TYPE_GYROSCOPE_UNCALIBRATED`, `TYPE_MAGNETIC_FIELD_UNCALIBRATED`.

### iPhone / iOS

**Framework:** Core Motion (`CMMotionManager`).

| Sensor | API | Data |
|--------|-----|------|
| Accelerometer | `startAccelerometerUpdates(to:withHandler:)` / `accelerometerData` | x, y, z acceleration (including gravity) |
| Gyroscope | `startGyroUpdates(to:withHandler:)` / `gyroData` | Rotation rate x, y, z |
| Magnetometer | `startMagnetometerUpdates(to:withHandler:)` / `magnetometerData` | `CMMagneticField` x, y, z |

Create one `CMMotionManager`; set e.g. `accelerometerUpdateInterval`, `gyroUpdateInterval`, `magnetometerUpdateInterval` (in seconds), then call the corresponding `start...Updates(to:withHandler:)`. The handler receives the latest sample (e.g. `CMMagnetometerData` with `magneticField.x/y/z`).

For fused orientation/compass use `startDeviceMotionUpdates(to:withHandler:)` which delivers `CMDeviceMotion`: attitude (roll, pitch, yaw), rotation rate, user acceleration (gravity removed), and optionally calibrated `magneticField`. That is the standard way to get compass-like orientation on iOS.

Check `isAccelerometerAvailable`, `isGyroAvailable`, `isMagnetometerAvailable` before starting updates.

### Toughpad FZ-G1 series (Linux)

Sensors are exposed via the Linux **Industrial I/O (IIO)** subsystem in sysfs, not a high-level API. There is no built-in "compass app" API; you read raw IIO channels under `/sys/bus/iio/devices/` (e.g. `in_accel_*`, `in_anglvel_*`, `in_magn_*`), apply scale factors to get physical units, and run your own fusion (e.g. Fusion AHRS in a Python daemon) to get orientation. See the section below for hardware details.

### Comparison

| Aspect | Android | iPhone / iOS | Toughpad FZ-G1 |
|--------|---------|--------------|----------------|
| Accelerometer | SensorManager, TYPE_ACCELEROMETER, m/s2 | CMMotionManager, accelerometerData / deviceMotion | IIO sysfs, raw then scale to m/s2 |
| Gyroscope | TYPE_GYROSCOPE, rad/s | gyroData / deviceMotion | IIO sysfs, raw then scale to deg/s or rad/s |
| Magnetometer | TYPE_MAGNETIC_FIELD, uT | magnetometerData / deviceMotion.magneticField | IIO sysfs, raw then scale |
| Fused orientation/compass | getRotationMatrix + getOrientation, or TYPE_ROTATION_VECTOR | CMDeviceMotion (attitude + magneticField) | User-space fusion (e.g. Fusion AHRS in Python daemon) |
| Integration | In-app only | In-app only | Daemon reads IIO + gpsd, outputs NMEA/gpsd for Navit |

### IMU calibration

The daemon applies a software calibration layer: **gyro bias** and **accel offset** are subtracted from each sample before AHRS fusion. You can load calibration from a file, set it at runtime via the calibration API, or run an automatic gyro bias collection (device held still).

**Options:**

- **`--calibration-file PATH`**  
  Load calibration from a JSON file at startup. If the calibration API is used to set values or to run gyro calibration, the file is updated when you call `set_calibration` or when gyro calibration finishes (so the daemon persists calibration).

- **`--calibration-port PORT`**  
  Enable the calibration TCP API on the given port (default: 0 = disabled). Bind address is 127.0.0.1. See "Calibration API" below.

**Linux (IIO):** The IIO reader still uses kernel sysfs scale/offset when present (`in_accel_scale`, `in_anglvel_scale`, etc.). The daemon’s calibration is applied on top of that (so you can correct residual bias in user space).

**Android / iPhone (remote):** The client sends scaled values; the daemon’s calibration (bias/offset) is applied to those before fusion.

### Calibration API

When `--calibration-port PORT` is set, the daemon listens on `127.0.0.1:PORT`. Protocol: **one JSON object per line**. Send one request line; read one response line.

**Get current calibration and status**

Request:
```json
{"get_calibration": true}
```
Response:
```json
{"gyro_bias": [0.0, 0.0, 0.0], "accel_offset": [0.0, 0.0, 0.0], "calibration_status": "idle", "samples_collected": 0, "samples_needed": 0}
```
When collecting gyro bias, `calibration_status` is `"collecting"` and `samples_collected` / `samples_needed` show progress.

**Set calibration**

Request:
```json
{"set_calibration": {"gyro_bias": [0.1, -0.05, 0.02], "accel_offset": [0.0, 0.0, 0.0]}}
```
Units: `gyro_bias` in deg/s, `accel_offset` in m/s^2. Omit keys to leave that part unchanged. If `--calibration-file` is set, the file is updated.
Response: `{"ok": true}` or `{"error": "..."}`.

**Run gyro bias calibration**

Place the device still (e.g. on a table), then send:

Request:
```json
{"calibrate_gyro": {"seconds": 5}}
```
`seconds` (0.5–60) is how long to collect; default 5. The daemon collects gyro samples at the configured IMU rate, then sets `gyro_bias` to the mean of those samples.

Response: `{"status": "collecting", "samples_needed": 500}`. Poll `get_calibration` until `calibration_status` is `"idle"`; then `gyro_bias` is updated. If `--calibration-file` is set, the file is written when collection finishes.

**Example (command line)**

```bash
# Start daemon with calibration file and API on port 2950
navit-daemon --calibration-file /var/lib/navit-daemon/cal.json --calibration-port 2950

# In another terminal: get current calibration
echo '{"get_calibration": true}' | nc -q 1 127.0.0.1 2950

# Set gyro bias manually (e.g. from external calibration)
echo '{"set_calibration": {"gyro_bias": [0.01, -0.02, 0.01]}}' | nc -q 1 127.0.0.1 2950

# Start 5-second gyro collection (hold device still)
echo '{"calibrate_gyro": {"seconds": 5}}' | nc -q 1 127.0.0.1 2950
```

### Platform compatibility of this daemon

**Linux: yes.** Use `--source=linux` (default). It uses the kernel IIO subsystem (`/sys/bus/iio/devices/`) for accelerometer and gyroscope, and gpsd for GPS. It runs as a normal process and outputs NMEA on TCP. Target devices: Toughpad FZ-G1 and any Linux system with IIO IMU and gpsd.

**Android and iPhone: yes, via remote.** Run the daemon on a Linux host with `--source=remote`. An Android or iOS app reads device sensors and GPS, then sends JSON over TCP to the daemon; the daemon fuses and outputs NMEA. All three platforms supported: Linux natively, Android and iOS as TCP clients.

**Remote protocol.** With `--source=remote`, the daemon listens on `--remote-port` (default 2949). Client sends newline-delimited JSON: IMU `{"accel":[x,y,z],"gyro":[x,y,z],"magnetometer":[x,y,z]}` (accel m/s^2, gyro deg/s, magnetometer uT; magnetometer is optional), GPS `{"lat":float,"lon":float,"alt":float,"speed_ms":float,"track":float,"time_iso":str|null}`. One line can contain all keys.

For in-app fusion on Android or iOS without the daemon, use the platform APIs (SensorManager rotation vector, Core Motion device motion) inside Navit’s platform-specific vehicle code using the APIs described in the Comparison table above.

**Build instructions:** See [BUILD.md](BUILD.md) for platform-specific build and packaging instructions for Linux, Android, and iOS.

### Supported IMU devices (Raspberry Pi and Linux)

The daemon supports common IMU sensors used with Raspberry Pi and other Linux systems via the Linux IIO subsystem. Devices are auto-detected, or you can specify paths manually.

**Supported IMUs:**

| IMU Model | Sensors | Driver | Notes |
|-----------|---------|--------|-------|
| **MPU6050** | Accel + Gyro (6-axis) | `i2c-mpu6050` | Very common, I2C interface |
| **MPU6500** | Accel + Gyro (6-axis) | `i2c-mpu6050` | Similar to MPU6050 |
| **MPU9250** | Accel + Gyro + Mag (9-axis) | `i2c-mpu6050` | Includes magnetometer (AK8963) |
| **MPU9255** | Accel + Gyro + Mag (9-axis) | `i2c-mpu6050` | Similar to MPU9250 |
| **LSM6DS3** | Accel + Gyro (6-axis) | `st_lsm6dsx` | STMicroelectronics |
| **LSM6DSO** | Accel + Gyro (6-axis) | `st_lsm6dsx` | STMicroelectronics |
| **LSM6DSL** | Accel + Gyro (6-axis) | `st_lsm6dsx` | STMicroelectronics |
| **LSM6DSM** | Accel + Gyro (6-axis) | `st_lsm6dsx` | STMicroelectronics |
| **BNO055** | Accel + Gyro + Mag (9-axis) | `bno055` | Includes built-in fusion (optional) |
| **ICM20948** | Accel + Gyro + Mag (9-axis) | `inv_icm20948` | InvenSense |
| **ADXL345** | Accel only (3-axis) | `adxl345` | Accelerometer only (no gyro/mag) |

**Setup instructions:**

1. **Enable I2C/SPI** (if needed):
   ```bash
   # Raspberry Pi: Enable I2C
   sudo raspi-config  # Interface Options -> I2C -> Enable
   # Or edit /boot/config.txt and add: dtparam=i2c_arm=on
   ```

2. **Load kernel driver** (usually automatic):
   ```bash
   # Check if driver is loaded
   lsmod | grep -E "(mpu6050|lsm6ds|bno055|icm20948|adxl345)"
   
   # Check IIO devices
   ls -la /sys/bus/iio/devices/
   ```

3. **Verify device detection**:
   ```bash
   # List IIO devices
   cat /sys/bus/iio/devices/iio:device*/name
   
   # Check available channels
   ls /sys/bus/iio/devices/iio:device0/
   ```

4. **Run daemon** (auto-detection):
   ```bash
   # Daemon will auto-detect IMU devices
   navit-daemon --source=linux
   
   # Or specify paths manually
   navit-daemon --accel-path /sys/bus/iio/devices/iio:device0 \
                --gyro-path /sys/bus/iio/devices/iio:device0 \
                --magnetometer-path /sys/bus/iio/devices/iio:device1
   ```

**Device-specific notes:**

- **MPU6050/MPU9250**: Very common on Raspberry Pi HATs. Usually appears as `iio:device0` with both accel and gyro channels. MPU9250 includes magnetometer (may appear as separate device or same device).
- **LSM6DS series**: Often found on development boards. Accel and gyro typically on same device.
- **BNO055**: Has built-in fusion chip; can use its orientation directly or use raw sensor data. The daemon uses raw data for consistency.
- **ADXL345**: Accelerometer only; requires separate gyroscope for AHRS. Not recommended for heading without gyro.

**Troubleshooting:**

- If devices aren't detected, check kernel driver is loaded: `dmesg | grep -i iio`
- Verify I2C/SPI is enabled and device is connected: `i2cdetect -y 1` (for I2C bus 1)
- Check device permissions: `ls -la /sys/bus/iio/devices/iio:device*/in_accel_*_raw`
- Enable debug logging: `navit-daemon --debug` to see device discovery messages

### How the Navit codebase can benefit from these sensors

The following is based on the Navit codebase at `../navit` (or the navit repo). Navit consumes position and direction via the vehicle plugin interface. Key attributes are `position_direction` (heading in degrees), `position_speed`, `position_coord_geo`, and optionally `position_magnetic_direction`. Providing better or continuous direction from magnetometer/gyro/accelerometer fusion improves several areas:

**1. Direction source today**

- **vehicle_gpsd.c:** `position_direction` comes from gpsd `data->fix.track` (GPS course-over-ground). Only valid when moving and when GPS has fix.
- **vehicle_android.c:** Direction from `Location.getBearing()` (GPS or fused provider; often 0 or stale when stationary).
- **vehicle_iphone.c:** Direction from Core Location (course). Same limitations when stationary or in poor GPS.

When GPS is lost or poor (tunnel, urban canyon, slow/stationary), direction is missing or stale. Fused IMU heading (magnetometer + gyro, optionally accelerometer) can supply continuous heading and fill these gaps.

**2. Tunnel extrapolation (track.c)**

When the user is on an underground segment and GPS is lost (`tr->tunnel == 1`), Navit extrapolates position using last known speed and direction: `transform_project(pro, &tr->curr_in, tr->speed * tr->tunnel_extrapolation / 36, tr->direction, &tr->curr_in)`. It uses `tr->direction` (last direction from the vehicle) and can fall back to road segment angle. If the vehicle plugin supplies direction from a fused IMU source (e.g. the daemon on Toughpad feeding NMEA/gpsd with heading from Fusion AHRS), tunnel extrapolation stays accurate, especially on curved roads, instead of relying on a single stale GPS bearing.

**3. Vehicle cursor and map rotation (navit.c, vehicle.c)**

The map vehicle icon rotation uses `position_direction`: `nv->dir = *attr_dir.u.numd` then `vehicle_draw(..., nv->dir - transform_get_yaw(...), nv->speed)`. So the on-screen heading comes directly from the vehicle. Better, more frequent direction (e.g. from IMU) keeps the icon and map orientation aligned with the real heading when GPS bearing is absent or laggy.

**4. Compass OSD (osd_core.c)**

The compass OSD draws from `position_direction` via `vehicle_get_attr(v, attr_position_direction, &attr_dir, NULL)`. With magnetometer-based or fused heading, the compass remains usable when GPS bearing is unavailable (e.g. standing still or in a tunnel).

**5. Street matching and turn hints (track.c)**

Tracking uses `tr->curr_angle` / `tr->direction` together with road segment angles (`tracking_angle_delta`, `street_direction` for forward/backward). More accurate and stable heading improves which street segment is selected and whether Navit thinks you are moving with or against the segment, especially on winding roads.

**6. Lag extrapolation (track.c)**

When `attr_lag` is set, position is extrapolated using speed and direction; direction is interpolated between previous and current: `edirection = direction + tracking_angle_diff(direction, tr->direction, 360) * lag.u.num / 10`. More frequent, stable direction updates from an IMU reduce jumps and make this extrapolation smoother.

**7. Pedestrian plugin (plugin/pedestrian/pedestrian.c)**

On Android, the pedestrian plugin already uses magnetometer and accelerometer: it derives device orientation (portrait/landscape/flat) and yaw from raw sensor data and sets `attr_orientation` and transform pitch/yaw for the map view. So Navit already benefits from these sensors in pedestrian mode; the same idea (sensor-derived heading) can be used to feed or correct `position_direction` when in vehicle mode and GPS bearing is poor or absent.

**8. position_magnetic_direction**

The attribute exists (e.g. vehicle_file.c, vehicle_wince.c) but is not widely used. It could be used for true vs magnetic north on the compass or as an input to fusion when both GPS track and magnetic heading are available.

**Summary**

Navit benefits from sensor-derived or sensor-fused heading wherever it currently uses `position_direction`: tunnel dead reckoning, vehicle icon rotation, compass OSD, street matching, and lag compensation. On Android and iPhone, improving the vehicle plugin to use fused orientation (e.g. rotation vector or device motion) when GPS bearing is invalid would help. On Toughpad FZ-G1, the Python daemon that fuses IIO IMU + gpsd and outputs NMEA/gpsd is the way to supply that improved direction to Navit.

---

## The Toughpad FZ-G1 series
Likely uses STMicroelectronics sensor models:
Accelerometer:

LIS3DH - Very common 3-axis accelerometer in tablets/laptops from that era
LIS2DH - Similar to LIS3DH, also widely used
LIS331DLH - Another possibility

Gyroscope + Accelerometer combined:

LSM6DS0 - System-in-package with both 3-axis accelerometer and 3-axis gyroscope
LSM6DSx series (LSM6DS3, LSM6DSL, etc.) - Newer versions with similar functionality

Magnetometer (for digital compass):

LIS3MDL - 3-axis magnetometer
LSM303 series - Another common option

Which Toughpad models have these sensors:
All FZ-G1 models (MK1 through MK5) include the same basic sensor suite. Across all generations, the FZ-G1 has:

Ambient light sensor
Digital compass (magnetometer)
Gyro sensor
Acceleration sensor

FZ-G1 MK4 (FZ-G1R0-53TE) definitely has these sensors, and all other FZ-G1 variants (MK1, MK2, MK3, MK5) should have similar or identical sensor configurations.
