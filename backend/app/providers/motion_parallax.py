"""Paralaje 3D a partir de una imagen fija: un modelo abierto estima la profundidad (Depth Anything V2 Small, Apache-2.0,
25 M de parámetros, corre en CPU) y la cámara se mueve desplazando cada píxel según su cercanía. Sin cuentas ni pago."""

import asyncio
import subprocess
from pathlib import Path
from typing import Any

from app.core.interfaces import ProviderError

MODEL = "depth-anything/Depth-Anything-V2-Small-hf"
FG_RATIO = 4 / 3  # la imagen es 3:4; el resto del 9:16 es su propio fondo desenfocado (igual que el video con zoom)
MARGIN = 1.20  # la imagen se amplía para tener margen de movimiento sin ver los bordes

# (paneo x, paneo y, paralaje, zoom inicial, zoom final): un movimiento distinto por escena
PATHS = (
    (-0.020, 0.0, 46.0, 1.00, 1.08),
    (0.020, 0.0, -46.0, 1.08, 1.00),
    (0.0, -0.016, 40.0, 1.00, 1.07),
    (0.014, 0.012, -40.0, 1.06, 1.00),
)


def estimate_depth(pipe: Any, image: Path):
    """Profundidad relativa normalizada a 0..1 (1 = lo más cercano)."""
    import numpy as np
    from PIL import Image

    out = pipe(Image.open(image).convert("RGB"))["depth"]
    depth = np.asarray(out, dtype=np.float32)
    low, high = float(depth.min()), float(depth.max())
    return (depth - low) / (high - low) if high > low else np.zeros_like(depth)


def render_parallax(
    image: Path, depth, output: Path, *, seconds: float, index: int, fps: int = 30, width: int = 1080, height: int = 1920,
) -> None:
    import cv2
    import numpy as np

    fg_h = round(width * FG_RATIO / 2) * 2
    top = (height - fg_h) // 2
    big_w, big_h = int(width * MARGIN), int(fg_h * MARGIN)

    src = cv2.imread(str(image), cv2.IMREAD_COLOR)
    if src is None:
        raise ProviderError(f"parallax: no se pudo leer {image.name}")

    def cover(img, w, h):
        scale = max(w / img.shape[1], h / img.shape[0])
        resized = cv2.resize(img, (round(img.shape[1] * scale), round(img.shape[0] * scale)), interpolation=cv2.INTER_CUBIC)
        y, x = (resized.shape[0] - h) // 2, (resized.shape[1] - w) // 2
        return resized[y : y + h, x : x + w]

    big = cover(src, big_w, big_h)
    d = cv2.resize(depth, (big_w, big_h), interpolation=cv2.INTER_CUBIC)
    d = cv2.GaussianBlur(d, (0, 0), sigmaX=big_w * 0.004)  # bordes de profundidad suaves: evita rasgaduras al desplazar
    d = d[(big_h - fg_h) // 2 : (big_h - fg_h) // 2 + fg_h, (big_w - width) // 2 : (big_w - width) // 2 + width]
    centered = (d - 0.5).astype(np.float32)

    bg = cv2.resize(cover(src, width // 6, height // 6), (width, height), interpolation=cv2.INTER_LINEAR)
    bg = cv2.GaussianBlur(bg, (0, 0), sigmaX=6)
    bg = (bg * 0.9).astype(np.uint8)

    xs = np.arange(width, dtype=np.float32)[None, :]
    ys = np.arange(fg_h, dtype=np.float32)[:, None]
    pan_x, pan_y, par, z0, z1 = PATHS[index % len(PATHS)]
    frames = max(2, round(seconds * fps))

    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{width}x{height}", "-r", str(fps),
         "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(output)],
        stdin=subprocess.PIPE,
    )
    try:
        for k in range(frames):
            t = k / (frames - 1)
            t = t * t * (3 - 2 * t)  # suavizado de entrada y salida
            zoom = z0 + (z1 - z0) * t
            move = 2 * t - 1
            mx = (big_w / 2 + (xs - width / 2) / zoom + pan_x * width * move + par * move * centered).astype(np.float32)
            my = (big_h / 2 + (ys - fg_h / 2) / zoom + pan_y * fg_h * move + par * 0.4 * move * centered).astype(np.float32)
            fg = cv2.remap(big, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            frame = bg.copy()
            frame[top : top + fg_h] = fg
            proc.stdin.write(frame.tobytes())
        proc.stdin.close()
    except BrokenPipeError:
        pass
    if proc.wait() != 0:
        raise ProviderError("parallax: ffmpeg falló al codificar el clip")


class ParallaxMotion:
    """MotionProvider: imagen → clip con profundidad. El modelo se carga al primer uso (la API no lo necesita)."""

    def __init__(self, model: str = MODEL) -> None:
        self._model = model
        self._pipe: Any = None

    async def animate(self, image: Path, output: Path, *, seconds: float, index: int) -> Path:
        await asyncio.to_thread(self._animate, image, output, seconds, index)
        return output

    def _animate(self, image: Path, output: Path, seconds: float, index: int) -> None:
        try:
            if self._pipe is None:
                from transformers import pipeline

                self._pipe = pipeline(task="depth-estimation", model=self._model, device=-1)
            render_parallax(image, estimate_depth(self._pipe, image), output, seconds=seconds, index=index)
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"parallax: {e!r}") from e
