package com.navit.daemon.client

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import java.io.BufferedWriter
import java.io.OutputStreamWriter
import java.net.Socket
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import kotlin.math.PI

class MainActivity : AppCompatActivity(), SensorEventListener, LocationListener {
    private lateinit var sensorManager: SensorManager
    private lateinit var locationManager: LocationManager
    private var accelerometer: Sensor? = null
    private var gyroscope: Sensor? = null
    private var socket: Socket? = null
    private var writer: BufferedWriter? = null
    private var isConnected = false

    private lateinit var statusText: TextView
    private lateinit var connectButton: Button

    private var lastAccel: FloatArray? = null
    private var lastGyro: FloatArray? = null
    private var lastLocation: Location? = null

    companion object {
        private const val TAG = "NavitDaemonClient"
        private const val PERMISSION_REQUEST_CODE = 1
        private const val DAEMON_HOST = "192.168.1.100"
        private const val DAEMON_PORT = 2949
        private const val SENSOR_DELAY_US = 10000L
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        statusText = findViewById(R.id.statusText)
        connectButton = findViewById(R.id.connectButton)

        sensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        locationManager = getSystemService(Context.LOCATION_SERVICE) as LocationManager

        accelerometer = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
        gyroscope = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE)

        connectButton.setOnClickListener {
            if (isConnected) {
                disconnect()
            } else {
                checkPermissionsAndConnect()
            }
        }

        updateStatus("Not connected")
    }

    private fun checkPermissionsAndConnect() {
        if (ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.ACCESS_FINE_LOCATION
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.ACCESS_FINE_LOCATION),
                PERMISSION_REQUEST_CODE
            )
        } else {
            connect()
        }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == PERMISSION_REQUEST_CODE &&
            grantResults.isNotEmpty() &&
            grantResults[0] == PackageManager.PERMISSION_GRANTED
        ) {
            connect()
        }
    }

    private fun connect() {
        Thread {
            try {
                socket = Socket(DAEMON_HOST, DAEMON_PORT)
                writer = BufferedWriter(OutputStreamWriter(socket!!.getOutputStream()))
                isConnected = true

                runOnUiThread {
                    updateStatus("Connected to $DAEMON_HOST:$DAEMON_PORT")
                    connectButton.text = "Disconnect"
                }

                sensorManager.registerListener(
                    this,
                    accelerometer,
                    SensorManager.SENSOR_DELAY_FASTEST
                )
                sensorManager.registerListener(
                    this,
                    gyroscope,
                    SensorManager.SENSOR_DELAY_FASTEST
                )

                if (ContextCompat.checkSelfPermission(
                        this,
                        Manifest.permission.ACCESS_FINE_LOCATION
                    ) == PackageManager.PERMISSION_GRANTED
                ) {
                    locationManager.requestLocationUpdates(
                        LocationManager.GPS_PROVIDER,
                        1000L,
                        1.0f,
                        this
                    )
                }
            } catch (e: Exception) {
                Log.e(TAG, "Connection failed", e)
                runOnUiThread {
                    updateStatus("Connection failed: ${e.message}")
                }
            }
        }.start()
    }

    private fun disconnect() {
        isConnected = false
        sensorManager.unregisterListener(this)
        locationManager.removeUpdates(this)

        try {
            writer?.close()
            socket?.close()
        } catch (e: Exception) {
            Log.e(TAG, "Disconnect error", e)
        }

        writer = null
        socket = null

        updateStatus("Disconnected")
        connectButton.text = "Connect"
    }

    override fun onSensorChanged(event: SensorEvent) {
        if (!isConnected || writer == null) return

        when (event.sensor.type) {
            Sensor.TYPE_ACCELEROMETER -> {
                lastAccel = event.values.clone()
            }
            Sensor.TYPE_GYROSCOPE -> {
                lastGyro = event.values.clone()
                sendIMUData()
            }
        }
    }

    override fun onAccuracyChanged(sensor: Sensor, accuracy: Int) {}

    override fun onLocationChanged(location: Location) {
        if (!isConnected || writer == null) return
        lastLocation = location
        sendGPSData()
    }

    private fun sendIMUData() {
        if (lastAccel == null || lastGyro == null) return

        try {
            val accelMps2 = floatArrayOf(
                lastAccel!![0],
                lastAccel!![1],
                lastAccel!![2]
            )
            val gyroDegPerS = floatArrayOf(
                Math.toDegrees(lastGyro!![0].toDouble()).toFloat(),
                Math.toDegrees(lastGyro!![1].toDouble()).toFloat(),
                Math.toDegrees(lastGyro!![2].toDouble()).toFloat()
            )

            val json = """{"accel":[${accelMps2[0]},${accelMps2[1]},${accelMps2[2]}],"gyro":[${gyroDegPerS[0]},${gyroDegPerS[1]},${gyroDegPerS[2]}]}"""
            writer!!.write(json)
            writer!!.newLine()
            writer!!.flush()
        } catch (e: Exception) {
            Log.e(TAG, "Send IMU failed", e)
            disconnect()
        }
    }

    private fun sendGPSData() {
        val loc = lastLocation ?: return

        try {
            val timeIso = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.US).apply {
                timeZone = TimeZone.getTimeZone("UTC")
            }.format(Date(loc.time))

            val json = """{"lat":${loc.latitude},"lon":${loc.longitude},"alt":${loc.altitude},"speed_ms":${loc.speed},"track":${loc.bearing.toDouble()},"time_iso":"$timeIso"}"""
            writer!!.write(json)
            writer!!.newLine()
            writer!!.flush()
        } catch (e: Exception) {
            Log.e(TAG, "Send GPS failed", e)
            disconnect()
        }
    }

    private fun updateStatus(text: String) {
        statusText.text = text
        Log.d(TAG, text)
    }

    override fun onDestroy() {
        super.onDestroy()
        disconnect()
    }
}
