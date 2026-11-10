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

- **Same Mac:** add a **Syphon Spout Out TOP** named `visuales_cello` after the
  final visual. The zip comes set to use it.
- **Another computer:** add an **NDI Out TOP**, then press **Find NDI / Syphon
  senders** in the web page and pick it in the gallery. Use a wired network.
- **Format:** a portrait texture of about 1:2.4 fits the cello best. The image
  follows the cello in 3D: it moves, leans and turns with it, in perspective.
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
| `/bow/speed` | m/s along the bow: + = down-bow, − = up-bow, 0 = still |
| `/bow/along` | metres along the strings where the bow crosses, from the cello's centre (+ = towards the scroll; sul ponticello to sul tasto) |
| `/bow/tip`, `/bow/frog` | x y z in metres (the bow as a wand): origin = the cello's centre, x right, y up, z towards the camera |
| `/bow/dir` | x y z, unit vector from frog to tip |
| `/bow/tip_velocity` | x y z in m/s |
| `/bow/length` | metres of bow seen (shorter than the bow: the hand hides the frog end) |

The bow is found on about 97–100% of frames while bowing and about 75% while
waving it in the air. Very fast swings blur and drop out for a moment. A bow
lying still for many seconds is taken as part of the room until it moves.

### Sound (when the tuner runs: pick it in the gallery, or open its panel)

| Address | Value |
|---|---|
| `/tuner/freq` | Hz of the note played (0 when silent) |
| `/tuner/note` | the note's name, e.g. `A3` (a string: use an OSC In DAT) |
| `/tuner/cents` | −50 to +50, how far off the note |
| `/tuner/level` | dB |
| `/vibrato/rate` | Hz of the vibrato (0 without vibrato) |
| `/vibrato/extent` | cents of the vibrato |

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
- **The light is offset from the cello:** the Kinect or projector moved. Press
  **Calibrate 3D**.
- **Nothing on the projector:** the projector must be set to extend. Pick the
  right screen under **Screen**, or press **f** in the projector window.
- **The picture is a "waiting" card:** TouchDesigner isn't sending yet. Check
  the Syphon Spout Out TOP's name, then press **Find NDI / Syphon senders**.
