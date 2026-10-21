import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PySide6.QtCore import QObject, QTimer

from app.animation.controller import PetController
from app.config.manager import ConfigManager
from app.constants import PROFILES_DIR
from app.services.audio import VoicePlayer
from app.ui.pet_window import PetWindow

VOICE_ROOT = PROFILES_DIR / "default" / "assets" / "voice"
BEIJING_TZ = timezone(timedelta(hours=8))

CATEGORY_SUBDIR = {
    "idle": "",
    "click": "click",
    "no_interaction": "special/no_interaction",
    "late_night": "special/late_night",
}


class VoiceBehavior(QObject):
    def __init__(self, pet: PetWindow, controller: PetController,
                 config: ConfigManager, voice: VoicePlayer):
        super().__init__()
        self._pet = pet
        self._controller = controller
        self._config = config
        self._voice = voice

        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.timeout.connect(self._try_play_idle)

        self._no_interaction_timer = QTimer(self)
        self._no_interaction_timer.setSingleShot(True)
        self._no_interaction_timer.timeout.connect(self._try_play_no_interaction)
        self._no_interaction_fired = False

        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(60_000)
        self._clock_timer.timeout.connect(self._check_late_night)
        self._last_late_night_date = str(
            self._config.get("voice.last_late_night_date", "") or ""
        ) or None

        self._last_played: dict[str, Path] = {}

        self._pet.clicked.connect(self._on_clicked)
        self._pet.drag_started.connect(self._on_user_interaction)
        print("[voice] VoiceBehavior 初始化完成，clicked 信号已连接")

    def start(self):
        self._schedule_idle()
        self._reset_no_interaction_timer()
        self._clock_timer.start()
        self._check_late_night()
        print(f"[voice] 启动完成，语言={self._lang()}，语音开关={self._enabled()}")

    # ---------- 配置 ----------

    def _cfg(self, key, default):
        return self._config.get(f"voice.{key}", default)

    def _enabled(self) -> bool:
        return bool(self._cfg("enabled", True))

    def _lang(self) -> str:
        return str(self._cfg("language", "zh-CN"))

    # ---------- 挑选（不连续重复）----------

    def _pick_no_repeat(self, files: list[Path], category: str) -> Path | None:
        if not files:
            return None
        if len(files) == 1:
            chosen = files[0]
        else:
            last = self._last_played.get(category)
            pool = [f for f in files if f != last] if last is not None else files
            if not pool:
                pool = files
            chosen = random.choice(pool)
        self._last_played[category] = chosen
        return chosen

    # ---------- 统一触发入口 ----------

    def _trigger_category(self, category: str, *, play: bool = True,
                          interrupt: bool = False) -> dict:
        """
        返回：{"ok": bool, "reason": str, "file": Path|None, "source": str}
        play=True 时直接调用播放器。
        """
        if category not in CATEGORY_SUBDIR:
            return {"ok": False, "reason": f"未知类别：{category}",
                    "file": None, "source": ""}

        if not self._enabled():
            return {"ok": False, "reason": "语音总开关关闭",
                    "file": None, "source": ""}

        lang_dir = VOICE_ROOT / self._lang()

        if category == "click":
            click_files = self._list_files(lang_dir, "click")
            if click_files:
                files = click_files
                record_key = "click"
                source = "专用"
            else:
                files = self._list_files(lang_dir, "")
                record_key = "click_fallback"
                source = "回退闲置池"
        else:
            subdir = CATEGORY_SUBDIR[category]
            files = self._list_files(lang_dir, subdir)
            record_key = category
            source = "专用"

        if not files:
            subdir = CATEGORY_SUBDIR.get(category, "")
            target_dir = lang_dir / subdir if subdir else lang_dir
            return {"ok": False, "reason": f"{target_dir} 下没有 wav",
                    "file": None, "source": ""}

        target = self._pick_no_repeat(files, category=record_key)
        if target is None:
            return {"ok": False, "reason": "无可用文件",
                    "file": None, "source": ""}

        if play:
            self._voice.play(target, interrupt=interrupt)
            print(f"[voice] 播放 {category}（{source}）：{target.name}")

        return {"ok": True, "reason": "", "file": target, "source": source}

    # ---------- 定时器回调 ----------

    def _try_play_idle(self):
        self._schedule_idle()
        if not self._is_idle():
            return
        self._trigger_category("idle")

    def _is_idle(self) -> bool:
        if self._pet.is_dragging:
            return False
        if self._controller.current_action != "idle":
            return False
        return True

    def _on_clicked(self):
        print("[voice] 收到点击信号")
        self._on_user_interaction()
        if not bool(self._cfg("click_enabled", True)):
            print("[voice] 点击跳过：click_enabled = false")
            return
        self._trigger_category("click", interrupt=True)

    def _on_user_interaction(self):
        self._no_interaction_fired = False
        self._reset_no_interaction_timer()

    def _reset_no_interaction_timer(self):
        timeout_s = float(self._cfg("no_interaction_timeout_s", 900))
        if timeout_s <= 0:
            return
        self._no_interaction_timer.start(int(timeout_s * 1000))

    def _try_play_no_interaction(self):
        if self._no_interaction_fired:
            return
        if self._pet.is_dragging:
            return
        files = self._list_files(
            VOICE_ROOT / self._lang(), "special/no_interaction"
        )
        if not files:
            return
        result = self._trigger_category("no_interaction")
        if result["ok"]:
            self._no_interaction_fired = True

    def _check_late_night(self):
        if not bool(self._cfg("late_night_enabled", True)):
            return
        now = datetime.now(BEIJING_TZ)
        today = now.strftime("%Y-%m-%d")
        if self._last_late_night_date == today:
            return
        threshold = self._parse_hhmm(str(self._cfg("late_night_time", "22:30")))
        if threshold is None:
            return
        if (now.hour, now.minute) < threshold:
            return
        files = self._list_files(
            VOICE_ROOT / self._lang(), "special/late_night"
        )
        if not files:
            return
        result = self._trigger_category("late_night")
        if result["ok"]:
            self._last_late_night_date = today
            self._config.set("voice.last_late_night_date", today)

    def _schedule_idle(self):
        lo = float(self._cfg("idle_min_interval_s", 300))
        hi = float(self._cfg("idle_max_interval_s", 3600))
        if hi < lo:
            hi = lo
        self._idle_timer.start(int(random.uniform(lo, hi) * 1000))

    # ---------- 工具 ----------

    @staticmethod
    def _parse_hhmm(s: str):
        try:
            h, m = s.strip().split(":")
            h, m = int(h), int(m)
            if 0 <= h < 24 and 0 <= m < 60:
                return h, m
        except Exception:
            pass
        return None

    def _list_files(self, base: Path, subdir: str) -> list[Path]:
        folder = base / subdir if subdir else base
        if not folder.is_dir():
            return []
        return sorted(
            p for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() == ".wav"
        )

    # ---------- 调试接口（供测试工具 & M4 设置面板使用）----------

    def debug_trigger(self, category: str) -> dict:
        """手动触发指定类别，不改变熬夜/无交互的状态标记。"""
        return self._trigger_category(category, play=True)

    def debug_info(self) -> dict:
        """返回当前配置和各类别素材数量。"""
        lang = self._lang()
        lang_dir = VOICE_ROOT / lang
        counts = {
            "idle": len(self._list_files(lang_dir, "")),
            "click": len(self._list_files(lang_dir, "click")),
            "no_interaction": len(self._list_files(lang_dir, "special/no_interaction")),
            "late_night": len(self._list_files(lang_dir, "special/late_night")),
        }
        return {
            "enabled": self._enabled(),
            "language": lang,
            "click_enabled": bool(self._cfg("click_enabled", True)),
            "late_night_enabled": bool(self._cfg("late_night_enabled", True)),
            "late_night_time": str(self._cfg("late_night_time", "22:30")),
            "idle_interval": (
                self._cfg("idle_min_interval_s", 300),
                self._cfg("idle_max_interval_s", 3600),
            ),
            "no_interaction_timeout_s": self._cfg("no_interaction_timeout_s", 900),
            "counts": counts,
        }