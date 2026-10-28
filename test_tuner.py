"""Synthetic check of the tuner: cello-like tones with known pitch and
vibrato are fed to PitchTracker, and the detected note, cents and vibrato
rate/extent are compared with the truth.

    .venv/bin/python test_tuner.py
"""

import math

import numpy as np

from cellomask.audio import PitchTracker, freq_to_note

SR = 16000


def cello_tone(f0, seconds, vib_rate=0.0, vib_cents=0.0, cents_off=0.0,
               noise=0.01, seed=0):
    """Sawtooth-ish tone (cellos are harmonic-rich; the fundamental of the
    low strings is weaker than the 2nd/3rd harmonics) with sinusoidal
    vibrato of +-vib_cents at vib_rate Hz."""
    t = np.arange(int(seconds * SR)) / SR
    cents = cents_off + vib_cents * np.sin(2 * np.pi * vib_rate * t)
    f = f0 * 2 ** (cents / 1200)
    phase = 2 * np.pi * np.cumsum(f) / SR
    amps = [0.6, 1.0, 0.8, 0.5, 0.35, 0.25, 0.15, 0.1]
    x = sum(a * np.sin((k + 1) * phase) for k, a in enumerate(amps) if (k + 1) * f0 < SR / 2.2)
    x = 0.2 * x / np.abs(x).max()
    return (x + noise * np.random.default_rng(seed).normal(size=len(t))).astype(np.float32)


def run(signal, step_every=160):
    tr = PitchTracker(sr=SR)
    for i in range(0, len(signal), step_every):
        tr.feed(signal[i:i + step_every])
        tr.step(t=(i + step_every) / SR)
    return tr


def check(name, ok, detail):
    print(f"{'PASS' if ok else 'FAIL'}  {name:38s} {detail}")
    return ok


def main():
    ok = True
    # open strings and a high thumb-position note, steady
    for f0, cents_off in ((65.41, 0), (98.0, -12), (146.83, 7), (220.0, 0), (880.0, 20)):
        tr = run(cello_tone(f0, 1.5, cents_off=cents_off))
        s = tr.snapshot()
        exp_note, _, _ = freq_to_note(f0)
        err = abs(s["cents"] - cents_off) if s["cents"] is not None else 999
        v = s["vibrato"]
        ok &= check(f"steady {exp_note} {cents_off:+.0f}c",
                    s["note"] == exp_note and err < 3 and not (v and v["present"]),
                    f"-> {s['note']} {s['cents']:+.1f}c (err {err:.1f}c), "
                    f"vibrato {'yes' if v and v['present'] else 'no'}")

    # vibrato: typical cello 5-6.5 Hz, +-10..30 cents
    for f0, rate, extent in ((110.0, 5.5, 20), (220.0, 6.5, 12), (329.63, 4.8, 30)):
        tr = run(cello_tone(f0, 2.0, vib_rate=rate, vib_cents=extent))
        s = tr.snapshot()
        v = s["vibrato"] or {}
        ok &= check(f"vibrato {f0:.0f}Hz {rate}Hz +-{extent}c",
                    v.get("present") and abs(v["rate"] - rate) < 0.4
                    and abs(v["extent"] - extent) < 0.25 * extent
                    and s["note"] == freq_to_note(f0)[0],
                    f"-> {s['note']} rate {v.get('rate', 0):.2f}Hz extent "
                    f"+-{v.get('extent', 0):.1f}c strength {v.get('strength', 0):.2f}")

    # silence is not a note
    tr = run(np.random.default_rng(1).normal(0, 0.0005, SR).astype(np.float32))
    s = tr.snapshot()
    ok &= check("silence", s["note"] is None, f"-> note {s['note']}")

    print("ALL TESTS PASSED" if ok else "SOME TESTS FAILED")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
