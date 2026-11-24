# CELLO FX RIG — Max 9

Open `Cello_FX_Rig.maxpat` in Max 9 on macOS. This is a single flat patch: all processing objects and patch cords are in the main patcher; there are no `p`, `bpatcher`, or abstraction instances. Choose your interface and sample rate in **Options → Audio Status**. Start at 48 kHz with a 64 or 128 sample vector if the interface supports it. The patch starts with a low master level and includes a low-level 220 Hz test oscillator.

## Test the full signal path

1. Click **DSP** (top left).
2. Click **TEST TONE**. The 220 Hz tone is mixed into the input path at low level.
3. Confirm the **OUTPUT METER** responds. Turn TEST TONE off before connecting or playing the cello.
4. Select the interface input and output in Audio Status. Connect a cello pickup/preamp to input 1, raise input gain gradually, and monitor through the interface.

The flat signal order is **Input/Test → Whammy → Delay → Sustain → Reverb → master clip/gain → meter and outputs 1–2**. The Sustain recorder is fed by the Delay output so it can record the delay tail. The current chain is mono, with the same output signal routed to both hardware output channels.

## Controls

- **Whammy:** expression dial 0–127 maps from the low to high semitone fields (default −12 to +12); wet 0–1. `pitchshift~` is the native real-time shifter.
- **Delay:** time 20–8000 ms, wet 0–1, feedback clipped to 0–0.9, low-pass damping, high-pass filter, and signal clamp.
- **Sustain:** click Capture to record the next five seconds of delay output, then enable Freeze to play the recorded buffer in a loop. Freeze has a 400 ms fade. Wet control blends the loop with live delay output.
- **Reverb:** two short feedback delay lines with damping, size/feedback, wet control and output clamp.
- **Master:** low initial level (0.05), hard clip safety, output meter, stereo hardware outputs.
- **MIDI:** CC 21 Whammy, CC 22 delay feedback, CC 23 delay time, CC 24 reverb mix, CC 7 master level.

## Verified and remaining work

Max 9.1.5 was used to open the flat patch. The patch JSON and patch cord endpoints were checked, and the direct graph from both ADC and test oscillator reaches the output and meter. Native `pitchshift~`, `tapin~`, `tapout~`, `svf~`, `onepole~`, `buffer~`, `record~`, and `groove~` availability was checked against installed Max help/reference files. The 220 Hz live DSP meter check is still pending; do not treat software parsing as proof of audio execution. MIDI mappings are simple CC ingress mappings and have not been tested with hardware.

Still incomplete: OSC decoding/routing, individual effect bypass switches, adjustable sustain attack/release, true stereo processing and ping-pong delay, early reflection controls, stereo width, full routing reorder, separate input meter/clip indicator, and a high-quality room reverb. The reverb is a compact delay network, not a studio reverb. Whammy latency/artifacts and sustain loop periodicity need listening tests.
