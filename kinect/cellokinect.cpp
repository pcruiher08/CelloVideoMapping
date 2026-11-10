// Kinect v2 -> stdout, for cellomask/kinect.py.
//
// libfreenect2 is C++ and its OpenGL depth decoder wants the main thread of
// its own process, so the Kinect is read here and the frames are piped to
// the app rather than loaded into Python.
//
// stdout: one "KV2H" message, then one "KV2F" message per frame, each
//   4-byte tag, little-endian uint32 JSON length, JSON, payload.
//   KV2H JSON: colour size and intrinsics, depth grid size, serial.
//   KV2F JSON: seq, t (host time, s), locked, color (a new colour image
//   follows); payload: colour BGR (w*h*3, only when "color" is true),
//   depth uint16 mm (dw*dh, 0 = none), hits uint8 (dw*dh).
// One message per depth frame (always 30 a second): the colour camera
// drops to 15 fps in a dim room, and the depth-only tracking between
// detections needs no new colour.
// The image is un-mirrored (libfreenect2 delivers a mirror view), and the
// depth is the Kinect's registered onto the colour image, kept as the
// nearest reading in each BLOCK x BLOCK cell (the depth camera has ~1/9 of
// the colour camera's pixels, so the full-size map is mostly holes).
// stdin, one per line: "lock" (hold exposure), "unlock", "quit".

#include <libfreenect2/libfreenect2.hpp>
#include <libfreenect2/frame_listener_impl.h>
#include <libfreenect2/registration.h>
#include <libfreenect2/packet_pipeline.h>
#include <libfreenect2/logger.h>

#include <atomic>
#include <chrono>
#include <cmath>
#include <csignal>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <string>
#include <thread>
#include <vector>
#include <unistd.h>

static const int BLOCK = 4;
static std::atomic<bool> running(true);
static std::atomic<int> lock_request(-1);          // -1 none, 0 unlock, 1 lock
static std::atomic<double> last_frame(0.0);        // when a frame last went out

static double now_s() {
    using namespace std::chrono;
    return duration<double>(system_clock::now().time_since_epoch()).count();
}

static bool write_all(const void *p, size_t n) {
    const char *c = static_cast<const char *>(p);
    while (n) {
        ssize_t k = ::write(1, c, n);
        if (k <= 0) return false;                  // the app went away
        c += k;
        n -= size_t(k);
    }
    return true;
}

static bool send(const char *tag, const std::string &json, const std::vector<const void *> &parts,
                 const std::vector<size_t> &sizes) {
    uint32_t n = uint32_t(json.size());
    if (!write_all(tag, 4) || !write_all(&n, 4) || !write_all(json.data(), n)) return false;
    for (size_t i = 0; i < parts.size(); ++i)
        if (!write_all(parts[i], sizes[i])) return false;
    return true;
}

static void read_commands() {
    std::string line;
    while (running && std::getline(std::cin, line)) {
        if (line == "lock") lock_request = 1;
        else if (line == "unlock") lock_request = 0;
        else if (line == "quit") break;
    }
    running = false;                               // stdin closed: the app quit
}

int main(int argc, char **argv) {
    std::signal(SIGPIPE, SIG_IGN);
    std::signal(SIGINT, [](int) { running = false; });
    std::signal(SIGTERM, [](int) { running = false; });
    libfreenect2::setGlobalLogger(libfreenect2::createConsoleLogger(libfreenect2::Logger::Warning));
    std::string want = argc > 1 ? argv[1] : "gl";
    // "noedge": keep depth on sharp depth steps. The edge-aware filter drops
    // them as flying pixels, and with them a thin bow in front of a far wall
    // (all of it is edge), which the bow tracker needs
    bool edge_filter = !(argc > 2 && std::string(argv[2]) == "noedge");

    libfreenect2::Freenect2 fn;
    if (fn.enumerateDevices() == 0) {
        std::fprintf(stderr, "cellokinect: no Kinect v2 found (USB 3 port, and its power adapter on?)\n");
        return 2;
    }
    libfreenect2::PacketPipeline *pipeline =
        want == "cpu" ? static_cast<libfreenect2::PacketPipeline *>(new libfreenect2::CpuPacketPipeline())
                      : new libfreenect2::OpenGLPacketPipeline();
    libfreenect2::Freenect2Device *dev = fn.openDevice(fn.getDefaultDeviceSerialNumber(), pipeline);
    if (!dev) {
        std::fprintf(stderr, "cellokinect: could not open the Kinect\n");
        return 3;
    }
    libfreenect2::Freenect2Device::Config config;
    config.EnableEdgeAwareFilter = edge_filter;
    dev->setConfiguration(config);
    libfreenect2::SyncMultiFrameListener color_listener(libfreenect2::Frame::Color);
    libfreenect2::SyncMultiFrameListener depth_listener(libfreenect2::Frame::Depth);
    dev->setColorFrameListener(&color_listener);
    dev->setIrAndDepthFrameListener(&depth_listener);
    if (!dev->start()) {
        std::fprintf(stderr, "cellokinect: could not start the Kinect\n");
        return 4;
    }
    libfreenect2::Freenect2Device::ColorCameraParams cp = dev->getColorCameraParams();
    libfreenect2::Registration reg(dev->getIrCameraParams(), cp);
    libfreenect2::Frame undistorted(512, 424, 4), registered(512, 424, 4), bigdepth(1920, 1082, 4);
    libfreenect2::Frame last_color(1920, 1080, 4);   // registration needs a colour frame; its pixels do not matter

    const int W = 1920, H = 1080, DW = W / BLOCK, DH = H / BLOCK;
    char hd[512];
    // un-mirroring flips x, so the principal point moves to W - 1 - cx
    std::snprintf(hd, sizeof hd,
                  "{\"w\":%d,\"h\":%d,\"fx\":%.4f,\"fy\":%.4f,\"cx\":%.4f,\"cy\":%.4f,"
                  "\"dw\":%d,\"dh\":%d,\"serial\":\"%s\",\"firmware\":\"%s\",\"pipeline\":\"%s\"}",
                  W, H, cp.fx, cp.fy, W - 1 - cp.cx, cp.cy, DW, DH, dev->getSerialNumber().c_str(),
                  dev->getFirmwareVersion().c_str(), want == "cpu" ? "cpu" : "gl");
    if (!send("KV2H", hd, {}, {})) return 0;

    std::thread(read_commands).detach();
    // the app gone means stop, even if something else keeps our pipes open
    // (a process it started inheriting them): a helper outlived its app for
    // half an hour with the Kinect still on
    // no frames for 3 s: the USB link failed (LIBUSB_ERROR_OTHER after the
    // Kinect was moved left it silent, and the light froze on the cello).
    // Exit, and the app starts a fresh helper, which reopens the Kinect
    last_frame = now_s();
    std::thread([] {
        while (running) {
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
            if (now_s() - last_frame > 3.0) {
                std::fprintf(stderr, "cellokinect: no frames for 3 s (USB link?); restarting\n");
                std::_Exit(5);
            }
        }
    }).detach();
    pid_t parent = getppid();
    std::thread([parent] {
        while (running) {
            if (getppid() != parent) {
                std::fprintf(stderr, "cellokinect: the app is gone; exiting\n");
                std::_Exit(0);
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
        }
    }).detach();
    std::vector<uint8_t> bgr(size_t(W) * H * 3);
    std::vector<uint16_t> depth(size_t(DW) * DH);
    std::vector<uint8_t> hits(size_t(DW) * DH);
    libfreenect2::FrameMap frames, cframes;
    bool locked = false, have_color = false;
    unsigned long seq = 0;

    while (running) {
        if (!depth_listener.waitForNewFrame(frames, 2000)) {
            std::fprintf(stderr, "cellokinect: no frames for 2 s\n");
            continue;
        }
        double t = now_s();
        bool new_color = false;
        if (color_listener.hasNewFrame() && color_listener.waitForNewFrame(cframes, 0)) {
            // colour: BGRX (or RGBX), mirrored -> BGR, upright
            libfreenect2::Frame *rgb = cframes[libfreenect2::Frame::Color];
            const uint8_t *src = rgb->data;
            bool rgbx = rgb->format == libfreenect2::Frame::RGBX;
            for (int y = 0; y < H; ++y) {
                const uint8_t *s = src + size_t(y) * W * 4;
                uint8_t *d = bgr.data() + size_t(y) * W * 3;
                for (int x = 0; x < W; ++x) {
                    const uint8_t *p = s + size_t(W - 1 - x) * 4;
                    d[3 * x] = rgbx ? p[2] : p[0];
                    d[3 * x + 1] = p[1];
                    d[3 * x + 2] = rgbx ? p[0] : p[2];
                }
            }
            last_color.format = rgb->format;
            color_listener.release(cframes);
            new_color = have_color = true;
        }
        if (!have_color) {                        // nothing to register onto yet
            depth_listener.release(frames);
            continue;
        }
        libfreenect2::Frame *dep = frames[libfreenect2::Frame::Depth];
        reg.apply(&last_color, dep, &undistorted, &registered, true, &bigdepth);
        // depth: rows 1..1080 of bigdepth line up with the colour rows
        const float *bd = reinterpret_cast<const float *>(bigdepth.data) + W;
        for (int by = 0; by < DH; ++by)
            for (int bx = 0; bx < DW; ++bx) {
                float best = INFINITY;
                int n = 0;
                for (int y = by * BLOCK; y < (by + 1) * BLOCK; ++y)
                    for (int x = bx * BLOCK; x < (bx + 1) * BLOCK; ++x) {
                        float z = bd[size_t(y) * W + (W - 1 - x)];
                        if (std::isfinite(z) && z > 0) {
                            ++n;
                            if (z < best) best = z;
                        }
                    }
                size_t i = size_t(by) * DW + bx;
                depth[i] = n ? uint16_t(std::min(best, 65535.f)) : 0;
                hits[i] = uint8_t(n);
            }
        depth_listener.release(frames);

        int req = lock_request.exchange(-1);
        if (req == 1 && !locked) {
            // hold what auto exposure settled on
            float it = dev->getColorSettingFloat(libfreenect2::COLOR_SETTING_GET_INTEGRATION_TIME);
            float gain = dev->getColorSettingFloat(libfreenect2::COLOR_SETTING_GET_ANALOG_GAIN);
            if (it > 0 && gain > 0) {
                dev->setColorManualExposure(it, gain);
                locked = true;
            }
            std::fprintf(stderr, "cellokinect: exposure %s (%.2f ms, gain %.2f)\n",
                         locked ? "locked" : "not locked", it, gain);
        } else if (req == 0 && locked) {
            dev->setColorAutoExposure(0);
            locked = false;
        }

        char fj[160];
        std::snprintf(fj, sizeof fj, "{\"seq\":%lu,\"t\":%.6f,\"locked\":%s,\"color\":%s}", seq++, t,
                      locked ? "true" : "false", new_color ? "true" : "false");
        bool sent = new_color ? send("KV2F", fj, {bgr.data(), depth.data(), hits.data()},
                                     {bgr.size(), depth.size() * 2, hits.size()})
                              : send("KV2F", fj, {depth.data(), hits.data()}, {depth.size() * 2, hits.size()});
        if (!sent)
            break;
        last_frame = now_s();
    }
    // libfreenect2's stop can hang on macOS (the USB transfers never finish
    // cancelling), which left the Kinect running after the app quit: give
    // it two seconds, then leave anyway (the OS releases the device)
    std::thread([] {
        std::this_thread::sleep_for(std::chrono::seconds(2));
        std::fprintf(stderr, "cellokinect: the Kinect did not stop cleanly; exiting\n");
        std::_Exit(0);
    }).detach();
    if (locked) dev->setColorAutoExposure(0);
    dev->stop();
    dev->close();
    return 0;
}
