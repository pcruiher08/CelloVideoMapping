# Show files (TouchDesigner and Max)

Snapshots of the show's TouchDesigner and Max files, kept here so they are
versioned with the cello app. They are worked on in place on the show Mac
(Angel's MacBook Pro); copy them back here after changes.

| File here | On the show Mac | What it is |
|---|---|---|
| `touchdesigner/Prueba TD Visuales GPT apagon.toe` | `~/Desktop/Proyecto Integrador/TD/` | The visuals. Sends `visuales_cello` over NDI to the cello app; talks to Ableton Live through TDAbleton; gets the cello app's OSC on port 9000 and Max's on 8400. |
| `max/OSC_Control_CelloP/` | `~/Desktop/Proyecto Integrador/OSC_Control_CelloP/` | The Max project: `Interfaz_Cello_Performance.maxpat` analyses the cello's sound (amplitude, bands, pitch, vibrato) and sends it to TouchDesigner over OSC (`udpsend 127.0.0.1 8400`); `Recibidor.maxpat`. |
| `max/Cello_FX_Rig/` | `~/Documents/Codex/2026-11-22/project-cello-fx-rig-max-msp/CELLO_FX_RIG/` | An effects rig (whammy, delay, sustain/freeze, reverb), controlled by MIDI CC. |

Snapshot of 2026-11-23 (the `.toe` as saved at 21:41).
