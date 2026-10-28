import ARKit
import SceneKit
import SwiftUI

/// Camera preview; the same ARSession feeds the streamer.
struct ARPreview: UIViewRepresentable {
    let streamer: Streamer

    func makeUIView(context: Context) -> ARSCNView {
        let view = ARSCNView(frame: .zero)
        view.automaticallyUpdatesLighting = false
        view.session.delegate = streamer
        streamer.start(session: view.session)
        return view
    }

    func updateUIView(_ uiView: ARSCNView, context: Context) {}
}

struct ContentView: View {
    @StateObject private var streamer = Streamer()
    @AppStorage("host") private var host = "10.22.205.165:8000"

    var body: some View {
        ZStack(alignment: .bottom) {
            ARPreview(streamer: streamer).ignoresSafeArea()
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
                }
                Text(streamer.status)
                    .font(.footnote.monospaced())
                    .foregroundStyle(.white)
            }
            .padding()
            .background(.black.opacity(0.55))
        }
        .onAppear {
            UIApplication.shared.isIdleTimerDisabled = true      // a mounted phone must not sleep
            if !streamer.connected { streamer.connect(host: host) }   // and should not need a tap
        }
    }
}
