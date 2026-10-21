from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QSoundEffect


class VoicePlayer(QObject):
    MAX_POOL = 4

    played = Signal(str)  # 播放时发出文件绝对路径，测试工具和 M4 面板都会订阅

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pool: list[QSoundEffect] = []
        self._volume = 0.8

    def set_volume(self, volume: float):
        self._volume = max(0.0, min(1.0, float(volume)))
        for e in self._pool:
            e.setVolume(self._volume)

    def is_playing(self) -> bool:
        return any(e.isPlaying() for e in self._pool)

    def stop_all(self):
        for e in self._pool:
            e.stop()

    def play(self, path: Path, interrupt: bool = False):
        if not path.exists():
            return
        if interrupt:
            self.stop_all()
        effect = self._acquire()
        effect.setSource(QUrl.fromLocalFile(str(path)))
        effect.play()
        self.played.emit(str(path))

    def _acquire(self) -> QSoundEffect:
        for e in self._pool:
            if not e.isPlaying():
                return e
        if len(self._pool) >= self.MAX_POOL:
            old = self._pool.pop(0)
            old.stop()
            old.deleteLater()
        e = QSoundEffect(self)
        e.setVolume(self._volume)
        self._pool.append(e)
        return e