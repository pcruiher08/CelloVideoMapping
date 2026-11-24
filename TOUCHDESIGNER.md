# Cello video mapping with TouchDesigner

The app tracks the cello and the bow with a **Kinect v2**, projects
TouchDesigner's visuals onto the cello's front with a projector, and sends
TouchDesigner everything it measures over **OSC**.

## Install on the TouchDesigner Mac

1. **Download** the latest `cellotracking-*.zip` from this repository's
   [Releases](https://github.com/pcruiher08/CelloVideoMapping/releases) page.
2. **Install Apple's developer tools and Homebrew** (once). The Kinect driver
   is built on the Mac from source:
   ```bash
   xcode-select --install
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
3. **Unzip and start:**
   ```bash
   cd ~/Downloads && unzip cellotracking-*.zip && cd cellotracking-*/ && bash show.sh
   ```
   The first start installs everything (Python packages, about 1 GB, plus the
   Kinect driver). It takes several minutes and needs internet. Later starts
   take about 20 s.
4. **Connect the hardware:**
   - **Kinect v2:** plugged directly into a USB 3 port on the Mac, not through
     a hub, with its power adapter on. Mount it rigidly next to the projector.
   - **Projector:** over HDMI, set to **extend** (not mirror) at its native
     resolution (System Settings › Displays). Pick it under **Screen** in the
     web page's Projector section.
5. **Open the web page:** http://127.0.0.1:8000 on that Mac, or the address
   `show.sh` prints, from a phone or tablet on the same network.
6. **Calibrate** if the Kinect, projector or room differ from where the zip was
   made. With the cello alone and still, in a dim room, press
   **Calibrate 3D** (about 30 s). It also rescans the cello. Then press
   **Fit the light's edge** if light spills past the cello's edge.

Keys in the projector window: **f** covers or uncovers the screen,
**b** blacks out, **q** quits.

## TouchDesigner → the cello (video in)

- **NDI:** add an **NDI Out TOP** after the final visual, then press **Find
  NDI / Syphon senders** in the web page and pick it in the gallery. The app
  remembers it after that. Works on the same Mac or from another computer (use
  a wired network).
- **Syphon (same Mac only):** a **Syphon Spout Out TOP** works the same way.
- The zip starts with a test grid on the cello until you pick a sender.
- **Format:** a portrait texture of about 1:2.4 fits the cello best, at
  **about 800 x 1920 or larger** (the projector shows the whole cello about
  1650 pixels tall; the app uses up to 2048 pixels of the image's long side).
  The image goes straight to projector pixels in one warp, so its detail
  reaches the cello. It follows the cello in 3D: it moves, leans and turns
  with it, in perspective.
- **Lit area:** only the cello's front face gets light (not the neck or the
  ribs), with a clean, fixed outline. A hand or the bow in front of the cello
  is painted over, so the shape doesn't get bitten.

## The cello → TouchDesigner (OSC out)

In TouchDesigner add an **OSC In CHOP** (numbers) or **OSC In DAT** (the note
name) on port **9000**. The target is set in the web page (TouchDesigner
section, **OSC to**): `127.0.0.1` when TouchDesigner runs on the same Mac. All
values are floats, sent every tracked frame (about 20–30 per second).

### Cello

| Address | Value |
|---|---|
| `/cello/present` | 1 when the cello is tracked, else 0 |
| `/cello/x`, `/cello/y` | centre in the camera image, 0–1 (0 = left / top) |
| `/cello/angle` | tilt in the image, degrees from upright (+ = top to the right) |
| `/cello/size` | length in the image, 0–1 of the image height |
| `/cello/distance` | metres from the camera |
| `/cello/lean` | degrees, + = top leaning away from the camera |
| `/cello/turn` | degrees, + = right side turned away |
| `/cello/covered` | 0–1 of the cello hidden (hands, bow) |

### Bow (no markers: found in the Kinect's depth)

| Address | Value |
|---|---|
| `/bow/present` | 1 when the bow is found, else 0 |
| `/bow/angle` | degrees to the strings in the cello's plane: 0 = square to them, + = tip towards the scroll |
| `/bow/tilt` | degrees out of the cello's plane (leans towards the outer or inner strings) |
| `/bow/speed` | m/s along the bow: + = down-bow, − = up-bow, 0 = still (from how the bow slides through the strings) |
| `/bow/contact` | where on the bow the strings are: 0 = at the frog, 1 = at the tip (not sent while lifted) |
| `/bow/on_strings` | 1 while the bow is on the strings, 0 when lifted off them (speed then reads 0) |
| `/bow/along` | metres along the strings where the bow crosses, from the cello's centre (+ = towards the scroll; sul ponticello to sul tasto) |
| `/bow/tip`, `/bow/frog` | x y z in metres (the bow as a wand): origin = the cello's centre, x right, y up, z towards the camera |
| `/bow/dir` | x y z, unit vector from frog to tip |
| `/bow/tip_velocity` | x y z in m/s |
| `/bow/length` | metres of bow seen (shorter than the bow: the hand hides the frog end) |

The bow is found on about 97–100% of frames while bowing and about 75% while
waving it in the air. Very fast swings blur and drop out for a moment. It is
found in front of a black backdrop too (which gives the Kinect no depth), and
a bow resting across the strings stays found. It is followed only above the
lower end of the cello's body (below it, the floor and stands are in the way).
The bow tracker runs in its own process, so it does not slow the projection.

### Sound (when the tuner runs: pick it in the gallery, or open its panel)

| Address | Value |
|---|---|
| `/tuner/freq` | Hz of the note played (0 when silent) |
| `/tuner/note` | the note's name, e.g. `A3` (a string: use an OSC In DAT) |
| `/tuner/cents` | −50 to +50, how far off the note |
| `/tuner/level` | dB |
| `/vibrato/rate` | Hz of the vibrato (0 without vibrato) |
| `/vibrato/extent` | cents of the vibrato |

### Bow painting

| Address | Value |
|---|---|
| `/paint/active` | 1 while painting, else 0 |
| `/paint/hold` | 0–1, how far a start or stop gesture has been held (0 when none) |
| `/paint/brush` | u v, where the brush is on the cello (0–1: u left to right, v scroll to endpin); only while painting with the bow found |

## Painting on the cello with the bow

The app can paint on the cello itself: the bow's tip is a brush that lays
thick, streaky ribbons of paint in blues, violets and magentas. The paint
piles up and stays where it was put on the wood as the cello moves, and it
drifts slowly.

- **Start:** hold the bow **upright beside the cello** (along the strings,
  tip up) for 2 seconds.
- **Paint:** play or draw. Faster strokes paint wider ribbons; down-bows are
  warmer, up-bows cooler, and the colours drift over time.
- **Stop:** hold the bow **pointing down beside the cello** for 2 seconds.
  The painting fades out over about 3 seconds.
- Hold the bow beside the cello, not in front of the strings, and keep the tip
  above the floor: the bow tracker ignores both places. Normal playing never
  triggers a gesture.
- **By default the paint goes behind TouchDesigner's graphics:** it shows
  where TouchDesigner's picture is black, and its bright graphics cover it.
  Untick **Paint behind TouchDesigner's graphics** to put it on top.
- The web page (TouchDesigner section) has **Start**, **Stop** and **Clear**
  buttons for rehearsal, the gesture's progress, and a switch to turn the
  painting off.

## Hand signs switch effects in Max

With the fingering hand beside the cello's neck, **in the white gloves**:

- **✌️ peace**, held about 1 s, switches the **ping-pong delay** on or off.
- **👍 thumbs up**, held about 1 s, switches the **overdrive** on or off.
- Lower the hand before the same sign switches it back.

The app reads the glove's outline in the Kinect's full-resolution image, so
bare hands are not seen. It sends `/fx/pingpong` and `/fx/overdrive` (1 on,
0 off) to Max on `127.0.0.1:7400`, on every change and every 2 s. The web page
(TouchDesigner section) shows the sign it sees and has buttons to switch the
effects by hand.

In Max, `Interfaz_Cello_Performance.maxpat` (in this repository's `show/max/`)
has the effects: the cello from input 1 through an overdrive and a ping-pong
delay, out on outputs 2–5 (the console sends them to the speakers), switched
by `udpreceive 7400` or by its two toggles.

## What the app does on its own

- **3D tracking of the cello:** a 3D scan of the cello is fitted to the
  Kinect's depth every frame. That gives position, lean and turn, so the
  picture lands on the cello in perspective wherever it is.
- **Smooth light:** the projector image moves at 60 Hz, using a motion
  forecast between tracked frames, which covers most of the system's delay of
  about 0.1 s. Small tracking noise is smoothed out when the cello is still.
- **Robust to the player:** hands and the bow over the cello don't change its
  shape. A person close to the camera isn't mistaken for the cello. Brief
  tracking dropouts keep the last shape for half a second.
- **Edge control** (Projector section): **Edge inset** pulls the light in from
  the rim (3 mm by default). **Motion inset** pulls it in further while the
  cello moves fast, so it doesn't spill. **Fit the light's edge** corrects the
  outline point by point.
- **Live tuner** graph on the cello (gallery), for rehearsal.

## Troubleshooting

- **The light freezes for a few seconds:** the Kinect's USB connection dropped.
  It reconnects by itself; plug it directly into the Mac.
- **The Mac locked during the show:** `show.sh` keeps it awake while it runs
  (macOS `caffeinate`); start the show with it, not `run.sh`.
- **Calibrate 3D is rejected ("lens centre far outside the image"):** what is
  lit is too flat (the cello and one board behind it). Add a board at another
  depth or angle and calibrate again: the app pools the day's captures, which
  usually solves it.
- **The light drifts off the cello:** if boards, stands or the backdrop were
  moved or removed but the Kinect and projector were not, press **Room
  changed** (Projector section). The app took the moved surroundings for the
  Kinect moving; this resets that, with no calibration. If the Kinect or the
  projector really moved, press **Calibrate 3D**.
- **Nothing on the projector:** the projector must be set to extend. Pick the
  right screen under **Screen**, or press **f** in the projector window.
- **The cello is dark, or shows a "waiting for …" card:** the app is set to a
  sender that isn't sending. The card is nearly black on the cello. The web
  page's TouchDesigner section says **Waiting for …** instead of
  **Receiving …**. Check the NDI Out TOP is active, press **Find NDI / Syphon
  senders**, and pick the sender in the gallery.
