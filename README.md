# Cello Video Mapping

Projects TouchDesigner's visuals onto a played cello and sends TouchDesigner
the cello's and the bow's movement over OSC, with a **Kinect v2** and a
projector. **To install and run it, and for everything TouchDesigner receives,
see [TOUCHDESIGNER.md](TOUCHDESIGNER.md)**; the ready-to-run zip is under
[Releases](https://github.com/pcruiher08/CelloVideoMapping/releases).

The rest of this file documents the parts in detail, starting with the
original marker-based bow tracker (`bowtrack/`).

## Cello Bow Tracker (orange tape markers, webcam)

Real-time tracking of a cello bow's **x, y position and angle** from a webcam,
using two **orange gaffer tape** markers on the bow. Shows a live overlay plus
a metrics panel (position, angle, speed, up/down-bow direction, sparklines).
Built with videomapping in mind: tracking data can be streamed over **OSC** to
TouchDesigner, MadMapper, Resolume, Processing, etc.

## Setup

Markers: wrap a band of orange gaffer tape near the **frog** and another near
the **tip** of the bow (2–3 cm wide is plenty). Avoid other orange objects in
frame.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run

```bash
.venv/bin/python run.py                  # default webcam (index 0)
.venv/bin/python run.py --source 1       # external camera
.venv/bin/python run.py --source clip.mp4  # recorded video
.venv/bin/python run.py --flip           # mirror view
.venv/bin/python run.py --osc --osc-port 9000   # stream OSC for videomapping
```

First run on macOS: grant camera access to your terminal app in
*System Settings → Privacy & Security → Camera*.

### Keys

| Key | Action |
|-----|--------|
| `c` | Calibration mode — click the tape in the image to sample its color (click both markers; multiple clicks widen the range) |
| `m` | Toggle binary mask view (see exactly what the color filter detects) |
| `r` | Reset trail, metrics and HSV range to defaults |
| `s` | Save the calibrated HSV range to `config.json` (auto-loaded next run) |
| `q` | Quit |

## How it works

`bowtrack/tracker.py` converts each frame to HSV, thresholds the orange range,
cleans the mask with morphology, and takes the two best blobs as bow
endpoints. Endpoint identity (A/B) is kept stable across frames by
nearest-neighbor matching, so the angle doesn't flip. Position and angle are
smoothed with a **One Euro filter** (no lag on fast strokes, no jitter at
rest), and short occlusions are coasted through. `metrics.py` derives speed
and up/down-bow direction by projecting velocity onto the bow axis.

## OSC output (for videomapping)

With `--osc`, each frame sends:

| Address | Args |
|---------|------|
| `/bow/xy` | midpoint x, y — normalized 0..1, origin top-left |
| `/bow/angle` | degrees, 0 = horizontal, CCW positive |
| `/bow/ends` | ax, ay, bx, by — normalized endpoints |
| `/bow/speed` | midpoint speed in px/s |
| `/bow/ok` | 1 tracking / 0 lost |

## Tests

```bash
.venv/bin/python test_synthetic.py
```

Renders synthetic frames with moving orange markers and checks tracked
position/angle against ground truth, plus occlusion recovery.

## Videomapping (`--map`)

Renders generative visuals driven by the bow and corner-pins them onto a
physical surface, using the projector as a second screen.

```bash
.venv/bin/python run.py --map                # windowed, for setting up
.venv/bin/python run.py --map --fullscreen   # on the projector
```

The tracker runs in a worker thread and the renderer draws at vsync, so a
dropped camera frame does not stutter the projection.

### Setting up

1. **Turn off display mirroring** (System Settings → Displays). Mirroring
   leaves macOS reporting a single screen, so there is nothing separate to
   project onto. Extended gives the projector its own screen.
2. Calibrate the tape colour first with the normal view (`python run.py`,
   press `c`, click the orange tape, `s` to save) — `--map` reuses that
   `config.json`.
3. Run `--map --fullscreen`, press `c` for the calibration grid, and nudge
   the four corners until the projected grid lines up with the surface.
4. Press `s`. The calibration is written to `warp.json` as normalized
   coordinates, so it survives a resolution change.

### Keys

| Key | Action |
| --- | --- |
| `c` | calibration mode (shows the warp grid) |
| `1` `2` `3` `4` | select corner: TL, TR, BR, BL |
| arrows | nudge the selected corner (hold shift for coarse steps) |
| `g` | toggle the grid on its own |
| `s` / `r` | save `warp.json` / reset the warp to full screen |
| `[` `]` | shorter / longer motion trails |
| `f` | toggle fullscreen |
| `q` or esc | quit |

### How it renders

Three fullscreen passes per frame (`bowtrack/render.py`):

1. **fade** — darkens the accumulation buffer slightly; this is what makes
   the trails, at the cost of one texture rather than a growing CPU-side
   list of points.
2. **stroke** — additively draws the glowing bow segment. Hue follows the
   bow angle, brightness follows speed.
3. **warp** — samples the accumulation through the inverse homography so the
   content lands on the calibrated quad.

Content space is y-up (OpenGL's convention); projector space is y-down, so
"top-left" means the visually top-left corner when you are nudging it. The
homography in `bowtrack/warp.py` absorbs the flip.

To change the look, edit `_STROKE_FRAG` in `bowtrack/render.py` — it receives
`u_a`, `u_b`, `u_angle`, `u_speed`, `u_time` and `u_ok` as uniforms.

### Note on the Sony VPL-SW636C

Its built-in cameras are IR sensors for the interactive-pen feature and are
not available as a video source (no UVC interface; the USB port exposes only
a 5-byte HID mouse and a virtual CD). Use HDMI for the projection and the
Mac's built-in camera — or any USB webcam — for tracking.

## Camera selection and capture mode

`--source` takes `auto` (the built-in Mac camera), an index, part of a camera
name, or a video file path:

```bash
.venv/bin/python run.py --source brio --width 1280 --height 720 --fps 90
```

Name matching exists because AVFoundation reorders camera indices whenever an
iPhone Continuity Camera appears, so a fixed index is not stable.

### Logitech Brio 4K

Do not run it at 4K. 4K is capped at 30 fps, which is the worst setting here:

| Mode | Frame time | Pixels per frame |
| --- | --- | --- |
| 4K @ 30 | 33 ms | 8.3 M |
| 1080p @ 60 | 17 ms | 2.1 M |
| 720p @ 90 | 11 ms | 0.9 M |

Two orange tape markers resolve fine at 720p (`min_area` is 25 px), so 720p90
costs nothing in detection quality and removes ~22 ms of latency plus 9x the
per-frame work in `inRange` and the morphology passes.

Also:

- **Plug it directly into the Mac**, not a USB 2.0 hub or dock. High-framerate
  MJPEG needs USB 3.0 bandwidth.
- **MJPEG is requested by default** (`--no-mjpg` to disable). Raw formats
  cannot sustain 1080p60 over USB and the driver silently falls back to
  single-digit framerates.
- **Set the field of view to 65°** in Logi Tune. It ships at 90°, which spends
  most of the sensor on the room rather than the bow.
- **`--lock-exposure`** tries to disable auto exposure and auto white balance.
  These otherwise drift as projected light enters the scene, moving the HSV
  values of the tape out from under the threshold mid-performance.

macOS/AVFoundation does not report `CAP_PROP_FPS` or `CAP_PROP_FOURCC` back
(it returns 1 and -1), so passing `--fps` also measures and prints the rate
actually delivered. Trust that number, not the requested one.

## Running on another computer

```bash
./package.sh        # here: writes dist/cellotracking-YYYYMMDD.zip (~8 MB)
```

Copy the zip over, then:

```bash
unzip cellotracking-*.zip && cd cellotracking-*
./run.sh --source brio      # installs on first run, then starts the app
```

- `run.sh` calls `install.sh` every time. `install.sh` does nothing
  unless `requirements.txt` changed. On a new machine it creates `.venv` with
  the newest Python 3.10-3.13 it finds and installs everything (~1 GB with
  PyTorch, a few minutes). The browser opens by itself once the server answers.
- `./install.sh --force` rebuilds the environment; `PYTHON=/path/to/python3.12
  ./install.sh` picks the interpreter.
- The zip has the code, the trained model (`models/cello-seg.pt`) and the
  replacement images. Training data, runs and the SAM/base weights stay
  behind (~500 MB, only needed to retrain).
- No Python needed on the target machine: if no Python 3.10-3.13 is found (a
  stock Mac only has Apple's 3.9), `install.sh` downloads
  [uv](https://docs.astral.sh/uv/) and a standalone Python 3.12 into
  `.tools/` inside the folder. No admin rights, no shell profile changes.
  Needs internet the first time.
- Don't move the folder after installing (the venv stores absolute paths);
  if you do, run `./install.sh --force`.
- **Apple Silicon Macs** run the model on the GPU (MPS). **Linux** uses CUDA
  with an NVIDIA GPU, otherwise the CPU, which is too slow for live video. Selecting
  cameras by name only works on macOS; on Linux use an index (`--source 0`).
  Windows is not covered by these scripts (use WSL2 or install by hand).
- Plugged in a camera after starting? Restart: OpenCV numbers cameras at start-up.

## TouchDesigner (visuals on the cello)

The visuals come from TouchDesigner; this app puts them on the cello's front
face (segmentation, 3D mapping, prediction, learned outline) and drives the
projector. It also sends the cello's state to TouchDesigner over OSC.

**Video in**, in TouchDesigner after the final visual:

- **Syphon Spout Out TOP** when TouchDesigner runs on this same Mac (GPU
  sharing, no compression, ~1 frame of delay). Name the sender, e.g.
  `visuales_cello`; it appears here as `TouchDesigner / visuales_cello`.
- **NDI Out TOP** when it runs on another computer. Wired Ethernet is best;
  Wi-Fi works with a smaller image. If the two computers are on different
  subnets (NDI cannot find the sender), list the sender's IP in
  `~/.ndi/ndi-config.v1.json`: `{"ndi": {"networks": {"ips": "10.22.162.39"}}}`.
  A VPN exit node (Tailscale) can also swallow the traffic: turn it off.

In the web page: **TouchDesigner → Find NDI / Syphon senders**, then click
the sender's tile in the gallery. A portrait texture (about 1:2.4, e.g.
720x1728) fits the cello best. The choice is remembered across restarts
(`data/settings.json`), and the app waits for the sender if it is not up yet.

**OSC out**, every frame, to the address in *OSC to* (`127.0.0.1` when
TouchDesigner is on this Mac), port 9000 by default, for an **OSC In CHOP**:
`/cello/present x y angle size distance lean turn covered`,
`/tuner/freq note cents level`, `/vibrato/rate extent` (see
`cellomask/live.py`).

### Moving the project to the TouchDesigner Mac

Step by step, with everything TouchDesigner receives:
**[TOUCHDESIGNER.md](TOUCHDESIGNER.md)**. In short: download the zip from
[Releases](https://github.com/pcruiher08/CelloVideoMapping/releases), unzip,
`bash show.sh`. To make a new release zip here:

```bash
./package.sh --live "syphon:TouchDesigner / visuales_cello" --osc 127.0.0.1
gh release create vYYYY.MM.DD dist/cellotracking-*.zip --notes-file TOUCHDESIGNER.md
```

- The zip carries this rig's calibrations (projector, camera position, the
  cello's 3D scan and outline) and settings. They hold while the projector
  and the Kinect stay put; otherwise press **Calibrate 3D** there (it also
  rescans the cello, alone and still).
- The projector's HDMI goes to that Mac, set to **extend**.
- The Kinect plugs into that Mac (USB 3); `show.sh` uses it. With the iPhone
  instead (`SOURCE=lidar ./show.sh`), enter that Mac's address and port 8000
  in the **CelloDepth** app (`show.sh` prints it).
- Needs macOS 13+ and Python 3.10-3.13 (fetched automatically if missing);
  the NDI runtime comes with the `cyndilib` package.
- `test_live.py` checks NDI, Syphon and OSC on one Mac with stand-in senders.

### Kinect v2 as the depth camera

The Kinect v2 replaces the iPhone: colour and time-of-flight depth over
USB 3 (it needs its own power adapter), read by a small helper built on
[libfreenect2](https://github.com/OpenKinect/libfreenect2), which is not in
Homebrew. `install.sh` builds it (`bash kinect/build.sh`: Homebrew packages,
then libfreenect2 and `kinect/bin/cellokinect`, about a minute).

```bash
./show.sh                       # Kinect (the default source)
SOURCE=lidar ./show.sh          # back to the iPhone
./run.sh --source kinect        # without the projector window
```

- Mount it rigidly beside the projector, then press **Calibrate 3D** with the
  cello alone: calibrations made with the iPhone do not carry over.
- Its depth is its own infrared light: the projector does not disturb it,
  and it works in a dark hall. Range about 0.5-4.5 m.
- The depth camera sees less than the colour one: keep the cello away from
  the left and right edges of the image (no depth there).
- `test_kinect.py` checks the frame format offline; `--live` also reads the
  real Kinect for a few seconds.

### The cello's exact shape from depth (`cellomask/model3d.py`)

- **Depth fill:** the segmentation's mask is the seed; the cello's edge comes
  from the depth (it stops at the jump to the wall), and gaps such as the
  fingerboard slot fill in.
- **3D scan:** **Learn cello shape** (and **Calibrate 3D**) scans the cello
  alone and still. Every frame the scan is fitted to the live depth and
  the image outline, and the light takes the scan's exact outline at that
  pose: hands and the bow cannot change it. The depth fill takes over when
  it does not fit.
- **Which detection is the cello:** a close person (a red shirt) can also be
  detected as one. The pick follows the cello from frame to frame, uses the
  scan to find it again, and without a scan rejects anything not cello-sized
  in the depth.
- **/cloud** shows the live point cloud with the fitted scan in cyan.
  `test_model3d.py` checks all of this on a synthetic cello.

## Cello replacement (`cellomask/`)

Instance-segments the cello with a fine-tuned **YOLO26-seg** model and puts a
chosen image or video where the cello is, controlled from a web page.

```bash
./run.sh                       # built-in camera (installs first if needed)
./run.sh --source brio         # camera by name
```

Open <http://127.0.0.1:8000>. Pick or drop a replacement image/video on the
right; the **Mask** view shows what the model sees. `/output` is the clean
composited feed for the projector (click it to go fullscreen). Without a
camera setup, choose one of the sample photos under *Source → Test files*,
or upload a video of someone playing.

Fit modes: **Warp** rotates the image with the cello (image top = scroll),
**Fill** covers the cello's upright bounding box, **Window** pins the image
to the frame so the cello acts as a window onto it. *Feather* softens the
edge, *Grow* dilates/erodes the mask, *Black outside the cello* gives a
projection matte, *Responsive* trades mask stability for lag.

### Projection mapping onto the cello

```bash
./run.sh --source brio --projector     # projector window on the extended screen
```

The BRIO sits beside the projector; both stay fixed after calibrating.

1. Connect the projector by HDMI and set it to **extend**, not mirror
   (System Settings > Displays). `--projector` opens a fullscreen window on
   the last screen (`--projector 1` picks one; `--windowed` for testing).
2. Hold a flat, light board where the cello will be, facing projector and
   camera, and press **Calibrate** in the Projector section. The projector
   shows an ArUco marker grid; the camera finds it and the app fits the
   camera -> projector homography (`data/calibration.json`).
3. Put the cello there and choose **White** or **Outline**: the cello mask
   is projected as light. Fix any offset with **Shift X/Y** and **Scale**
   (a flat calibration is exact only on the board's plane; the cello's
   front sits a little off it).
4. **Content** projects the selected replacement (image, video or the live
   tuner) on the cello, black everywhere else. **Black** (or B in the
   projector window) is a blackout.

How it works: graphics are drawn in camera space inside the cello mask on
black, then warped into projector space with the calibration. The native
window shows them at the screen's refresh rate; `/output?view=projector` is
a browser fallback. `test_projector.py` runs the whole loop against a
simulated camera and projector (calibration within 1 px; projected light
covers the cello at IoU 0.92).

### Live tuner

Pick **Live tuner** (first tile in the gallery) to put a live pitch graph on
the cello, or the **Tuner** view / **Tuner only** link to see it alone. It
listens to the microphone (choose it under *Tuner*; macOS asks for microphone
permission the first time) and draws, like a tuner but over time, how many
cents each moment is off the nearest note. Vibrato is the wave in that trace,
and the dashed line is its running centre, so a vibrato that sits below
the note is visible. The header shows note, cents and Hz; the footer shows
vibrato rate and width, plus the waveform itself. Colour: green within 5
cents, amber within 15, red beyond.

Pitch is tracked by YIN at ~100 estimates/s over 55-1500 Hz (the cello's
range). The silence gate follows the room's noise floor. `test_tuner.py` checks
notes from C2 to A5 (within 2 cents) and vibrato rate/width on synthetic
cello tones. A4 reference, cents range and trace length are adjustable.

If `models/cello-seg.pt` does not exist the app falls back to zero-shot
**YOLOE** prompted with "cello" — it works, but misses more.

### Training data pipeline

The source dataset ([Roboflow cello-oglg8](https://universe.roboflow.com/talov-9bcpd/cello-oglg8),
CC BY 4.0, 200 images) has **bounding boxes only**, mostly catalogue photos.

```bash
.venv/bin/python -m cellomask.autolabel     # boxes -> SAM 2.1 masks -> data/seg/
.venv/bin/python -m cellomask.synth --clean # 600 stage-like composites (train only)
.venv/bin/python -m cellomask.train         # yolo26s-seg -> models/cello-seg.pt
```

1. **autolabel** prompts SAM 2.1 with each box and writes YOLO-seg polygons
   (85/15 train/val split). Check `data/seg/masks_preview.jpg`; list bad
   image stems in `data/seg/rejects.txt` and re-run.
2. **synth** pastes the masked cellos onto dark, spotlit backgrounds with the
   tilt of a played cello, arm/hand occluders (cut *out* of the mask so the
   replacement does not paint over the player's hands), a bow, exposure and
   white-balance jitter, noise and motion blur. Preview:
   `data/seg/synth_preview.jpg`.
3. **train** fine-tunes with mosaic, copy-paste and geometric augmentation.
4. **complete** (optional) finds cellos the original annotator skipped —
   several images show 2-3 cellos with only one box — and adds them via SAM.
   Run it with the trained model (`--model models/cello-seg.pt --dry-run`),
   check `data/seg/added_preview.jpg`, then without `--dry-run`, and retrain.
   YOLOE proposals were too noisy for this (merged racks, music stands).

**The biggest improvement will come from real footage of the actual setup**:
record a minute of playing with the stage camera, extract frames, label them
(SAM + a click, or Roboflow), add them to `data/seg/train`, retrain.
