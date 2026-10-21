"""Genera la línea de tiempo de fotogramas (pose de cada personaje) a partir del audio y de quién habla en cada momento.
Uso: python make_timeline.py samples/dialogue.json timeline.json"""
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.lipsync import mouth_curves, read_wav  # noqa: E402

src = Path(sys.argv[1])
config = json.loads(src.read_text(encoding="utf-8"))
samples, rate = read_wav(str(src.parent / config["audio"]))
fps = config["fps"]
jaw, wide = mouth_curves(samples, rate, fps)
frames_total = len(jaw)
rng = random.Random(7)

# Parpadeos: cada 2 a 4,5 s, de 5 fotogramas
blinks, t = set(), rng.uniform(1.0, 2.5)
while t < frames_total / fps:
    start = round(t * fps)
    blinks.update({start: 0.5, start + 1: 1.0, start + 2: 1.0, start + 3: 0.6, start + 4: 0.2}.items())
    t += rng.uniform(2.0, 4.5)
blink = dict(blinks)

lines = config["lines"]
frames, current = [], lines[0].get("shows") or lines[0]["speaker"]
for f in range(frames_total):
    time = f / fps
    line = next((l for l in lines if l["start"] <= time < l["end"]), None)
    speaking = line is not None and line["speaker"] != "NARRADOR"
    if line:
        current = line.get("shows") or line["speaker"]
    progress = (time - line["start"]) / (line["end"] - line["start"]) if line else 0.0
    j = float(jaw[f]) if speaking else 0.0
    frames.append({
        "char": current,
        "jaw": round(j, 3),
        "wide": round(float(wide[f]), 3) if speaking else 0.5,
        "blink": blink.get(f, 0.0),
        "brow": round(0.3 * j - (0.25 if line and line["speaker"] == "NARRADOR" else 0.0), 3),
        "yaw": round(math.sin(time * 0.9) * 0.07 + j * 0.02, 4),
        "pitch": round(-0.035 * j + math.sin(time * 1.3) * 0.015, 4),
        "roll": round(math.sin(time * 0.7) * 0.02, 4),
        "bob": round(math.sin(time * 2.1) * 0.012, 4),
        "lookX": round(math.sin(time * 0.5), 3),
        "gesture": round(j * math.sin(time * 5.0), 3),
        "zoom": round(1.0 + 0.07 * progress, 4),
    })

Path(sys.argv[2]).write_text(json.dumps({"characters": config["characters"], "frames": frames}), encoding="utf-8")
print(f"{frames_total} fotogramas a {fps} fps ({frames_total / fps:.1f} s)")
