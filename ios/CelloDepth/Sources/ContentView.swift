import ARKit
import AVFoundation
import SceneKit
import SwiftUI

/// Preview of the LiDAR camera session (AVFoundation capture).
struct CameraPreview: UIViewRepresentable {
    let session: AVCaptureSession

    final class View: UIView {
        override class var layerClass: AnyClass { AVCaptureVideoPreviewLayer.self }
    }

    func makeUIView(context: Context) -> View {
        let v = View()
        let layer = v.layer as! AVCaptureVideoPreviewLayer
        layer.session = session
        layer.videoGravity = .resizeAspect
        return v
    }

    func updateUIView(_ uiView: View, context: Context) {}
}

/// Camera preview of the streamer's ARSession (only while shown).
struct ARPreview: UIViewRepresentable {
    let streamer: Streamer

    func makeUIView(context: Context) -> ARSCNView {
        let view = ARSCNView(frame: .zero)
        view.automaticallyUpdatesLighting = false
        view.session = streamer.session
        return view
    }

    func updateUIView(_ uiView: ARSCNView, context: Context) {}
}

struct ContentView: View {
    @StateObject private var streamer = Streamer()
    @AppStorage("host") private var host = "10.22.205.165:8000"
    // on until streaming starts (to aim the phone), then off to keep it cool
    @State private var preview = true

    var body: some View {
        ZStack(alignment: .bottom) {
            if preview && streamer.capture == .camera {
                CameraPreview(session: streamer.camera.session).ignoresSafeArea()
            } else if preview {
                ARPreview(streamer: streamer).ignoresSafeArea()
            } else {
                Color.black.ignoresSafeArea()
            }
            VStack(spacing: 8) {
                HStack {
                    TextField("Mac address:port", text: $host)
                        .textFieldStyle(.roundedBorder)
                        .keyboardType(.numbersAndPunctuation)
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)
                    Button(streamer.connected ? "Stop" : "Connect") {
                        if streamer.connected { streamer.disconnect() } else { streamer.connect(host: host) }
                    }
                    .buttonStyle(.borderedProminent)
                    Button(preview ? "Hide" : "View") { preview.toggle() }
                        .buttonStyle(.bordered)
                }
                Picker("Capture", selection: Binding(get: { streamer.capture },
                                                     set: { streamer.use($0) })) {
                    Text("LiDAR camera").tag(Streamer.Capture.camera)
                    Text("ARKit").tag(Streamer.Capture.arkit)
                }
                .pickerStyle(.segmented)
                Text(streamer.status)
                    .font(.footnote.monospaced())
                    .foregroundStyle(.white)
            }
            .padding()
            .background(.black.opacity(0.55))
        }
        .onChange(of: streamer.connected) { on in      // iOS 16 form
            if on { preview = false }
        }
        .onAppear {
            streamer.start()
            UIApplication.shared.isIdleTimerDisabled = true      // a mounted phone must not sleep
            if !streamer.connected { streamer.connect(host: host) }   // and should not need a tap
        }
    }
}
