# Build Instructions

This document describes how to build and package the Navit daemon for Linux, Android, and iOS.

## Linux

The daemon is a Python package. It can be installed as a standard Python package or run directly.

### Requirements

- Python 3.8 or higher
- pip
- Linux kernel with IIO subsystem (for `--source=linux`)
- gpsd (for GPS on Linux)

### Build and Install

```bash
# Install dependencies
pip install -e ".[dev]"

# Or install from source
pip install .

# Run directly without install
python -m navit_daemon --help
```

### Create Distribution Package

```bash
# Build wheel and source distribution
python -m build

# Outputs: dist/navit_daemon-0.1.0-py3-none-any.whl
#          dist/navit_daemon-0.1.0.tar.gz
```

### Systemd Service (Optional)

Create `/etc/systemd/system/navit-daemon.service`:

```ini
[Unit]
Description=Navit GPS+IMU fusion daemon
After=network.target gpsd.service

[Service]
Type=simple
User=navit
ExecStart=/usr/local/bin/navit-daemon --source=linux --nmea-port=2948
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable navit-daemon
sudo systemctl start navit-daemon
```

## Android

The Android client app reads device sensors (accelerometer, gyroscope, GPS) and sends JSON to the daemon over TCP.

### Requirements

- Android Studio Arctic Fox or later
- Android SDK API 21+ (Android 5.0+)
- Android device with accelerometer, gyroscope, and GPS

### Build

```bash
cd android
./gradlew assembleDebug

# Output: android/app/build/outputs/apk/debug/app-debug.apk
```

### Install

```bash
# Via ADB
adb install android/app/build/outputs/apk/debug/app-debug.apk

# Or build and install directly
./gradlew installDebug
```

### Configuration

The app requires:
- **Location permission** (for GPS)
- **Network permission** (to connect to daemon)
- **Daemon host/port** (set in app settings or via intent)

The daemon must be running on a reachable host with `--source=remote --remote-port=2949` (default).

## iOS

The iOS client app reads device sensors (accelerometer, gyroscope, GPS) and sends JSON to the daemon over TCP.

### Requirements

- Xcode 13 or later
- macOS (for building)
- iOS 13.0+ target
- iOS device with accelerometer, gyroscope, and GPS

### Build

```bash
cd ios
xcodebuild -workspace NavitDaemonClient.xcworkspace \
           -scheme NavitDaemonClient \
           -configuration Release \
           -sdk iphoneos \
           archive -archivePath build/NavitDaemonClient.xcarchive

# Or open in Xcode and build
open NavitDaemonClient.xcworkspace
```

### Install

1. Connect iOS device via USB
2. In Xcode: Product > Destination > Select your device
3. Product > Run (or Cmd+R)

For distribution:
- Archive: Product > Archive
- Export: Window > Organizer > Distribute App

### Configuration

The app requires:
- **Location permission** (Info.plist: `NSLocationWhenInUseUsageDescription`)
- **Network permission** (Info.plist: `NSAppTransportSecurity` if needed)
- **Daemon host/port** (set in app settings)

The daemon must be running on a reachable host with `--source=remote --remote-port=2949` (default).

## Cross-Platform Notes

### Python on Android/iOS

While Python can run on Android (via Termux, Kivy, PyDroid) and iOS (via Pythonista, Pyto), the daemon is designed to run on Linux. For Android/iOS, use the native client apps that implement the remote protocol.

### Remote Protocol

Both Android and iOS clients send newline-delimited JSON:

- **IMU:** `{"accel":[x,y,z],"gyro":[x,y,z]}` (accel in m/s^2, gyro in deg/s)
- **GPS:** `{"lat":float,"lon":float,"alt":float,"speed_ms":float,"track":float,"time_iso":"ISO8601"}`

One line can contain both IMU and GPS keys.

### Testing

1. Start daemon: `navit-daemon --source=remote --remote-port=2949`
2. Configure client app with daemon host/port
3. Start client app; it connects and sends sensor data
4. Daemon outputs NMEA on `--nmea-port` (default 2948)
