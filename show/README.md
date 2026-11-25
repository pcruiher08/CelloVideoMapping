# Show files (TouchDesigner, Max and Ableton Live)

Snapshots of the show's TouchDesigner and Max files, kept here so they are
versioned with the cello app. They are worked on in place on the show Mac
(Angel's MacBook Pro); copy them back here after changes.

| File here | On the show Mac | What it is |
|---|---|---|
| `touchdesigner/Visuales Generativos - Lo que la luz escucha - Angel Bustillos.toe` | `~/Desktop/Proyecto Integrador/TD/` | The visuals used in the show (`Prueba TD Visuales GPT apagon.toe` is the earlier version). Sends `visuales_cello` over NDI to the cello app; talks to Ableton Live through TDAbleton; gets the cello app's OSC on port 9000 and Max's on 8400. |
| `max/OSC_Control_CelloP/` | `~/Desktop/Proyecto Integrador/OSC_Control_CelloP/` | The Max project: `Interfaz_Cello_Performance.maxpat` analyses the cello's sound (amplitude, bands, pitch, vibrato) and sends it to TouchDesigner over OSC (`udpsend 127.0.0.1 8400`); `Recibidor.maxpat`. |
| `live/Lo que la luz escucha Project/Live Performance Session - Lo que la luz escucha - Angel Bustillos.als` | `~/Desktop/Proyecto Integrador/tda prueba 2 Project/` | The Ableton Live 12 set, with the ping-pong delay and overdrive MIDI-mapped to CC 20 / 21 from "from Max 1" (Min Off, Max On). Open Max before Live. |
| `max/Cello_FX_Rig/` | `~/Documents/Codex/2026-11-22/project-cello-fx-rig-max-msp/CELLO_FX_RIG/` | An effects rig (whammy, delay, sustain/freeze, reverb), controlled by MIDI CC. |

Snapshot of 2026-11-24 (the `.toe`, `.maxpat` and `.als` as saved at 18:38, after the full stage test).
The release zip carries this folder as `show/`.
