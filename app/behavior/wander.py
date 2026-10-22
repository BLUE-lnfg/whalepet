import random

from PySide6.QtCore import QEasingCurve, QObject, QTimer, QVariantAnimation

from app.animation.controller import PetController
from app.config.binder import ConfigBinder
from app.config.manager import ConfigManager
from app.ui.pet_window import PetWindow


class WanderManager(QObject):
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

        # 声明式绑定：散步组 + 翻面组分开，一眼能看清各自关心什么
        self._binder = ConfigBinder(config, self)
        self._binder.bind(
            ["behavior.walk.enabled",
             "behavior.walk.min_interval_s",
             "behavior.walk.max_interval_s"],
            self._on_walk_config_changed,
        )
        self._binder.bind(
            ["behavior.facing.turn_min_s",
             "behavior.facing.turn_max_s",
             "behavior.facing.turn_probability"],
            self._on_facing_config_changed,
        )

    def _cfg(self, key, default):
        return self._config.get(f"behavior.{key}", default)

    # ---------- 配置变化响应 ----------

    def _on_walk_config_changed(self, key: str):
        enabled = self._cfg("walk.enabled", True)
        if not enabled:
            print(f"[wander] {key} → 散步已禁用，停止定时器")
            self._wander_timer.stop()
            if self._walking:
                self._abort_walk("开关被关闭")
            return
        print(f"[wander] {key} → 散步已启用，重新调度")
        self._schedule_wander()

    def _on_facing_config_changed(self, key: str):
        print(f"[wander] {key} → 翻面参数已更新，重新调度")
        self._schedule_facing()

    # ---------- 启动 ----------

    def start(self):
        print(f"[wander] 启动：散步间隔 {self._cfg('walk.min_interval_s', 25)}-"
              f"{self._cfg('walk.max_interval_s', 70)}s，"
              f"翻面间隔 {self._cfg('facing.turn_min_s', 8)}-"
              f"{self._cfg('facing.turn_max_s', 20)}s")
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
        delay = int(random.uniform(lo, hi) * 1000)
        self._wander_timer.start(delay)

    def _try_start_walk(self):
        if not self._cfg("walk.enabled", True):
            print("[wander] 跳过散步：walk.enabled = false")
            return

        if self._walking:
            print("[wander] 跳过散步：正在散步")
            self._schedule_wander()
            return

        if self._controller.current_action != "idle":
            print(f"[wander] 跳过散步：当前动作 {self._controller.current_action} 非 idle")
            self._schedule_wander()
            return

        if not self._controller.has(self.WALK_ACTION):
            print("[wander] 跳过散步：无 walk 动作素材")
            self._schedule_wander()
            return

        lo = int(self._cfg("walk.min_distance", 120))
        hi = int(self._cfg("walk.max_distance", 380))
        distance = random.randint(lo, max(lo, hi))
        direction = random.choice((-1, 1))

        min_x, max_x = self._pet.walk_x_bounds()
        cur_x = self._pet.x()

        if direction == -1 and cur_x - distance < min_x:
            direction = 1
        elif direction == 1 and cur_x + distance > max_x:
            direction = -1

        target_x = max(min_x, min(max_x, cur_x + direction * distance))
        if abs(target_x - cur_x) < 20:
            print("[wander] 跳过散步：位移不足 20px（已贴边）")
            self._schedule_wander()
            return

        self._pet.set_facing("left" if direction == -1 else "right")

        self._walking = True
        self._controller.play(self.WALK_ACTION, loop=True)

        speed = max(10, int(self._cfg("walk.speed_px_per_s", 80)))
        duration_ms = int(abs(target_x - cur_x) / speed * 1000)
        duration_ms = max(200, duration_ms)

        actual_distance = abs(target_x - cur_x)
        print(f"[wander] 开始散步：方向={'左' if direction == -1 else '右'}，"
              f"距离 {actual_distance}px，速度 {speed}px/s，"
              f"预计 {duration_ms / 1000:.1f}s")

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
        print("[wander] 散步完成，回到 idle")
        self._controller.play_idle()
        self._schedule_wander()

    def _abort_walk_by_drag(self):
        self._abort_walk("拖动")

    def _abort_walk(self, reason: str):
        if not self._walking:
            return
        self._move_anim.stop()
        self._walking = False
        print(f"[wander] 散步被打断（{reason}）")
        self._controller.play_idle()
        self._schedule_wander()

    def _on_clip_changed(self, clip):
        if self._walking and clip.action != self.WALK_ACTION:
            self._abort_walk(f"动作切换到 {clip.action}")

    # ---------- 随机朝向 ----------

    def _schedule_facing(self):
        lo = float(self._cfg("facing.turn_min_s", 8))
        hi = float(self._cfg("facing.turn_max_s", 20))
        if hi < lo:
            hi = lo
        delay = int(random.uniform(lo, hi) * 1000)
        self._facing_timer.start(delay)

    def _maybe_turn_facing(self):
        self._schedule_facing()
        if self._walking:
            return
        if self._controller.current_action != "idle":
            return
        if random.random() < float(self._cfg("facing.turn_probability", 0.5)):
            old = self._pet.facing
            self._pet.toggle_facing()
            print(f"[wander] 随机翻面：{old} → {self._pet.facing}")