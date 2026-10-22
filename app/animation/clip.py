from dataclasses import dataclass, field
from PySide6.QtGui import QImage, QPixmap

def _mirror(pix: QPixmap) -> QPixmap:
    img = pix.toImage().mirrored(True, False)
    out = QPixmap.fromImage(img)
    out.setDevicePixelRatio(pix.devicePixelRatio())
    return out

@dataclass
class Clip:
    action: str
    frames: list[QPixmap]
    fps: int
    loop: bool
    out_size: tuple[int, int]
    _mirrored: list[QPixmap] | None = field(default=None, init=False, repr=False)

    @property
    def frame_count(self): return len(self.frames)
    @property
    def frame_duration_ms(self): return 1000.0 / self.fps

    def frames_for_facing(self, facing: str) -> list[QPixmap]:
        if facing != "left": return self.frames
        if self._mirrored is None:
            self._mirrored = [_mirror(f) for f in self.frames]
        return self._mirrored