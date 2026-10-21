import asyncio
import shutil
from pathlib import Path

from app.core.interfaces import ProviderError
from app.core.subtitles import chunk_segments, to_srt
from app.core.types import RenderedVideo, VideoSpec

SUBTITLE_STYLE = (
    "FontName=DejaVu Sans,FontSize=12,Bold=1,Alignment=2,MarginV=90,Outline=3,Shadow=0,"
    "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000"
)
# Un movimiento de cámara distinto por escena (acercar, alejar, paneo) da sensación de profundidad sin animar personajes
CAMERA = (
    "z='min(zoom+0.0007,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    "z='if(eq(on,1),1.15,max(zoom-0.0007,1.0))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    "z=1.12:x='(iw-iw/zoom)*on/{frames}':y='ih/2-(ih/zoom/2)'",
    "z=1.12:x='(iw-iw/zoom)*(1-on/{frames})':y='ih/2-(ih/zoom/2)'",
)
ZOOM_OVERSCAN = 1.5  # las imágenes se amplían antes del zoom suave para que no se vea el pixelado
FOREGROUND_RATIO = 4 / 3  # la imagen nítida es 3:4; el resto del 9:16 se rellena con ella misma desenfocada


class FFmpegVideo:
    """Imágenes con zoom suave + narración + subtítulos quemados, todo en una sola pasada de FFmpeg.

    Las imágenes 3:4 no se estiran a 9:16: van a ancho completo sobre un fondo desenfocado de la misma imagen.
    """

    def __init__(self, preset: str = "fast", crf: int = 21):
        self._preset = preset
        self._crf = crf

    async def render(self, spec: VideoSpec) -> RenderedVideo:
        if not spec.images:
            raise ProviderError("ffmpeg: no hay imágenes")
        for tool in ("ffmpeg", "ffprobe"):
            if not shutil.which(tool):
                raise ProviderError(f"{tool} no está instalado")

        output = spec.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        srt = output.with_suffix(".srt")
        srt.write_text(to_srt(chunk_segments(spec.segments)), encoding="utf-8")

        audio = spec.audio.resolve()
        duration = await self._duration(audio)
        n = len(spec.images)
        if spec.durations and len(spec.durations) == n:
            scale = duration / sum(spec.durations)  # el audio manda: las escenas se ajustan a su duración total
            frames_per = [max(1, round(d * scale * spec.fps)) for d in spec.durations]
        else:
            frames_per = [max(1, round(duration / n * spec.fps))] * n
        w, h = spec.width, spec.height
        fh = round(w * FOREGROUND_RATIO / 2) * 2  # altura de la imagen nítida, par para el códec
        bw, bh = int(w * ZOOM_OVERSCAN), int(fh * ZOOM_OVERSCAN)

        # Recorte previo de la franja inferior; trunc(.../2)*2 mantiene una altura par para el códec
        trim = f"crop=iw:trunc(ih*{1 - spec.crop_bottom:.4f}/2)*2:0:0," if spec.crop_bottom > 0 else ""
        animated = [bool(spec.clips and spec.clips[i]) for i in range(n)]
        clips = [
            # Escena con clip de paralaje: ya viene compuesta en 1080x1920; solo se ajusta a la duración de la escena
            f"[{i}:v]fps={spec.fps},trim=end_frame={frames_per[i]},setpts=PTS-STARTPTS,format=yuv420p,setsar=1[v{i}]"
            if animated[i] else
            f"[{i}:v]{trim}format=yuv420p,split[bg{i}][fg{i}];"
            f"[bg{i}]scale={w // 6}:{h // 6}:force_original_aspect_ratio=increase,crop={w // 6}:{h // 6},"
            f"boxblur=4:2,scale={w}:{h},eq=brightness=-0.1,"
            f"zoompan=z=1:d={frames_per[i]}:s={w}x{h}:fps={spec.fps}[b{i}];"
            f"[fg{i}]scale={bw}:{bh}:force_original_aspect_ratio=increase:flags=lanczos,crop={bw}:{bh},unsharp=5:5:0.5,"
            f"zoompan={CAMERA[i % len(CAMERA)].replace('{frames}', str(frames_per[i]))}"
            f":d={frames_per[i]}:s={w}x{fh}:fps={spec.fps}[f{i}];"
            f"[b{i}][f{i}]overlay=0:(H-h)/2,setsar=1[v{i}]"
            for i in range(n)
        ]
        joined = "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[cat]"
        tail = [f"[cat]subtitles={srt.name}:force_style='{SUBTITLE_STYLE}'[body0]"]
        cmd = ["ffmpeg", "-y", "-loglevel", "error"]
        for i, image in enumerate(spec.images):
            cmd += ["-i", str((spec.clips[i] if animated[i] else image).resolve())]
        cmd += ["-i", str(audio)]
        nxt, body = n + 1, "body0"
        if spec.watermark:
            cmd += ["-i", str(spec.watermark.resolve())]
            tail += [f"[{nxt}:v]scale=150:-1,format=rgba,colorchannelmixer=aa=0.85[wm]", f"[{body}][wm]overlay=W-w-40:190[body1]"]
            nxt, body = nxt + 1, "body1"
        total = duration
        audio_map = f"{n}:a"
        if spec.outro:
            cmd += ["-loop", "1", "-framerate", str(spec.fps), "-t", f"{spec.outro_seconds}", "-i", str(spec.outro.resolve())]
            tail += [
                f"[{nxt}:v]scale={w}:{h},setsar=1,fps={spec.fps},format=yuv420p[vo]",
                f"[{body}]format=yuv420p,setsar=1[bd]", "[bd][vo]concat=n=2:v=1:a=0[body2]",
                f"[{n}:a]apad=pad_dur={spec.outro_seconds}[aout]",
            ]
            body, audio_map, total = "body2", "[aout]", duration + spec.outro_seconds
        tail.append(f"[{body}]scale=out_color_matrix=bt709:out_range=tv,format=yuv420p[out]")
        cmd += [
            "-filter_complex", ";".join([*clips, joined, *tail]),
            "-map", "[out]", "-map", audio_map, "-t", f"{total:.2f}",
            "-c:v", "libx264", "-preset", self._preset, "-crf", str(self._crf), "-pix_fmt", "yuv420p",
            "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(output),
        ]
        await self._run(cmd, cwd=output.parent)  # cwd = carpeta del .srt: evita escapar rutas en el filtro

        return RenderedVideo(path=output, duration=await self._duration(output), file_size=output.stat().st_size)

    async def _duration(self, path: Path) -> float:
        out = await self._run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]
        )
        try:
            return float(out.strip())
        except ValueError as e:
            raise ProviderError(f"ffprobe: duración ilegible en {path.name}") from e

    @staticmethod
    async def _run(cmd: list[str], cwd: Path | None = None) -> str:
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=cwd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode:
            raise ProviderError(f"{cmd[0]} falló: {stderr.decode(errors='replace')[-600:]}")
        return stdout.decode()
