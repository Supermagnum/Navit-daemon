import SwiftUI
import CoreMotion
import CoreLocation

struct ContentView: View {
    @StateObject private var client = DaemonClient()
    
    var body: some View {
        VStack(spacing: 20) {
            Text("Navit Daemon Client")
                .font(.title)
            
            Text(client.status)
                .font(.body)
                .foregroundColor(client.isConnected ? .green : .red)
            
            Button(action: {
                if client.isConnected {
                    client.disconnect()
                } else {
                    client.connect()
                }
            }) {
                Text(client.isConnected ? "Disconnect" : "Connect")
                    .padding()
                    .background(client.isConnected ? Color.red : Color.green)
                    .foregroundColor(.white)
                    .cornerRadius(8)
            }
        }
        .padding()
    }
}

class DaemonClient: NSObject, ObservableObject, CLLocationManagerDelegate {
    @Published var status = "Not connected"
    @Published var isConnected = false
    
    private let motionManager = CMMotionManager()
    private let locationManager = CLLocationManager()
    private var outputStream: OutputStream?
    private let daemonHost = "192.168.1.100"
    private let daemonPort: UInt32 = 2949
    
    override init() {
        super.init()
        locationManager.delegate = self
        locationManager.desiredAccuracy = kCLLocationAccuracyBest
        locationManager.requestWhenInUseAuthorization()
        
        motionManager.accelerometerUpdateInterval = 0.01
        motionManager.gyroUpdateInterval = 0.01
    }
    
    func connect() {
        var readStream: Unmanaged<CFReadStream>?
        var writeStream: Unmanaged<CFWriteStream>?
        
        CFStreamCreatePairWithSocketToHost(
            nil,
            daemonHost as CFString,
            daemonPort,
            &readStream,
            &writeStream
        )
        
        outputStream = writeStream?.takeRetainedValue()
        outputStream?.open()
        
        if outputStream?.streamStatus == .open {
            isConnected = true
            status = "Connected to \(daemonHost):\(daemonPort)"
            
            startMotionUpdates()
            locationManager.startUpdatingLocation()
        } else {
            status = "Connection failed"
        }
    }
    
    func disconnect() {
        motionManager.stopAccelerometerUpdates()
        motionManager.stopGyroUpdates()
        motionManager.stopMagnetometerUpdates()
        locationManager.stopUpdatingLocation()
        outputStream?.close()
        outputStream = nil
        isConnected = false
        status = "Disconnected"
    }
    
    private func startMotionUpdates() {
        motionManager.startAccelerometerUpdates(to: .main) { [weak self] data, error in
            guard let self = self, let accel = data?.acceleration else { return }
            self.sendIMUData(accel: accel)
        }
        
        motionManager.startGyroUpdates(to: .main) { [weak self] data, error in
            guard let self = self, let gyro = data?.rotationRate else { return }
            self.sendIMUData(gyro: gyro)
        }
        
        if motionManager.isMagnetometerAvailable {
            motionManager.startMagnetometerUpdates(to: .main) { [weak self] data, error in
                guard let self = self, let mag = data?.magneticField else { return }
                self.sendIMUData(magnetometer: mag)
            }
        }
    }
    
    private var lastAccel: CMAcceleration?
    private var lastGyro: CMRotationRate?
    private var lastMagnetometer: CMMagneticField?
    
    private func sendIMUData(accel: CMAcceleration? = nil, gyro: CMRotationRate? = nil, magnetometer: CMMagneticField? = nil) {
        if let accel = accel {
            lastAccel = accel
        }
        if let gyro = gyro {
            lastGyro = gyro
        }
        if let magnetometer = magnetometer {
            lastMagnetometer = magnetometer
        }
        
        guard let accel = lastAccel, let gyro = lastGyro,
              let stream = outputStream else { return }
        
        let accelMps2 = [accel.x * 9.81, accel.y * 9.81, accel.z * 9.81]
        let gyroDegPerS = [
            gyro.x * 180.0 / .pi,
            gyro.y * 180.0 / .pi,
            gyro.z * 180.0 / .pi
        ]
        
        let json: String
        if let mag = lastMagnetometer {
            let magUt = [mag.x, mag.y, mag.z]
            json = String(format: """
                {"accel":[%.6f,%.6f,%.6f],"gyro":[%.6f,%.6f,%.6f],"magnetometer":[%.6f,%.6f,%.6f]}
                """,
                accelMps2[0], accelMps2[1], accelMps2[2],
                gyroDegPerS[0], gyroDegPerS[1], gyroDegPerS[2],
                magUt[0], magUt[1], magUt[2]
            )
        } else {
            json = String(format: """
                {"accel":[%.6f,%.6f,%.6f],"gyro":[%.6f,%.6f,%.6f]}
                """,
                accelMps2[0], accelMps2[1], accelMps2[2],
                gyroDegPerS[0], gyroDegPerS[1], gyroDegPerS[2]
            )
        }
        
        if let data = json.data(using: .utf8) {
            let bytes = data.withUnsafeBytes { $0.bindMemory(to: UInt8.self) }
            stream.write(bytes.baseAddress!, maxLength: data.count)
        }
    }
    
    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last, let stream = outputStream else { return }
        
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let timeIso = formatter.string(from: location.timestamp)
        
        let json = String(format: """
            {"lat":%.8f,"lon":%.8f,"alt":%.2f,"speed_ms":%.2f,"track":%.2f,"time_iso":"%@"}
            """,
            location.coordinate.latitude,
            location.coordinate.longitude,
            location.altitude,
            location.speed,
            location.course,
            timeIso
        )
        
        if let data = json.data(using: .utf8) {
            let bytes = data.withUnsafeBytes { $0.bindMemory(to: UInt8.self) }
            stream.write(bytes.baseAddress!, maxLength: data.count)
        }
    }
    
    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        status = "Location error: \(error.localizedDescription)"
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
