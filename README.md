# Navit-daemon
The Toughpad FZ-G1 series:
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
All FZ-G1 models (MK1 through MK5) include the same basic sensor suite according to the specifications we found earlier. The specs stated that across all generations, the FZ-G1 has:

Ambient light sensor
Digital compass (magnetometer)
Gyro sensor
Acceleration sensor

FZ-G1 MK4 (FZ-G1R0-53TE) definitely has these sensors, and all other FZ-G1 variants (MK1, MK2, MK3, MK5) should have similar or identical sensor configurations.

To get these to work with Navit and similar one needs a Python daemon that runs in the background. It reads GPS from gpsd, reads IMU data from Linux IIO, runs the Fusion algorithm to combine them, and outputs enhanced position data that Navit can consume.

Step 2: Install prerequisites
You'll need to install the necessary packages on your Linux system. Install Python3 development packages, the imufusion Python package which is the Python interface to the Fusion library, the gpsd client library for Python, and libiio Python bindings. You might also need the pyserial library if you want to create a virtual serial port for output.

Step 3: Test your sensor access
Before writing the wrapper, verify you can read both data sources. For GPS, test that you can connect to gpsd and get position data - it typically runs on localhost port 2947. For the IMU, check that the accelerometer and gyroscope appear in /sys/bus/iio/devices/ and that you can read raw values from the files there.

Step 4: Create the wrapper structure
Your Python wrapper needs several main components. First, an initialization section where you set up the Fusion AHRS algorithm with appropriate settings, connect to gpsd, and open the IIO device files for the accelerometer and gyroscope. Second, a main loop that runs continuously - it reads new IMU samples at a high rate (typically 100-200 Hz), reads GPS updates when available (usually 1 Hz), feeds the IMU data into the Fusion algorithm to get orientation, uses GPS position and velocity when available to correct for drift, and outputs the fused position estimate. Third, an output mechanism that formats the result as NMEA sentences and either writes to a virtual serial port or creates a new gpsd-compatible network service.

Step 5: Handle the IMU data
Read the raw accelerometer and gyroscope values from the IIO sysfs files, multiply by the scale factors to convert to proper units (m/s² for accelerometer, degrees/second for gyroscope), and feed these into the Fusion library. The library will calculate orientation (roll, pitch, yaw) from this data.

Step 6: Integrate GPS data
When GPS updates arrive from gpsd, you use the position (latitude, longitude, altitude) and velocity to anchor the IMU-based dead reckoning. The GPS provides absolute position fixes, while the IMU provides smooth, high-rate updates between GPS readings and can continue providing estimates during GPS outages.

Step 7: Handle the fusion
The Fusion library primarily gives you orientation (which direction you're facing). You need to combine this with GPS velocity to estimate position during GPS outages. When GPS is available, you use GPS position directly. When GPS is lost, you integrate velocity (from last GPS reading) using the orientation from the IMU to estimate how far you've moved.

Step 8: Output for Navit
Navit expects to read from either gpsd or directly from NMEA sentences. The easiest approach is to create a virtual serial port pair using socat, write NMEA sentences (especially GGA for position and RMC for position+velocity) to one end, and configure Navit or gpsd to read from the other end. Alternatively, you could modify gpsd to accept your data or create a simple TCP server that speaks the gpsd protocol.

Step 9: Handle timing and synchronization
The IMU should be sampled frequently (100+ Hz) while GPS updates arrive slowly (1 Hz). Your loop needs to handle these different rates. You might use Python's select or asyncio to handle the different data sources efficiently without blocking.

Step 10: Calibration
Before your system works well, you need calibration. The Fusion library has built-in gyroscope bias estimation, but you'll need to determine the accelerometer scale factors and offsets, figure out the mounting orientation of the IMU relative to the vehicle (which direction is forward), and possibly tune the Fusion algorithm settings like the gain parameter that controls how much it trusts the accelerometer versus the gyroscope.

Practical considerations:
Start simple - first just get orientation working by reading IMU and running Fusion to show roll, pitch, and yaw. Then add GPS reading and just pass GPS through unchanged. Then add the logic to detect GPS outages and use IMU + last velocity to estimate position. Test in a vehicle or while walking to see how well it maintains position during simulated GPS outages (you could block the GPS antenna temporarily).
The trickiest part will be the position estimation during GPS outages. The Fusion library gives you orientation but not position. You'll need to maintain velocity state and integrate it using the orientation to get position change.

This is a substantial project - probably a few weeks of part-time work to get something functional, and more time to tune it for good performance. But having the Fusion library handle the complex sensor fusion mathematics makes it much more achievable than starting from scratch.
