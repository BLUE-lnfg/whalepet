from PySide6.QtCore import QObject, QTimer, QElapsedTimer, Qt, Signal

from app.animation.clip import Clip


class FramePlayer(QObject):
    """
    按真实时间推进帧。QTimer 只负责"多久检查一次"，
    真正的帧号由 QElapsedTimer 的时间戳换算，避免定时器抖动导致卡顿或跳帧。
    """
    frame_changed = Signal(int)   # 参数：当前帧索引
    finished = Signal()           # 非循环动作播完时发出

    def __init__(self, parent=None):
        super().__init__(parent)
        self._clip: Clip | None = None
        self._current = 0
        self._loop = True
        self._elapsed = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.timeout.connect(self._tick)

    def play(self, clip: Clip, loop: bool | None = None):
        self._clip = clip
        self._loop = clip.loop if loop is None else loop
        self._current = 0
        self._elapsed.restart()
        # 按帧时长的一半检查一次，保证不晚于下一帧该切换的时刻
        interval = max(1, int(clip.frame_duration_ms / 2))
        self._timer.start(interval)
        self.frame_changed.emit(0)

    def stop(self):
        self._timer.stop()
        self._clip = None

    def current_index(self) -> int:
        return self._current

    def _tick(self):
        clip = self._clip
        if clip is None:
            return

        elapsed_ms = self._elapsed.elapsed()
        idx = int(elapsed_ms * clip.fps / 1000.0)

        if idx >= clip.frame_count:
            if self._loop:
                self._elapsed.restart()
                idx = 0
            else:
                # 停在最后一帧，通知"播完了"
                if self._current != clip.frame_count - 1:
                    self._current = clip.frame_count - 1
                    self.frame_changed.emit(self._current)
                self._timer.stop()
                self.finished.emit()
                return

        if idx != self._current:
            self._current = idx
            self.frame_changed.emit(idx)