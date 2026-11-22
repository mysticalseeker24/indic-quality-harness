"""Audio I/O and signal statistics (numpy + stdlib ``wave``; ffmpeg only for non-WAV input).

Nothing here calls a model. Frame-level measurements use 20 ms frames:
  * level in dBFS, to find silences relative to this clip's own speech level
  * spectral flatness, to find stretches of broadband noise (flat spectrum, speech-loud)
  * clipping: samples at full scale in runs of 3 or more
"""

from __future__ import annotations

import io
import shutil
import subprocess
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

FRAME_S = 0.02


def load_audio(path: str | Path) -> tuple[np.ndarray, int]:
    """Return mono float32 samples in [-1, 1] and the sample rate."""
    path = Path(path)
    try:
        with wave.open(str(path)) as w:
            return _from_wave(w)
    except (wave.Error, EOFError):
        pass
    if not shutil.which("ffmpeg"):
        raise RuntimeError(f"{path.name}: not a PCM WAV file and ffmpeg is not installed")
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "wav", "-acodec", "pcm_s16le", "-ac", "1", "-"],
        capture_output=True,
        check=True,
    )
    with wave.open(io.BytesIO(proc.stdout)) as w:
        return _from_wave(w)


def load_audio_bytes(data: bytes) -> tuple[np.ndarray, int]:
    with wave.open(io.BytesIO(data)) as w:
        return _from_wave(w)


def _from_wave(w: wave.Wave_read) -> tuple[np.ndarray, int]:
    sr, ch, width, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
    raw = w.readframes(n)
    if width == 2:
        x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 1:
        x = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif width == 4:
        x = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise wave.Error(f"unsupported sample width {width}")
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, sr


def wav_bytes(x: np.ndarray, sr: int) -> bytes:
    pcm = (np.clip(x, -1.0, 1.0) * 32767.0).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def write_wav(path: str | Path, x: np.ndarray, sr: int) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(wav_bytes(x, sr))


def frames(x: np.ndarray, sr: int) -> np.ndarray:
    hop = max(1, int(sr * FRAME_S))
    n = len(x) // hop
    if n == 0:
        return np.zeros((1, max(1, len(x))), dtype=np.float32) if len(x) == 0 else x[None, :]
    return x[: n * hop].reshape(n, hop)


def frame_db(x: np.ndarray, sr: int) -> np.ndarray:
    f = frames(x, sr)
    rms = np.sqrt(np.mean(f.astype(np.float64) ** 2, axis=1) + 1e-12)
    return 20 * np.log10(rms + 1e-12)


def frame_flatness(x: np.ndarray, sr: int) -> np.ndarray:
    f = frames(x, sr) * np.hanning(frames(x, sr).shape[1])
    mag = np.abs(np.fft.rfft(f, axis=1)) + 1e-10
    return np.exp(np.mean(np.log(mag), axis=1)) / np.mean(mag, axis=1)


def runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """[start, end) index runs where mask is True."""
    out, start = [], None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        elif not v and start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(mask)))
    return out


@dataclass
class AudioStats:
    duration_s: float
    speech_level_db: float
    noise_floor_db: float
    active_s: float
    lead_silence_s: float
    trail_silence_s: float
    silences: list[tuple[float, float]] = field(default_factory=list)  # internal, >= 0.3 s
    noise_runs: list[tuple[float, float]] = field(default_factory=list)
    clip_ratio: float = 0.0
    clip_regions: list[tuple[float, float]] = field(default_factory=list)

    @property
    def longest_silence(self) -> tuple[float, float] | None:
        return max(self.silences, key=lambda s: s[1] - s[0], default=None)

    def summary(self) -> dict:
        ls = self.longest_silence
        return {
            "duration_s": round(self.duration_s, 3),
            "active_speech_s": round(self.active_s, 3),
            "lead_silence_s": round(self.lead_silence_s, 3),
            "trail_silence_s": round(self.trail_silence_s, 3),
            "longest_internal_silence_s": round(ls[1] - ls[0], 3) if ls else 0.0,
            "clip_ratio": round(self.clip_ratio, 5),
            "noise_floor_db": round(self.noise_floor_db, 1),
            "speech_level_db": round(self.speech_level_db, 1),
            "noise_s": round(sum(b - a for a, b in self.noise_runs), 3),
        }


def analyse(x: np.ndarray, sr: int) -> AudioStats:
    db = frame_db(x, sr)
    dur = len(x) / sr
    if len(x) == 0:
        return AudioStats(0.0, -120.0, -120.0, 0.0, 0.0, 0.0)
    speech_level = float(np.percentile(db, 90))
    noise_floor = float(np.percentile(db, 10))
    thr = max(-60.0, speech_level - 30.0)
    silent = db < thr
    sil_runs = runs(silent)
    lead = sil_runs[0][1] * FRAME_S if sil_runs and sil_runs[0][0] == 0 else 0.0
    trail = (len(db) - sil_runs[-1][0]) * FRAME_S if sil_runs and sil_runs[-1][1] == len(db) else 0.0
    internal = [(a * FRAME_S, b * FRAME_S) for a, b in sil_runs if a > 0 and b < len(db) and (b - a) * FRAME_S >= 0.3]
    active = float((~silent).sum()) * FRAME_S
    # broadband noise: flat spectrum at speech-like loudness, sustained >= 0.3 s
    flat = frame_flatness(x, sr)
    noisy = (flat > 0.45) & (db > speech_level - 15.0)
    noise_runs = [(a * FRAME_S, b * FRAME_S) for a, b in runs(noisy) if (b - a) * FRAME_S >= 0.3]
    # clipping: |x| >= 0.98 for 3+ consecutive samples
    hot = np.abs(x) >= 0.98
    clipped = np.zeros_like(hot)
    if hot.any():
        k = hot[:-2] & hot[1:-1] & hot[2:]
        clipped[:-2] |= k
        clipped[1:-1] |= k
        clipped[2:] |= k
    clip_ratio = float(clipped.mean())
    clip_frames = frames(clipped.astype(np.float32), sr).max(axis=1) > 0
    clip_regions = [(a * FRAME_S, b * FRAME_S) for a, b in runs(clip_frames) if b - a >= 1]
    return AudioStats(
        dur, speech_level, noise_floor, active, lead, trail, internal, noise_runs, clip_ratio, clip_regions
    )


def chunk_plan(x: np.ndarray, sr: int, max_s: float = 29.0, min_s: float = 18.0) -> list[tuple[int, int]]:
    """Cut points for <= max_s chunks, each cut at the quietest 100 ms inside [min_s, max_s] of the chunk."""
    n = len(x)
    if n <= max_s * sr:
        return [(0, n)]
    db = frame_db(x, sr)
    win = 5  # 5 x 20 ms
    smooth = np.convolve(db, np.ones(win) / win, mode="same")
    out, pos = [], 0
    while n - pos > max_s * sr:
        lo = int((pos / sr + min_s) / FRAME_S)
        hi = int((pos / sr + max_s) / FRAME_S)
        k = lo + int(np.argmin(smooth[lo:hi])) if hi > lo else hi
        cut = k * int(sr * FRAME_S)
        out.append((pos, cut))
        pos = cut
    out.append((pos, n))
    return out


def alt_chunk_plan(x: np.ndarray, sr: int) -> list[tuple[int, int]]:
    """A different segmentation for a second-opinion transcription."""
    n = len(x)
    if n > 29 * sr:
        return chunk_plan(x, sr, max_s=21.0, min_s=12.0)
    if n < 3 * sr:
        return [(0, n)]
    db = frame_db(x, sr)
    mid = len(db) // 2
    lo, hi = int(mid * 0.6), int(mid * 1.4)
    k = lo + int(np.argmin(db[lo:hi]))
    cut = k * int(sr * FRAME_S)
    return [(0, cut), (cut, n)]


def silence(seconds: float, sr: int) -> np.ndarray:
    return np.zeros(int(seconds * sr), dtype=np.float32)


def quiet_points(x: np.ndarray, sr: int, min_gap_s: float = 0.12) -> list[float]:
    """Centres (s) of short pauses, used by the injector to cut at word boundaries."""
    db = frame_db(x, sr)
    thr = max(-60.0, float(np.percentile(db, 90)) - 30.0)
    pts = []
    for a, b in runs(db < thr):
        if (b - a) * FRAME_S >= min_gap_s and a > 0 and b < len(db):
            pts.append((a + b) / 2 * FRAME_S)
    return pts
