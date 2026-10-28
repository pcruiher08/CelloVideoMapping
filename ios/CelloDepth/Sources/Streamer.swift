import ARKit
import CoreImage
import UIKit

/// Streams every camera frame it can keep up with to the Mac over a WebSocket:
/// a JPEG of the colour image, the LiDAR depth map (and its confidence, with
/// ARKit), and the camera intrinsics. Frames come from the LiDAR camera
/// directly (AVFoundation, the default: cooler, less delay) or from ARKit. Up to two frames are in flight (one encoding while the
/// other is on the wire); frames arriving beyond that are dropped, so the Mac
/// always gets a recent view. One at a time capped the stream at ~20 fps:
/// each frame waited for the previous send to finish before encoding.
///
/// Message: "CDP1", UInt32 little-endian header length, JSON header, then
/// JPEG bytes, and depth (Float16 metres, dw x dh) followed by confidence
/// (UInt8 0-2), raw-deflated together when the header has "z".
final class Streamer: NSObject, ObservableObject, ARSessionDelegate, URLSessionWebSocketDelegate {
    @Published var connected = false
    @Published var status = "not connected"

    private var task: URLSessionWebSocketTask?
    private var opened = false          // handshake done: only then are frames sent
    private var wanted: String?         // host to stay connected to (reconnects when the Mac restarts)
    private lazy var urlSession = URLSession(configuration: .default, delegate: self, delegateQueue: .main)
    private let ci = CIContext()
    private let queue = DispatchQueue(label: "encode")
    private var inFlight = 0            // frames encoding or sending; main thread only
    private let maxInFlight = 2
    private var sent = 0
    // what the camera delivers, before any frame is dropped here, and why it
    // may be slow (sent to the Mac in each header)
    private var camFrames = 0
    private var camStart = CACurrentMediaTime()
    private var camFps = 0.0
    private var lastReport = CACurrentMediaTime()
    private var orientation = "portrait"
    // the image the Mac works at (its calibrations are in these pixels) and
    // the smaller one actually sent: 1280 px frames at 30 fps were ~390 KB
    // each, more than the Wi-Fi carried, so frames bunched up and the Mac got
    // ~20 fps. Segmentation runs at 512 px, so 960 loses nothing; the Mac
    // scales it back up
    private let outWidth: CGFloat = 1280
    private let sendWidth: CGFloat = 960

    enum Capture: String { case camera, arkit }
    @Published private(set) var capture: Capture =
        Capture(rawValue: UserDefaults.standard.string(forKey: "capture") ?? "") ?? .camera

    /// Owned here, not by the preview view, so the preview can be removed
    /// while streaming: drawing the camera on the phone's screen at 60 fps
    /// is heat the phone does not need, and a hot phone (thermal state
    /// critical) gets ARKit throttled to 20 fps.
    let session = ARSession()
    let camera = DepthCamera()
    private var started = false

    func start() {
        guard !started else { return }
        started = true
        session.delegate = self
        camera.onFrame = { [weak self] image, K, depth, ts in
            let tDeliver = CACurrentMediaTime()
            DispatchQueue.main.async {
                self?.handle(image: image, K: K, depth: depth, confidence: nil, ts: ts, tDeliver: tDeliver)
            }
        }
        UIDevice.current.beginGeneratingDeviceOrientationNotifications()
        run(capture)
    }

    /// Switch between the LiDAR camera and ARKit (they cannot share the camera).
    func use(_ c: Capture) {
        guard c != capture else { return }
        UserDefaults.standard.set(c.rawValue, forKey: "capture")
        if capture == .arkit { session.pause() } else { camera.stop() }
        locked = false
        capture = c
        run(c)
    }

    private func run(_ c: Capture) {
        if c == .camera {
            if let problem = camera.start() { status = problem }
            return
        }
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
        let dev = capture == .camera ? camera.device
            : ARWorldTrackingConfiguration.configurableCaptureDeviceForPrimaryCamera
        guard let device = dev else {
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
        inFlight = 0
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
        guard let depth = frame.sceneDepth else { return }
        handle(image: frame.capturedImage, K: frame.camera.intrinsics, depth: depth.depthMap,
               confidence: depth.confidenceMap, ts: frame.timestamp, tDeliver: CACurrentMediaTime())
    }

    /// One frame from either source (main thread): `K` in pixels of `image`,
    /// `depth` Float32 metres, `ts` the capture time on the host clock.
    private func handle(image: CVPixelBuffer, K: simd_float3x3, depth: CVPixelBuffer,
                        confidence: CVPixelBuffer?, ts: TimeInterval, tDeliver: TimeInterval) {
        switch UIDevice.current.orientation {
        case .portrait: orientation = "portrait"
        case .portraitUpsideDown: orientation = "portraitUpsideDown"
        case .landscapeLeft: orientation = "landscapeLeft"
        case .landscapeRight: orientation = "landscapeRight"
        default: break                   // face up/down: keep the last one
        }
        camFrames += 1
        let tNow = CACurrentMediaTime()
        if tNow - camStart >= 1 {
            camFps = Double(camFrames) / (tNow - camStart)
            camFrames = 0
            camStart = tNow
        }
        guard let task = task, opened, inFlight < maxInFlight else { return }
        inFlight += 1
        let orient = orientation
        let isLocked = locked
        let diag: [String: Any] = ["cam_fps": camFps, "src": capture.rawValue,
                                   "thermal": ProcessInfo.processInfo.thermalState.rawValue,
                                   "lowpower": ProcessInfo.processInfo.isLowPowerModeEnabled]
        queue.async { [weak self] in
            guard let self = self else { return }
            let data = self.pack(image: image, K: K, depth: depth, confidence: confidence,
                                 ts: ts, orientation: orient, locked: isLocked, tDeliver: tDeliver,
                                 diag: diag)
            task.send(.data(data)) { err in
                DispatchQueue.main.async {
                    self.inFlight = max(0, self.inFlight - 1)
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
                      locked: Bool, tDeliver: TimeInterval, diag: [String: Any]) -> Data {
        // colour: the sensor image (always landscape), scaled to outWidth
        let iw = CGFloat(CVPixelBufferGetWidth(image))
        let ih = CGFloat(CVPixelBufferGetHeight(image))
        let s = outWidth / iw
        let ss = sendWidth / iw
        let scaled = CIImage(cvPixelBuffer: image).transformed(by: CGAffineTransform(scaleX: ss, y: ss))
        let jpeg = ci.jpegRepresentation(
            of: scaled, colorSpace: CGColorSpaceCreateDeviceRGB(),
            options: [kCGImageDestinationLossyCompressionQuality as CIImageRepresentationOption: 0.6]) ?? Data()

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

        // intrinsics are for the full camera image; simd is column-major
        let header: [String: Any] = [
            "w": Int((iw * s).rounded()), "h": Int((ih * s).rounded()),
            "fx": Double(K[0][0]) * Double(s), "fy": Double(K[1][1]) * Double(s),
            "cx": Double(K[2][0]) * Double(s), "cy": Double(K[2][1]) * Double(s),
            "dw": dw, "dh": dh, "ts": ts, "orientation": orientation, "locked": locked,
            // latency breakdown (phone clock, seconds): captured, delivered, encoded
            "t_cap": ts, "t_deliver": tDeliver, "t_send": CACurrentMediaTime(),
            "jpeg": jpeg.count, "depth": d16.count * 2, "conf": conf.count,
        ]
        var fields = header.merging(diag) { a, _ in a }
        // depth + confidence deflated together (smooth depth and a mostly
        // constant confidence shrink well): raw deflate, zlib.decompress(b, -15)
        var block = Data()
        d16.withUnsafeBufferPointer { block.append(Data(buffer: $0)) }
        block.append(conf)
        if let z = try? (block as NSData).compressed(using: .zlib) as Data {
            fields["z"] = z.count
            block = z
        }
        let headerData = (try? JSONSerialization.data(withJSONObject: fields)) ?? Data()
        var out = Data("CDP1".utf8)
        var n = UInt32(headerData.count).littleEndian
        out.append(Data(bytes: &n, count: 4))
        out.append(headerData)
        out.append(jpeg)
        out.append(block)
        return out
    }
}
