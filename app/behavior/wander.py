import random

from PySide6.QtCore import QEasingCurve, QObject, QTimer, QVariantAnimation

from app.animation.controller import PetController
from app.config.manager import ConfigManager
from app.ui.pet_window import PetWindow


class WanderManager(QObject):
    """自动散步 + 随机朝向。所有触发参数都从 config 读，用户可改 config.json 调。"""

    WALK_ACTION = "walk"

    def __init__(self, pet: PetWindow, controller: PetController, config: ConfigManager):
        super().__init__()
        self._pet = pet
        self._controller = controller
        self._config = config

        self._wander_timer = QTimer(self)
        self._wander_timer.setSingleShot(True)
        self._wander_timer.timeout.connect(self._try_start_walk)

        self._facing_timer = QTimer(self)
        self._facing_timer.setSingleShot(True)
        self._facing_timer.timeout.connect(self._maybe_turn_facing)

        self._move_anim = QVariantAnimation(self)
        self._move_anim.setEasingCurve(QEasingCurve.Linear)
        self._move_anim.valueChanged.connect(self._on_move)
        self._move_anim.finished.connect(self._on_walk_done)

        self._walking = False

        self._pet.drag_started.connect(self._abort_walk_by_drag)
        self._controller.clip_changed.connect(self._on_clip_changed)

    # ---------- 配置读取 ----------

    def _cfg(self, key, default):
        return self._config.get(f"behavior.{key}", default)

    # ---------- 启动 ----------

    def start(self):
        self._schedule_wander()
        self._schedule_facing()

    # ---------- 散步 ----------

    def _schedule_wander(self):
        if not self._cfg("walk.enabled", True):
            return
        lo = float(self._cfg("walk.min_interval_s", 25))
        hi = float(self._cfg("walk.max_interval_s", 70))
        if hi < lo:
            hi = lo
        self._wander_timer.start(int(random.uniform(lo, hi) * 1000))

    def _try_start_walk(self):
        if self._walking or self._controller.current_action != "idle":
            self._schedule_wander()
            return
        if not self._controller.has(self.WALK_ACTION):
            # 没有 walk 素材，静默跳过，但不影响下次再试（用户以后补了素材就自动生效）
            self._schedule_wander()
            return

        lo = int(self._cfg("walk.min_distance", 120))
        hi = int(self._cfg("walk.max_distance", 380))
        distance = random.randint(lo, max(lo, hi))
        direction = random.choice((-1, 1))

        min_x, max_x = self._pet.walk_x_bounds()
        cur_x = self._pet.x()

        # 一侧空间不够就反向；反向也不够就放弃本次
        if direction == -1 and cur_x - distance < min_x:
            direction = 1
        elif direction == 1 and cur_x + distance > max_x:
            direction = -1

        target_x = max(min_x, min(max_x, cur_x + direction * distance))
        if abs(target_x - cur_x) < 20:
            self._schedule_wander()
            return

        # 朝向与移动方向一致
        self._pet.set_facing("left" if direction == -1 else "right")

        self._walking = True
        self._controller.play(self.WALK_ACTION, loop=True)

        speed = max(10, int(self._cfg("walk.speed_px_per_s", 50)))
        duration_ms = int(abs(target_x - cur_x) / speed * 1000)
        duration_ms = max(200, duration_ms)

        self._move_anim.stop()
        self._move_anim.setDuration(duration_ms)
        self._move_anim.setStartValue(cur_x)
        self._move_anim.setEndValue(target_x)
        self._move_anim.start()

    def _on_move(self, value):
        if not self._walking:
            return
        self._pet.move(int(round(float(value))), self._pet.y())

    def _on_walk_done(self):
        if not self._walking:
            return
        self._walking = False
        self._controller.play_idle()
        self._schedule_wander()

    def _abort_walk_by_drag(self):
        if not self._walking:
            return
        self._move_anim.stop()
        self._walking = False
        self._controller.play_idle()
        self._schedule_wander()

    def _on_clip_changed(self, clip):
        # 散步期间若被外部切走（比如 click），立刻停止位移
        if self._walking and clip.action != self.WALK_ACTION:
            self._move_anim.stop()
            self._walking = False
            self._schedule_wander()

    # ---------- 随机朝向 ----------

    def _schedule_facing(self):
        lo = float(self._cfg("facing.turn_min_s", 8))
        hi = float(self._cfg("facing.turn_max_s", 20))
        if hi < lo:
            hi = lo
        self._facing_timer.start(int(random.uniform(lo, hi) * 1000))

    def _maybe_turn_facing(self):
        self._schedule_facing()
        if self._walking:
            return
        if self._controller.current_action != "idle":
            return
        if random.random() < float(self._cfg("facing.turn_probability", 0.5)):
            self._pet.toggle_facing()