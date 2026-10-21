from pathlib import Path

from PySide6.QtCore import QObject, Signal

from app.animation.clip import Clip
from app.animation.player import FramePlayer
from app.assets.loader import load_clip


class PetController(QObject):
    clip_changed = Signal(object)

    def __init__(self, cache_root: Path, parent=None):
        super().__init__(parent)
        self._cache_root = cache_root
        self._clips: dict[str, Clip] = {}
        self._player = FramePlayer(self)
        self._player.finished.connect(self._on_clip_finished)
        self._current_action: str | None = None

    @property
    def player(self) -> FramePlayer:
        return self._player

    @property
    def current_action(self) -> str | None:
        return self._current_action

    def load_all(self, dpr: float):
        if not self._cache_root.exists():
            print(f"[controller] 缓存目录不存在：{self._cache_root}")
            print("[controller] 请先运行：python tools/import_assets.py")
            return
        for action_dir in sorted(self._cache_root.iterdir()):
            if not action_dir.is_dir():
                continue
            clip = load_clip(action_dir, dpr)
            if clip is None:
                print(f"[controller] 跳过 {action_dir.name}：无有效缓存")
                continue
            self._clips[clip.action] = clip
            print(
                f"[controller] 已加载 {clip.action}: "
                f"{clip.frame_count} 帧 @ {clip.fps}fps, "
                f"{clip.out_size[0]}x{clip.out_size[1]}, loop={clip.loop}"
            )

    def has(self, action: str) -> bool:
        return action in self._clips

    def play(self, action: str, loop: bool | None = None):
        clip = self._clips.get(action)
        if clip is None:
            print(f"[controller] 动作不存在：{action}")
            return
        self._current_action = action
        self.clip_changed.emit(clip)
        self._player.play(clip, loop)

    def play_idle(self):
        if self.has("idle"):
            self.play("idle")
        else:
            print("[controller] 没有 idle 动作，无法播放")

    def trigger_click(self):
        if self._current_action == "click":
            return
        if self.has("click"):
            self.play("click", loop=False)
        else:
            self.play_idle()

    def _on_clip_finished(self):
        if self._current_action == "click":
            self.play_idle()