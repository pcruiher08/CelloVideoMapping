import AVFoundation

/// The LiDAR depth camera through AVFoundation, without ARKit.
///
/// ARKit also runs world tracking (visual-inertial SLAM) that this app never
/// uses: it heated the phone to thermal state "critical", where ARKit drops
/// to 20 fps, and it held each frame ~60 ms before handing it over. Here the
/// colour image and the LiDAR depth (registered to it by the system) come
/// straight from the camera, paired by timestamp.
final class DepthCamera: NSObject, AVCaptureDataOutputSynchronizerDelegate {
    let session = AVCaptureSession()
    private(set) var device: AVCaptureDevice?
    private let videoOutput = AVCaptureVideoDataOutput()
    private let depthOutput = AVCaptureDepthDataOutput()
    private var sync: AVCaptureDataOutputSynchronizer?
    private let queue = DispatchQueue(label: "depth-camera", qos: .userInteractive)

    /// Called on the camera queue: colour image, its intrinsics (pixels of
    /// that image), depth (Float32 metres), capture time (host clock).
    var onFrame: ((CVPixelBuffer, simd_float3x3, CVPixelBuffer, TimeInterval) -> Void)?

    /// Sets the session up and starts it; returns a problem, or nil.
    func start() -> String? {
        guard let dev = AVCaptureDevice.default(.builtInLiDARDepthCamera, for: .video, position: .back) else {
            return "this iPhone has no LiDAR camera"
        }
        device = dev
        // a 4:3 format with depth, 1920 wide like ARKit's (the Mac's
        // calibrations are for that framing); the fastest one
        let candidates = dev.formats.filter { f in
            let d = CMVideoFormatDescriptionGetDimensions(f.formatDescription)
            return !f.supportedDepthDataFormats.isEmpty && d.width * 3 == d.height * 4 && d.width >= 1280
        }
        func rate(_ f: AVCaptureDevice.Format) -> Double {
            f.videoSupportedFrameRateRanges.map(\.maxFrameRate).max() ?? 0
        }
        let format = candidates.filter {
            CMVideoFormatDescriptionGetDimensions($0.formatDescription).width == 1920
        }.max(by: { rate($0) < rate($1) }) ?? candidates.max(by: { rate($0) < rate($1) })
        guard let format = format else { return "no LiDAR video format with depth" }
        let depthFormat = format.supportedDepthDataFormats.filter {
            let t = CMFormatDescriptionGetMediaSubType($0.formatDescription)
            return t == kCVPixelFormatType_DepthFloat32 || t == kCVPixelFormatType_DepthFloat16
        }.max(by: {
            CMVideoFormatDescriptionGetDimensions($0.formatDescription).width <
                CMVideoFormatDescriptionGetDimensions($1.formatDescription).width
        })

        session.beginConfiguration()
        session.sessionPreset = .inputPriority          // the format chosen below, not a preset
        guard let input = try? AVCaptureDeviceInput(device: dev), session.canAddInput(input) else {
            session.commitConfiguration()
            return "cannot open the LiDAR camera"
        }
        session.addInput(input)
        videoOutput.videoSettings = [kCVPixelBufferPixelFormatTypeKey as String:
                                        kCVPixelFormatType_420YpCbCr8BiPlanarFullRange]
        videoOutput.alwaysDiscardsLateVideoFrames = true
        depthOutput.alwaysDiscardsLateDepthData = true
        depthOutput.isFilteringEnabled = true        // holes filled, like ARKit's sceneDepth
        guard session.canAddOutput(videoOutput), session.canAddOutput(depthOutput) else {
            session.commitConfiguration()
            return "cannot stream video and depth together"
        }
        session.addOutput(videoOutput)
        session.addOutput(depthOutput)
        if let c = videoOutput.connection(with: .video), c.isCameraIntrinsicMatrixDeliverySupported {
            c.isCameraIntrinsicMatrixDeliveryEnabled = true
        }
        do {
            try dev.lockForConfiguration()
            dev.activeFormat = format
            if let d = depthFormat { dev.activeDepthDataFormat = d }
            let fps = rate(format)
            dev.activeVideoMinFrameDuration = CMTime(value: 1, timescale: CMTimeScale(fps))
            dev.activeVideoMaxFrameDuration = CMTime(value: 1, timescale: CMTimeScale(fps))
            dev.unlockForConfiguration()
        } catch {
            session.commitConfiguration()
            return "camera setup failed: \(error.localizedDescription)"
        }
        session.commitConfiguration()

        let s = AVCaptureDataOutputSynchronizer(dataOutputs: [videoOutput, depthOutput])
        s.setDelegate(self, queue: queue)
        sync = s
        queue.async { self.session.startRunning() }
        return nil
    }

    func stop() {
        queue.async { self.session.stopRunning() }
    }

    func dataOutputSynchronizer(_ synchronizer: AVCaptureDataOutputSynchronizer,
                                didOutput collection: AVCaptureSynchronizedDataCollection) {
        guard let v = collection.synchronizedData(for: videoOutput) as? AVCaptureSynchronizedSampleBufferData,
              !v.sampleBufferWasDropped,
              let d = collection.synchronizedData(for: depthOutput) as? AVCaptureSynchronizedDepthData,
              !d.depthDataWasDropped,
              let image = CMSampleBufferGetImageBuffer(v.sampleBuffer) else { return }
        let depth = d.depthData.depthDataType == kCVPixelFormatType_DepthFloat32 ? d.depthData
            : d.depthData.converting(toDepthDataType: kCVPixelFormatType_DepthFloat32)
        guard let K = intrinsics(v.sampleBuffer, depth, CGFloat(CVPixelBufferGetWidth(image))) else { return }
        let ts = CMTimeGetSeconds(CMSampleBufferGetPresentationTimeStamp(v.sampleBuffer))
        onFrame?(image, K, depth.depthDataMap, ts)
    }

    /// The colour image's intrinsics in its own pixels: from the frame itself
    /// when the connection delivers them, else the depth's calibration
    /// (given for a reference size) scaled to the image.
    private func intrinsics(_ sb: CMSampleBuffer, _ depth: AVDepthData, _ width: CGFloat) -> simd_float3x3? {
        if let data = CMGetAttachment(sb, key: kCMSampleBufferAttachmentKey_CameraIntrinsicMatrix,
                                      attachmentModeOut: nil) as? Data {
            return data.withUnsafeBytes { $0.load(as: simd_float3x3.self) }
        }
        guard let cal = depth.cameraCalibrationData else { return nil }
        var K = cal.intrinsicMatrix
        let s = Float(width / cal.intrinsicMatrixReferenceDimensions.width)
        K[0][0] *= s; K[1][1] *= s; K[2][0] *= s; K[2][1] *= s
        return K
    }
}
