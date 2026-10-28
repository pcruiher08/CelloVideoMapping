import ARKit
import CoreImage
import UIKit

/// Streams every ARKit frame it can keep up with to the Mac over a WebSocket:
/// a JPEG of the colour image, the LiDAR depth map and its confidence, and the
/// camera intrinsics scaled to the JPEG. Frames that arrive while one is still
/// being encoded or sent are dropped, so the Mac always gets the newest view.
///
/// Message: "CDP1", UInt32 little-endian header length, JSON header, then
/// JPEG bytes, depth (Float16 metres, dw x dh) and confidence (UInt8 0-2).
final class Streamer: NSObject, ObservableObject, ARSessionDelegate, URLSessionWebSocketDelegate {
    @Published var connected = false
    @Published var status = "not connected"

    private var task: URLSessionWebSocketTask?
    private var opened = false          // handshake done: only then are frames sent
    private var wanted: String?         // host to stay connected to (reconnects when the Mac restarts)
    private lazy var urlSession = URLSession(configuration: .default, delegate: self, delegateQueue: .main)
    private let ci = CIContext()
    private let queue = DispatchQueue(label: "encode")
    private var busy = false            // main thread only
    private var sent = 0
    private var lastReport = CACurrentMediaTime()
    private var orientation = "portrait"
    private let outWidth: CGFloat = 1280

    func start(session: ARSession) {
        guard ARWorldTrackingConfiguration.supportsFrameSemantics(.sceneDepth) else {
            status = "this iPhone has no LiDAR"
            return
        }
        let config = ARWorldTrackingConfiguration()
        config.frameSemantics = [.sceneDepth]
        if let format = ARWorldTrackingConfiguration.supportedVideoFormats.first(where: {
            $0.imageResolution.width == 1920 && $0.framesPerSecond == 60
        }) {
            config.videoFormat = format
        }
        session.run(config)
        UIDevice.current.beginGeneratingDeviceOrientationNotifications()
    }

    func connect(host: String) {
        wanted = host
        guard let url = URL(string: "ws://\(host)/ws/iphone") else {
            status = "bad address"
            return
        }
        let t = urlSession.webSocketTask(with: url)
        t.maximumMessageSize = 16 << 20
        task = t
        opened = false
        t.resume()
        connected = true
        status = "connecting to \(host)…"
        receive()
    }

    func disconnect() {
        wanted = nil
        task?.cancel(with: .goingAway, reason: nil)
        task = nil
        opened = false
        connected = false
        status = "not connected"
    }

    // A send on a socket still connecting is queued and reports success, so
    // "streaming" used to show even when the Mac was unreachable.
    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask,
                    didOpenWithProtocol protocol: String?) {
        guard webSocketTask === task else { return }
        opened = true
        status = "connected, waiting for frames…"
    }

    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask,
                    didCloseWith closeCode: URLSessionWebSocketTask.CloseCode, reason: Data?) {
        guard webSocketTask === task else { return }
        fail(NSError(domain: "CelloDepth", code: closeCode.rawValue,
                     userInfo: [NSLocalizedDescriptionKey: "the Mac closed the connection"]))
    }

    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        guard task === self.task, let error = error else { return }
        fail(error)
    }

    /// Commands from the Mac ("lock" / "unlock" the exposure); also notices
    /// the connection closing.
    private func receive() {
        task?.receive { [weak self] result in
            switch result {
            case .failure(let e): DispatchQueue.main.async { self?.fail(e) }
            case .success(let message):
                if case .string(let cmd) = message {
                    if cmd.hasPrefix("ping:") {
                        // clock sync: answer at once with this phone's clock
                        // (the same timebase as ARFrame.timestamp)
                        let pong = "pong:" + cmd.dropFirst(5) + ":" + String(CACurrentMediaTime())
                        self?.task?.send(.string(pong)) { _ in }
                    } else {
                        DispatchQueue.main.async { self?.command(cmd) }
                    }
                }
                self?.receive()
            }
        }
    }

    /// Exposure, white balance and focus locked: the structured-light
    /// calibration compares each stripe pattern with its inverse, and auto
    /// exposure re-adjusting between the two flips the bits in a bright room.
    /// A fixed focus also keeps the lens's focal length (the intrinsics) steady.
    private(set) var locked = false

    private func command(_ cmd: String) {
        guard let device = ARWorldTrackingConfiguration.configurableCaptureDeviceForPrimaryCamera else {
            status = "cannot lock the exposure on this iPhone"
            return
        }
        let lock = cmd == "lock"
        do {
            try device.lockForConfiguration()
            if lock {
                if device.isExposureModeSupported(.locked) { device.exposureMode = .locked }
                if device.isWhiteBalanceModeSupported(.locked) { device.whiteBalanceMode = .locked }
                if device.isFocusModeSupported(.locked) { device.focusMode = .locked }
            } else {
                if device.isExposureModeSupported(.continuousAutoExposure) { device.exposureMode = .continuousAutoExposure }
                if device.isWhiteBalanceModeSupported(.continuousAutoWhiteBalance) { device.whiteBalanceMode = .continuousAutoWhiteBalance }
                if device.isFocusModeSupported(.continuousAutoFocus) { device.focusMode = .continuousAutoFocus }
            }
            device.unlockForConfiguration()
            locked = lock
        } catch {
            status = "exposure lock failed: \(error.localizedDescription)"
        }
    }

    private func fail(_ e: Error) {
        guard task != nil else { return }
        task = nil
        opened = false
        connected = false
        busy = false
        status = "can't reach the Mac: \(e.localizedDescription)"
        if let host = wanted {               // keep trying until Stop
            status += " · retrying"
            connected = true
            DispatchQueue.main.asyncAfter(deadline: .now() + 2) { [weak self] in
                guard let self = self, self.wanted == host, self.task == nil else { return }
                self.connect(host: host)
            }
        }
    }

    func session(_ session: ARSession, didUpdate frame: ARFrame) {
        switch UIDevice.current.orientation {
        case .portrait: orientation = "portrait"
        case .portraitUpsideDown: orientation = "portraitUpsideDown"
        case .landscapeLeft: orientation = "landscapeLeft"
        case .landscapeRight: orientation = "landscapeRight"
        default: break                   // face up/down: keep the last one
        }
        guard let task = task, opened, !busy, let depth = frame.sceneDepth else { return }
        busy = true
        let tDeliver = CACurrentMediaTime()   // ARKit hands the frame over
        let image = frame.capturedImage
        let K = frame.camera.intrinsics
        let ts = frame.timestamp
        let depthMap = depth.depthMap
        let confidence = depth.confidenceMap
        let orient = orientation
        let isLocked = locked
        queue.async { [weak self] in
            guard let self = self else { return }
            let data = self.pack(image: image, K: K, depth: depthMap, confidence: confidence,
                                 ts: ts, orientation: orient, locked: isLocked, tDeliver: tDeliver)
            task.send(.data(data)) { err in
                DispatchQueue.main.async {
                    self.busy = false
                    if let err = err { self.fail(err) } else { self.count() }
                }
            }
        }
    }

    private func count() {
        sent += 1
        let now = CACurrentMediaTime()
        if now - lastReport >= 1 {
            status = String(format: "streaming %.0f fps · %@", Double(sent) / (now - lastReport), orientation)
            sent = 0
            lastReport = now
        }
    }

    private func pack(image: CVPixelBuffer, K: simd_float3x3, depth: CVPixelBuffer,
                      confidence: CVPixelBuffer?, ts: TimeInterval, orientation: String,
                      locked: Bool, tDeliver: TimeInterval) -> Data {
        // colour: the sensor image (always landscape), scaled to outWidth
        let iw = CGFloat(CVPixelBufferGetWidth(image))
        let ih = CGFloat(CVPixelBufferGetHeight(image))
        let s = outWidth / iw
        let scaled = CIImage(cvPixelBuffer: image).transformed(by: CGAffineTransform(scaleX: s, y: s))
        let jpeg = ci.jpegRepresentation(
            of: scaled, colorSpace: CGColorSpaceCreateDeviceRGB(),
            options: [kCGImageDestinationLossyCompressionQuality as CIImageRepresentationOption: 0.7]) ?? Data()

        // depth: Float32 metres -> Float16, rows packed
        let dw = CVPixelBufferGetWidth(depth)
        let dh = CVPixelBufferGetHeight(depth)
        var d16 = [Float16](repeating: 0, count: dw * dh)
        CVPixelBufferLockBaseAddress(depth, .readOnly)
        if let base = CVPixelBufferGetBaseAddress(depth) {
            let stride = CVPixelBufferGetBytesPerRow(depth)
            for y in 0..<dh {
                let row = (base + y * stride).assumingMemoryBound(to: Float32.self)
                for x in 0..<dw { d16[y * dw + x] = Float16(row[x]) }
            }
        }
        CVPixelBufferUnlockBaseAddress(depth, .readOnly)

        var conf = Data()
        if let c = confidence {
            CVPixelBufferLockBaseAddress(c, .readOnly)
            if let base = CVPixelBufferGetBaseAddress(c) {
                let stride = CVPixelBufferGetBytesPerRow(c)
                for y in 0..<CVPixelBufferGetHeight(c) {
                    conf.append(Data(bytes: base + y * stride, count: CVPixelBufferGetWidth(c)))
                }
            }
            CVPixelBufferUnlockBaseAddress(c, .readOnly)
        }

        // intrinsics are for the full sensor image; simd is column-major
        let header: [String: Any] = [
            "w": Int((iw * s).rounded()), "h": Int((ih * s).rounded()),
            "fx": Double(K[0][0]) * Double(s), "fy": Double(K[1][1]) * Double(s),
            "cx": Double(K[2][0]) * Double(s), "cy": Double(K[2][1]) * Double(s),
            "dw": dw, "dh": dh, "ts": ts, "orientation": orientation, "locked": locked,
            // latency breakdown (phone clock, seconds): captured, delivered, encoded
            "t_cap": ts, "t_deliver": tDeliver, "t_send": CACurrentMediaTime(),
            "jpeg": jpeg.count, "depth": d16.count * 2, "conf": conf.count,
        ]
        let headerData = (try? JSONSerialization.data(withJSONObject: header)) ?? Data()
        var out = Data("CDP1".utf8)
        var n = UInt32(headerData.count).littleEndian
        out.append(Data(bytes: &n, count: 4))
        out.append(headerData)
        out.append(jpeg)
        d16.withUnsafeBufferPointer { out.append(Data(buffer: $0)) }
        out.append(conf)
        return out
    }
}
