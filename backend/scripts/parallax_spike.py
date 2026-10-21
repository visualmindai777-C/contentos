"""Prueba manual: profundidad + paralaje de las imágenes de muestra, con tiempos. Uso: python scripts/parallax_spike.py"""
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.providers.motion_parallax import MODEL, estimate_depth, render_parallax  # noqa: E402

ASSETS = Path(__file__).resolve().parent.parent / "tests" / "assets"
OUT = Path(__file__).resolve().parent.parent / "spike_out"
OUT.mkdir(exist_ok=True)

t0 = time.time()
from transformers import pipeline  # noqa: E402

pipe = pipeline(task="depth-estimation", model=MODEL, device=-1)
print(f"modelo cargado en {time.time() - t0:.1f} s", flush=True)

clips = []
for i, image in enumerate(sorted(ASSETS.glob("sample_*.jpg"))):
    t = time.time()
    depth = estimate_depth(pipe, image)
    t_depth = time.time() - t
    import cv2
    import numpy as np

    cv2.imwrite(str(OUT / f"depth_{i}.png"), (depth * 255).astype(np.uint8))
    t = time.time()
    clip = OUT / f"clip_{i}.mp4"
    render_parallax(image, depth, clip, seconds=8.0, index=i)
    print(f"escena {i}: profundidad {t_depth:.1f} s, render de 8 s de video {time.time() - t:.1f} s", flush=True)
    clips.append(clip)

listing = OUT / "list.txt"
listing.write_text("".join(f"file '{c.name}'\n" for c in clips))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(OUT / "spike.mp4")], check=True)
print(f"total {time.time() - t0:.1f} s", flush=True)
