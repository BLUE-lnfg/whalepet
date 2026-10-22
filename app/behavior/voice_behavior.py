import random
from datetime import datetime, timezone, timedelta
from pathlib import Path
from PySide6.QtCore import QObject, QTimer
from app.animation.controller import PetController
from app.config.binder import ConfigBinder
from app.config.manager import ConfigManager
from app.services.audio import VoicePlayer
from app.services.profile_manager import ProfileManager
from app.ui.pet_window import PetWindow

BEIJING_TZ = timezone(timedelta(hours=8))


class VoiceBehavior(QObject):
    def __init__(self, pet: PetWindow, ctrl: PetController, config: ConfigManager, voice: VoicePlayer,
                 pm: ProfileManager):
        super().__init__()
        self._pet, self._ctrl, self._config, self._voice, self._pm = pet, ctrl, config, voice, pm
        self._idle_timer = QTimer(self);
        self._idle_timer.setSingleShot(True);
        self._idle_timer.timeout.connect(self._play_idle)
        self._no_inter_timer = QTimer(self);
        self._no_inter_timer.setSingleShot(True);
        self._no_inter_timer.timeout.connect(self._play_no_inter)
        self._clock_timer = QTimer(self);
        self._clock_timer.setInterval(60000);
        self._clock_timer.timeout.connect(self._check_late)
        self._last_date = str(self._config.get("voice.last_late_night_date", "") or "") or None

        self._pet.clicked.connect(self._on_clicked)
        self._pet.drag_started.connect(self._on_user_interact)
        self._pm.profile_changed.connect(self._on_profile_switched)

        self._binder = ConfigBinder(config, self)
        self._binder.bind(["voice.enabled", "voice.idle_min_interval_s", "voice.idle_max_interval_s"],
                          self._on_idle_cfg)
        self._binder.bind("voice.no_interaction_timeout_s", self._on_no_inter_cfg)
        self._binder.bind(["voice.late_night_enabled", "voice.late_night_time"], self._on_late_cfg)

    def _voice_root(self) -> Path:
        return self._pm.current_voice_dir()

    def _on_profile_switched(self, name):
        print(f"[voice] 切换角色为 {name}，重置语音调度")
        self._voice.stop_all()
        self._schedule_idle()
        self._reset_no_inter()

    def _on_idle_cfg(self, key):
        print(f"[voice] {key} 变化，重新调度闲置语音")
        if self._config.get("voice.enabled", True):
            self._schedule_idle()
        else:
            self._idle_timer.stop()

    def _on_no_inter_cfg(self, key):
        print("[voice] 无交互阈值变化，重新调度")
        self._reset_no_inter()

    def _on_late_cfg(self, key):
        self._check_late()

    def start(self):
        print(
            f"[voice] 启动完成，语言={self._config.get('voice.language', 'zh-CN')}，语音开关={self._config.get('voice.enabled', True)}")
        self._schedule_idle()
        self._reset_no_inter()
        self._clock_timer.start()
        self._check_late()

    def _schedule_idle(self):
        lo, hi = float(self._config.get("voice.idle_min_interval_s", 300)), float(
            self._config.get("voice.idle_max_interval_s", 3600))
        self._idle_timer.start(int(random.uniform(lo, max(lo, hi)) * 1000))

    def _reset_no_inter(self):
        timeout = float(self._config.get("voice.no_interaction_timeout_s", 900))
        self._no_inter_timer.start(int(timeout * 1000))

    def _on_user_interact(self):
        self._reset_no_inter()

    def _on_clicked(self):
        print("[voice] 收到点击信号")
        self._on_user_interact()
        if not self._config.get("voice.click_enabled", True): return
        lang = str(self._config.get("voice.language", "zh-CN"))
        click_dir = self._voice_root() / lang / "click"
        files = list(click_dir.glob("*.wav")) if click_dir.exists() else list((self._voice_root() / lang).glob("*.wav"))
        if files:
            target = random.choice(files)
            print(f"[voice] 播放点击语音：{target.name}")
            self._voice.play(target, interrupt=True)

    def _play_idle(self):
        self._schedule_idle()
        if not self._config.get("voice.enabled",
                                True) or self._pet.is_dragging or self._ctrl.current_action != "idle": return
        lang = str(self._config.get("voice.language", "zh-CN"))
        files = list((self._voice_root() / lang).glob("*.wav"))
        if files:
            target = random.choice(files)
            print(f"[voice] 播放闲置语音：{target.name}")
            self._voice.play(target)

    def _play_no_inter(self):
        if self._pet.is_dragging: return
        lang = str(self._config.get("voice.language", "zh-CN"))
        files = list((self._voice_root() / lang / "special" / "no_interaction").glob("*.wav"))
        if files:
            target = random.choice(files)
            print(f"[voice] 播放无交互语音：{target.name}")
            self._voice.play(target)

    def _check_late(self):
        if not self._config.get("voice.enabled", True) or not self._config.get("voice.late_night_enabled", True): return
        now = datetime.now(BEIJING_TZ)
        today = now.strftime("%Y-%m-%d")
        if self._last_date == today: return
        t_str = str(self._config.get("voice.late_night_time", "22:30"))
        try:
            h, m = map(int, t_str.split(":"))
            if (now.hour, now.minute) < (h, m): return
        except Exception:
            return
        lang = str(self._config.get("voice.language", "zh-CN"))
        files = list((self._voice_root() / lang / "special" / "late_night").glob("*.wav"))
        if files:
            target = random.choice(files)
            print(f"[voice] 播放熬夜语音：{target.name}")
            self._last_date = today
            self._config.set("voice.last_late_night_date", today)
            self._voice.play(target)

    # 测试面板接口
    def debug_info(self):
        return {"enabled": self._config.get("voice.enabled", True),
                "language": self._config.get("voice.language", "zh-CN"), "click_enabled": True,
                "late_night_enabled": True, "late_night_time": "22:30", "idle_interval": (300, 3600),
                "no_interaction_timeout_s": 900,
                "counts": {"idle": 0, "click": 0, "no_interaction": 0, "late_night": 0}}