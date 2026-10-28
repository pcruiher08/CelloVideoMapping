import ARKit
import SceneKit
import SwiftUI

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
            if preview {
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
