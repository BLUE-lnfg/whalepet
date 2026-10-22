from pathlib import Path
from PySide6.QtCore import QObject, Signal
from app.animation.clip import Clip
from app.animation.player import FramePlayer
from app.assets.loader import load_clip

class PetController(QObject):
    clip_changed = Signal(object)
    def __init__(self, cache_root: Path):
        super().__init__()
        self._clips = {}
        self._player = FramePlayer(self)
        self._player.finished.connect(self._on_finished)
        self._current_action = None
        self._cache_root = cache_root

    @property
    def player(self): return self._player
    @property
    def current_action(self): return self._current_action

    def load_all(self, dpr: float):
        for action_dir in sorted(self._cache_root.iterdir()):
            if action_dir.is_dir():
                clip = load_clip(action_dir, dpr)
                if clip: self._clips[clip.action] = clip

    def clear(self):
        self._player.stop()
        self._current_action = None
        self._clips.clear()

    def has(self, action: str): return action in self._clips

    def available_actions(self):
        """供外部查询有哪些动作可用（防止调度不存在的动作）"""
        return self._clips.keys()

    def play(self, action: str, loop: bool = None):
        clip = self._clips.get(action)
        if not clip: return
        self._current_action = action
        self.clip_changed.emit(clip)
        self._player.play(clip, loop)

    def play_idle(self):
        if self.has("idle"): self.play("idle")

    def trigger_click(self):
        if self._current_action == "click": return
        if self.has("click"): self.play("click", loop=False)
        else: self.play_idle()

    def _on_finished(self):
        # 如果是点击动作，播完回主待机
        if self._current_action == "click":
            self.play_idle()
        # 如果是备用待机动作（例如 idle_alt1 等），播完也回主待机
        elif self._current_action and self._current_action.startswith("idle_") and self._current_action != "idle":
            self.play_idle()