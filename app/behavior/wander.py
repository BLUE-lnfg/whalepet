import random
from PySide6.QtCore import QObject, QTimer, QVariantAnimation, QEasingCurve
from app.animation.controller import PetController
from app.config.binder import ConfigBinder
from app.config.manager import ConfigManager
from app.ui.pet_window import PetWindow


class WanderManager(QObject):
    WALK_ACTION = "walk"

    def __init__(self, pet: PetWindow, controller: PetController, config: ConfigManager):
        super().__init__()
        self._pet, self._controller, self._config = pet, controller, config

        self._walk_timer = QTimer(self);
        self._walk_timer.setSingleShot(True);
        self._walk_timer.timeout.connect(self._try_walk)
        self._face_timer = QTimer(self);
        self._face_timer.setSingleShot(True);
        self._face_timer.timeout.connect(self._try_face)

        # 新增：备用待机动画的定时器
        self._idle_alt_timer = QTimer(self);
        self._idle_alt_timer.setSingleShot(True);
        self._idle_alt_timer.timeout.connect(self._try_play_alt_idle)

        self._move_anim = QVariantAnimation(self);
        self._move_anim.setEasingCurve(QEasingCurve.Linear)
        self._move_anim.valueChanged.connect(self._on_move)
        self._move_anim.finished.connect(self._on_walk_done)
        self._walking = False

        self._binder = ConfigBinder(config, self)
        self._binder.bind(["behavior.walk.enabled", "behavior.walk.min_interval_s", "behavior.walk.max_interval_s"],
                          self._on_walk_cfg)
        self._binder.bind(["behavior.facing.turn_min_s", "behavior.facing.turn_max_s"], self._on_face_cfg)

    def _on_walk_cfg(self, key):
        if not self._config.get("behavior.walk.enabled", True):
            self._walk_timer.stop()
            if self._walking: self._abort_walk("开关关闭")
            return
        self._schedule_walk()

    def _on_face_cfg(self, key):
        self._schedule_face()

    def start(self):
        self._schedule_walk()
        self._schedule_face()
        self._schedule_alt_idle()

    # ========== 散步逻辑 ==========
    def _schedule_walk(self):
        if not self._config.get("behavior.walk.enabled", True): return
        lo = float(self._config.get("behavior.walk.min_interval_s", 25))
        hi = float(self._config.get("behavior.walk.max_interval_s", 70))
        self._walk_timer.start(int(random.uniform(lo, max(lo, hi)) * 1000))

    def _try_walk(self):
        if not self._config.get("behavior.walk.enabled",
                                True) or self._walking or self._controller.current_action != "idle" or not self._controller.has(
                self.WALK_ACTION):
            self._schedule_walk()
            return
        min_x, max_x = self._pet.walk_x_bounds()
        cur_x = self._pet.x()
        dist = random.randint(int(self._config.get("behavior.walk.min_distance", 120)),
                              int(self._config.get("behavior.walk.max_distance", 380)))
        direction = random.choice((-1, 1))
        if direction == -1 and cur_x - dist < min_x:
            direction = 1
        elif direction == 1 and cur_x + dist > max_x:
            direction = -1
        target_x = max(min_x, min(max_x, cur_x + direction * dist))
        if abs(target_x - cur_x) < 20:
            self._schedule_walk()
            return

        self._pet.set_facing("left" if direction == -1 else "right")
        self._walking = True
        self._controller.play(self.WALK_ACTION, loop=True)
        speed = max(10, int(self._config.get("behavior.walk.speed_px_per_s", 80)))
        dur = max(200, int(abs(target_x - cur_x) / speed * 1000))
        self._move_anim.stop()
        self._move_anim.setDuration(dur)
        self._move_anim.setStartValue(cur_x)
        self._move_anim.setEndValue(target_x)
        self._move_anim.start()

    def _on_move(self, val):
        if self._walking: self._pet.move(int(val), self._pet.y())

    def _on_walk_done(self):
        if not self._walking: return
        self._walking = False
        self._controller.play_idle()
        self._schedule_walk()

    def _abort_walk(self, reason):
        self._move_anim.stop()
        self._walking = False
        self._controller.play_idle()
        self._schedule_walk()

    # ========== 随机朝向 ==========
    def _schedule_face(self):
        lo = float(self._config.get("behavior.facing.turn_min_s", 8))
        hi = float(self._config.get("behavior.facing.turn_max_s", 20))
        self._face_timer.start(int(random.uniform(lo, max(lo, hi)) * 1000))

    def _try_face(self):
        self._schedule_face()
        if self._walking or self._controller.current_action != "idle": return
        if random.random() < float(self._config.get("behavior.facing.turn_probability", 0.5)):
            self._pet.toggle_facing()

    # ========== 新增：备用待机动画轮换 ==========
    def _schedule_alt_idle(self):
        # 默认每 40~90 秒尝试一次切换备用待机
        self._idle_alt_timer.start(random.randint(40, 90) * 1000)

    def _try_play_alt_idle(self):
        self._schedule_alt_idle()  # 先预约下一次

        # 只有在主 idle 状态下才切（走路或点击时不行）
        if self._controller.current_action != "idle" or self._walking:
            return

        # 寻找所有备用待机动作（名字是 idle_xxx，且不是主 idle）
        all_actions = self._controller.available_actions()
        alt_actions = [a for a in all_actions if a.startswith("idle_") and a != "idle"]

        # 【核心需求】：如果没有备用动作，直接 return 跳过，什么都不做
        if not alt_actions:
            return

        # 如果有，随机挑一个播放一次（loop=False）
        target = random.choice(alt_actions)
        print(f"[wander] 播放备用待机动作：{target}")
        # 播完后，controller 的 _on_finished 会自动切回主 idle
        self._controller.play(target, loop=False)