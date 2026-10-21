"""Sincronía de la boca a partir del audio: lógica pura con numpy, sin modelos ni idioma concreto.

La abertura sale de la energía de la voz y la anchura de su brillo (centroide espectral: sonidos agudos = boca ancha,
graves = boca redonda). Es el método clásico de los dibujos animados: funciona igual en español que en cualquier idioma.
"""

import wave

import numpy as np


def read_wav(path_or_file) -> tuple[np.ndarray, int]:
    with wave.open(path_or_file) as w:
        rate, width, channels = w.getframerate(), w.getsampwidth(), w.getnchannels()
        raw = w.readframes(w.getnframes())
    if width != 2:
        raise ValueError("se espera WAV de 16 bits")
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return (samples.reshape(-1, channels).mean(axis=1) if channels > 1 else samples), rate


def _smooth(values: np.ndarray, attack: float, decay: float) -> np.ndarray:
    out = np.zeros_like(values)
    level = 0.0
    for i, v in enumerate(values):
        level += (v - level) * (attack if v > level else decay)
        out[i] = level
    return out


def mouth_curves(samples: np.ndarray, rate: int, fps: int) -> tuple[np.ndarray, np.ndarray]:
    """(abertura 0..1, anchura 0..1) por fotograma."""
    hop = rate // fps
    count = len(samples) // hop
    window = np.hanning(hop)
    freqs = np.fft.rfftfreq(hop, 1 / rate)
    rms = np.zeros(count, dtype=np.float32)
    centroid = np.zeros(count, dtype=np.float32)
    for i in range(count):
        chunk = samples[i * hop : (i + 1) * hop]
        rms[i] = float(np.sqrt(np.mean(chunk**2)))
        spectrum = np.abs(np.fft.rfft(chunk * window))
        total = float(spectrum.sum())
        centroid[i] = float((freqs * spectrum).sum() / total) if total > 1e-9 else 0.0

    scale = float(np.percentile(rms, 95)) or 1.0
    jaw = np.clip(rms / scale, 0, 1) ** 0.75
    jaw[rms < 0.03 * scale] = 0.0  # silencio: boca cerrada
    wide = np.clip((centroid - 600) / (3200 - 600), 0, 1)
    return _smooth(jaw, 0.65, 0.35), _smooth(wide, 0.4, 0.3)
