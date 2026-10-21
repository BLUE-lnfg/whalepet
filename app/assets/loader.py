from pathlib import Path

from PySide6.QtGui import QPixmap

from app.animation.clip import Clip
from app.assets.manifest import ClipManifest


def load_clip(cache_dir: Path, dpr: float = 1.0) -> Clip | None:
    """从 .cache/actions/<action>/ 读取帧序列，返回 Clip。失败返回 None。"""
    clip_json = cache_dir / "clip.json"
    if not clip_json.exists():
        return None

    manifest = ClipManifest.from_json(clip_json)

    frames: list[QPixmap] = []
    for name in manifest.frames:
        path = cache_dir / name
        if not path.exists():
            continue
        pix = QPixmap(str(path))
        if pix.isNull():
            continue
        # 关键：告诉 Qt 这张图对应多少物理像素，paintEvent 时 1:1 无重采样
        pix.setDevicePixelRatio(dpr)
        frames.append(pix)

    if not frames:
        return None

    return Clip(
        action=manifest.action,
        frames=frames,
        fps=manifest.out_fps,
        loop=manifest.loop,
        out_size=manifest.out_size,
    )