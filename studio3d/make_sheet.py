"""Hoja de personajes: cada uno en reposo y hablando, para revisar su diseño. Uso: python make_sheet.py timeline.json"""
import json
import sys

CAST = ["fresa", "pina", "banana", "limon", "sandia", "kiwi"]
neutral = {"jaw": 0.0, "wide": 0.5, "blink": 0.0, "brow": 0.0, "yaw": 0.15, "pitch": 0.0, "roll": 0.0, "bob": 0.0, "lookX": 0.0, "gesture": 0.0, "zoom": 1.0}
speaking = {**neutral, "jaw": 0.8, "wide": 0.6, "yaw": -0.1, "gesture": 0.8, "brow": 0.3}
frames = [{"char": c, **neutral} for c in CAST] + [{"char": c, **speaking} for c in CAST]
json.dump({"characters": {c: {"kind": c} for c in CAST}, "frames": frames}, open(sys.argv[1], "w"))
print(len(frames), "fotogramas")
