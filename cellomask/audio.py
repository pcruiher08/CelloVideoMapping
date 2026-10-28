"""Microphone pitch tracking for the live tuner graph.

A PortAudio input stream fills a ring buffer; an analysis thread runs YIN
every 10 ms on the newest 64 ms of audio, giving ~100 pitch estimates per
second — enough to resolve vibrato (5-7 Hz on a cello) as a smooth wave.

Range is 55-1500 Hz: the cello's open C is 65.4 Hz and thumb-position notes
rarely go above ~1.3 kHz. Audio is analysed at 16 kHz; PortAudio/CoreAudio
does the resampling from the device rate.
"""

import math
import threading
import time
from collections import deque

import numpy as np

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def yin(x, sr, fmin=55.0, fmax=1500.0, threshold=0.15):
    """Fundamental frequency of `x` by YIN (de Cheveigne & Kawahara 2002).

    Returns (f0 or None, aperiodicity 0..1 — lower is more periodic). The
    difference function is computed through FFT correlation, so a 1024-sample
    frame costs well under a millisecond."""
    x = np.asarray(x, np.float64)
    x = x - x.mean()
    n = len(x)
    tau_max = min(int(sr / fmin), n // 2)
    tau_min = max(2, int(sr / fmax))
    w = n - tau_max                                   # integration window
    size = 1 << int(math.ceil(math.log2(n + w)))
    r = np.fft.irfft(np.fft.rfft(x, size) * np.conj(np.fft.rfft(x[:w], size)),
                     size)[:tau_max + 1]              # r[tau] = sum x[j] x[j+tau]
    cs = np.concatenate([[0.0], np.cumsum(x * x)])
    taus = np.arange(tau_max + 1)
    energy_tau = cs[taus + w] - cs[taus]
    d = cs[w] + energy_tau - 2 * r
    d[0] = 0.0
    cmnd = np.ones_like(d)
    running = np.cumsum(d[1:])
    cmnd[1:] = d[1:] * taus[1:] / np.where(running > 0, running, 1)

    seg = cmnd[tau_min:tau_max]
    below = np.flatnonzero(seg < threshold)
    if len(below):
        tau = tau_min + below[0]
        while tau + 1 < tau_max and cmnd[tau + 1] < cmnd[tau]:   # walk to the dip
            tau += 1
    else:
        tau = tau_min + int(np.argmin(seg))
    ap = float(cmnd[tau])
    if 1 <= tau < tau_max:                            # parabolic refinement
        a, b, c = cmnd[tau - 1], cmnd[tau], cmnd[tau + 1]
        den = a - 2 * b + c
        shift = 0.5 * (a - c) / den if den > 1e-12 else 0.0
        tau = tau + float(np.clip(shift, -1, 1))
    if ap > 0.5:
        return None, ap
    return sr / tau, ap


def freq_to_note(f, a4=440.0):
    """(note name with octave, cents off that note, midi number)."""
    midi_f = 69 + 12 * math.log2(f / a4)
    midi = int(round(midi_f))
    return f"{NOTE_NAMES[midi % 12]}{midi // 12 - 1}", 100 * (midi_f - midi), midi


def analyse_vibrato(t, midi_f, min_rate=3.5, max_rate=9.0, window=0.0):
    """Vibrato rate (Hz), extent (cents, half peak-to-peak) and how periodic
    it is (0..1), from pitch samples of a single held note.

    The pitch curve is detrended (a slow glide is not vibrato), then the
    autocorrelation peak inside the vibrato band gives the rate.

    Each pitch estimate averages `window` seconds of audio, which flattens
    the vibrato like a boxcar filter: by sinc(rate * window), ~10% at 5.5 Hz
    with a 46 ms window. The extent is divided by that factor."""
    if len(t) < 30:
        return None
    dt = np.median(np.diff(t))
    grid = np.arange(t[0], t[-1], dt)
    if len(grid) < 30:
        return None
    cents = np.interp(grid, t, 100 * midi_f)
    k = np.arange(len(grid))
    cents = cents - np.polyval(np.polyfit(k, cents, 1), k)
    if cents.std() < 1.0:                              # dead straight: no vibrato
        return {"rate": 0.0, "extent": 0.0, "strength": 0.0}
    ac = np.correlate(cents, cents, "full")[len(cents) - 1:]
    ac /= ac[0]
    lo, hi = int(1 / (max_rate * dt)), int(math.ceil(1 / (min_rate * dt)))
    hi = min(hi, len(ac) - 2)
    if hi <= lo:
        return None
    peak = max(1, lo + int(np.argmax(ac[lo:hi + 1])))
    lag = float(peak)
    if peak < len(ac) - 1:                             # parabolic peak refinement
        a, b, c = ac[peak - 1], ac[peak], ac[peak + 1]
        den = a - 2 * b + c
        # only a true peak (den < 0) can be refined, and by at most half a
        # sample; on irregular audio an unclamped shift ran to negative lags
        if den < -1e-12:
            lag += float(np.clip(0.5 * (a - c) / den, -0.5, 0.5))
    rate = 1 / (lag * dt)
    extent = (np.percentile(cents, 95) - np.percentile(cents, 5)) / 2
    x = math.pi * rate * window
    if x > 1e-6:
        extent /= max(0.5, math.sin(x) / x)
    return {"rate": rate, "extent": float(extent),
            "strength": float(max(0.0, ac[peak]))}


class PitchTracker:
    """Live pitch + vibrato from a microphone (or fed samples, for tests)."""

    def __init__(self, sr=16000, frame=1024, hop=160, history=12.0, a4=440.0):
        self.sr = sr
        self.frame = frame
        self.hop = hop
        self.a4 = a4
        # silence gate, 8 dB above the room's noise floor (a quiet room
        # measured -43 dB on a MacBook mic, so a fixed -50 dB let hum in).
        # The floor drops instantly to any quieter level but rises only
        # 0.3 dB/s, so a long held note does not become "the floor"; and
        # anything louder than -38 dB always counts as sound.
        self.floor_db = None
        self.gate_db = -50.0
        self.buf = np.zeros(sr * 2, np.float32)
        self.write = 0                        # total samples written
        self.lock = threading.Lock()
        n = int(history * sr / hop)
        self.hist = deque(maxlen=n)           # (t, f0 or nan, level_db)
        self.wave = np.zeros(frame, np.float32)
        self.stream = None
        self.device = None
        self.error = None
        self.running = False
        self.vibrato = None
        self._vib_t = 0.0
        self._thread = None

    # --- input -------------------------------------------------------------

    def feed(self, samples):
        samples = np.asarray(samples, np.float32).ravel()
        with self.lock:
            n = len(self.buf)
            idx = (self.write + np.arange(len(samples))) % n
            self.buf[idx] = samples
            self.write += len(samples)

    def _callback(self, indata, frames, time_info, status):
        self.feed(indata[:, 0])

    def start(self, device=None):
        """Open the microphone. `device` is a sounddevice index or name
        substring; None means the system default input."""
        import sounddevice as sd
        self.stop_stream()
        try:
            self.stream = sd.InputStream(device=device, channels=1,
                                         samplerate=self.sr, blocksize=self.hop,
                                         dtype="float32", callback=self._callback)
            self.stream.start()
            info = sd.query_devices(self.stream.device)
            self.device = info["name"]
            self.error = None
        except Exception as e:                # no mic, permission, bad device
            self.stream = None
            self.device = None
            self.error = f"microphone: {e}"
        if not self.running:
            self.running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop_stream(self):
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

    @staticmethod
    def input_devices():
        import sounddevice as sd
        try:
            default = sd.default.device[0]
            return [{"index": i, "name": d["name"], "default": i == default}
                    for i, d in enumerate(sd.query_devices())
                    if d["max_input_channels"] > 0]
        except Exception:
            return []

    # --- analysis ----------------------------------------------------------

    def latest(self, n):
        with self.lock:
            if self.write < n:
                return None
            idx = (self.write - n + np.arange(n)) % len(self.buf)
            return self.buf[idx].copy()

    def step(self, t=None):
        """Analyse the newest frame once. Called by the thread every hop, or
        directly by tests after feed()."""
        x = self.latest(self.frame)
        if x is None:
            return
        t = time.time() if t is None else t
        rms = float(np.sqrt(np.mean(x * x)))
        level = 20 * math.log10(rms + 1e-9)
        rise = 0.3 * self.hop / self.sr
        if self.floor_db is None:
            self.floor_db = level
        self.floor_db = min(level, self.floor_db + rise)
        self.gate_db = min(-38.0, max(-65.0, self.floor_db + 8.0))
        f0 = None
        if level > self.gate_db:
            f0, _ = yin(x, self.sr)
        self.hist.append((t, f0 if f0 else float("nan"), level))
        self.wave = x
        if t - self._vib_t > 0.1:             # vibrato analysis at 10 Hz
            self._vib_t = t
            self.vibrato = self._vibrato()

    def _loop(self):
        last = 0
        while self.running:
            if self.write - last >= self.hop:
                last = self.write
                try:
                    self.step()
                except Exception as e:        # one bad frame must not stop the tuner
                    self.error = f"analysis: {e!r}"
                    print(f"tuner: {self.error}")
            else:
                time.sleep(0.003)

    def _held_note(self, seconds):
        """Pitch samples of the note being held now: the trailing run of
        voiced samples within `seconds`, cut at the last jump > 70 cents."""
        h = list(self.hist)
        if not h:
            return None, None
        t_now = h[-1][0]
        ts, ms = [], []
        for t, f, _ in reversed(h):
            if t_now - t > seconds or not (f == f):   # f != f -> nan -> unvoiced
                break
            m = 69 + 12 * math.log2(f / self.a4)
            if ms and abs(m - ms[-1]) > 0.7:
                break
            ts.append(t)
            ms.append(m)
        if not ts:
            return None, None
        return np.array(ts[::-1]), np.array(ms[::-1])

    def _vibrato(self):
        t, m = self._held_note(1.2)
        if t is None or t[-1] - t[0] < 0.5:
            return None
        # YIN integrates over frame - tau_max samples (~46 ms at 16 kHz)
        window = (self.frame - int(self.sr / 55.0)) / self.sr
        v = analyse_vibrato(t, m, window=window)
        if v is None:
            return None
        v["present"] = v["extent"] > 6 and v["strength"] > 0.3 and v["rate"] > 0
        return v

    def snapshot(self):
        """Everything the renderer and the UI need, in one consistent copy."""
        h = list(self.hist)
        t, m = self._held_note(0.5)
        note = cents = freq = None
        if t is not None and len(m) >= 5:
            centre = float(np.median(m))
            freq = self.a4 * 2 ** ((centre - 69) / 12)
            note, cents, _ = freq_to_note(freq, self.a4)
        level = h[-1][2] if h else -120.0
        return {"hist": h, "note": note, "cents": cents, "freq": freq,
                "vibrato": self.vibrato, "wave": self.wave, "level": level,
                "gate": self.gate_db,
                "a4": self.a4, "device": self.device, "error": self.error,
                "sr": self.sr}
