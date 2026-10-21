from dataclasses import dataclass, field

from PySide6.QtGui import QImage, QPixmap


def _mirror_pixmap(pix: QPixmap) -> QPixmap:
    """水平镜像，保留 devicePixelRatio。用 QImage.mirrored 避免 QTransform 的坐标偏移问题。"""
    img = pix.toImage().mirrored(True, False)
    out = QPixmap.fromImage(img)
    out.setDevicePixelRatio(pix.devicePixelRatio())
    return out


@dataclass
class Clip:
    """一个可播放的动作。左右朝向共享同一组源帧，左向帧懒加载镜像缓存。"""
    action: str
    frames: list[QPixmap]
    fps: int
    loop: bool
    out_size: tuple[int, int]

    _mirrored: list[QPixmap] | None = field(default=None, init=False, repr=False)

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    @property
    def frame_duration_ms(self) -> float:
        return 1000.0 / self.fps

    def frames_for_facing(self, facing: str) -> list[QPixmap]:
        if facing != "left":
            return self.frames
        if self._mirrored is None:
            self._mirrored = [_mirror_pixmap(f) for f in self.frames]
        return self._mirrored