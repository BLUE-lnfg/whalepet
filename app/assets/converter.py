import time
from pathlib import Path

import av
from PIL import Image, ImageSequence

from app.assets.manifest import ClipManifest

SOURCE_SUFFIXES = (".gif", ".webm")


# ---------- 解码 ----------

def _decode_gif(path: Path):
    frames, times = [], []
    t = 0.0
    with Image.open(path) as im:
        for frame in ImageSequence.Iterator(im):
            dur = frame.info.get("duration", 0) / 1000.0
            if dur <= 0:
                dur = 1 / 30
            frames.append(frame.convert("RGBA"))
            times.append(t)
            t += dur
    return frames, times


def _decode_webm(path: Path):
    frames, times = [], []
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        for frame in container.decode(stream):
            img = frame.to_image().convert("RGBA")
            t = float(frame.pts * stream.time_base) if frame.pts is not None else len(frames) / 30
            frames.append(img)
            times.append(t)
    return frames, times


def _decode(path: Path):
    if path.suffix.lower() == ".gif":
        return _decode_gif(path)
    return _decode_webm(path)


# ---------- 重采样 ----------

def _resample(frames, times, dst_fps: int):
    if len(frames) < 2:
        return frames, float(dst_fps)

    duration = times[-1] + (times[-1] - times[-2])
    src_fps = (len(frames) - 1) / max(times[-1], 1e-6) if times[-1] > 0 else dst_fps

    dst_count = max(1, int(round(duration * dst_fps)))
    out = []
    j = 0
    for i in range(dst_count):
        t = i / dst_fps
        while j + 1 < len(times) and times[j + 1] <= t:
            j += 1
        out.append(frames[j])
    return out, src_fps


# ---------- 缩放 ----------

def _fit_size(w: int, h: int, longest: int):
    if max(w, h) <= longest:
        return w, h
    s = longest / max(w, h)
    return max(1, round(w * s)), max(1, round(h * s))


def _resize_rgba(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    return img.convert("RGBa").resize(size, Image.Resampling.LANCZOS).convert("RGBA")


# ---------- 主入口 ----------

def import_action(
    action_dir: Path,
    cache_dir: Path,
    target_longest: int = 480,
    target_fps: int = 60,
    force: bool = False,
) -> ClipManifest | None:
    src = next(
        (p for p in action_dir.iterdir()
         if p.is_file() and p.suffix.lower() in SOURCE_SUFFIXES),
        None,
    )
    if src is None:
        return None

    clip_json = cache_dir / "clip.json"
    if not force and clip_json.exists() and clip_json.stat().st_mtime >= src.stat().st_mtime:
        return ClipManifest.from_json(clip_json)

    t0 = time.time()
    print(f"  解码 {src.name} ...", end="", flush=True)
    frames, times = _decode(src)
    print(f" {len(frames)} 帧", flush=True)

    frames, src_fps = _resample(frames, times, target_fps)
    w, h = frames[0].size
    out_size = _fit_size(w, h, target_longest)

    cache_dir.mkdir(parents=True, exist_ok=True)
    for old in cache_dir.glob("*.webp"):
        old.unlink()

    print(f"  缩放+写盘 {len(frames)} 帧 → {out_size[0]}x{out_size[1]} ...", end="", flush=True)
    frame_names = []
    for i, img in enumerate(frames):
        img = _resize_rgba(img, out_size)
        name = f"{i:04d}.webp"
        img.save(cache_dir / name, "WEBP", lossless=True, quality=100, method=4)
        frame_names.append(name)

    duration = len(frames) / target_fps
    manifest = ClipManifest(
        action=action_dir.name,
        source_file=src.name,
        src_fps=round(src_fps, 2),
        src_frames=len(times),
        duration=round(duration, 3),
        out_size=out_size,
        out_fps=target_fps,
        frame_count=len(frames),
        frames=frame_names,
    )
    manifest.to_json(clip_json)
    print(f" 完成，耗时 {time.time() - t0:.1f}s", flush=True)
    return manifest