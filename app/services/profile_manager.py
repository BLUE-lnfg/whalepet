import json
from dataclasses import dataclass
from pathlib import Path
from PySide6.QtCore import QObject, Signal
from app.config.manager import ConfigManager
from app.constants import BUILTIN_PROFILES_DIR, USER_PROFILES_DIR, CACHE_ROOT

DEFAULT_PROFILE_NAME = "default"


@dataclass
class ProfileInfo:
    name: str  # 目录名
    path: Path  # 根目录
    is_builtin: bool  # 是否内置
    display_name: str  # 显示名 (profile.json 里的 name)
    author: str
    version: str


class ProfileManager(QObject):
    profile_changed = Signal(str)  # 切换角色时发出信号

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config

        # 检查配置中的激活角色是否还存在，不存在则回退到 default
        configured = str(config.get("profile.active", DEFAULT_PROFILE_NAME))
        if not self._profile_exists(configured):
            configured = DEFAULT_PROFILE_NAME
        self._active = configured

    def _scan_dir(self, base: Path, is_builtin: bool) -> dict[str, ProfileInfo]:
        result = {}
        if not base.is_dir(): return result
        for d in base.iterdir():
            if d.is_dir() and (d / "assets").is_dir():
                display_name, author, version = d.name, "", ""
                p_json = d / "profile.json"
                if p_json.exists():
                    try:
                        data = json.loads(p_json.read_text(encoding="utf-8"))
                        display_name = data.get("name", d.name)
                        author = data.get("author", "")
                        version = data.get("version", "")
                    except Exception:
                        pass
                result[d.name] = ProfileInfo(d.name, d, is_builtin, display_name, author, version)
        return result

    def _all_profiles(self) -> dict[str, ProfileInfo]:
        # 用户目录优先，同名覆盖内置
        merged = {}
        for name, info in self._scan_dir(BUILTIN_PROFILES_DIR, True).items():
            merged[name] = info
        for name, info in self._scan_dir(USER_PROFILES_DIR, False).items():
            merged[name] = info
        return merged

    def _profile_exists(self, name: str) -> bool:
        return name in self._all_profiles()

    def list_profiles(self) -> list[ProfileInfo]:
        profiles = list(self._all_profiles().values())
        profiles.sort(key=lambda i: (not i.is_builtin, i.name.lower()))
        return profiles

    def active_name(self) -> str:
        return self._active

    def active_info(self) -> ProfileInfo | None:
        return self._all_profiles().get(self._active)

    def current_profile_dir(self) -> Path:
        info = self.active_info()
        return info.path if info else BUILTIN_PROFILES_DIR / DEFAULT_PROFILE_NAME

    def current_actions_cache_dir(self) -> Path:
        return CACHE_ROOT / self._active / "actions"

    def current_voice_dir(self) -> Path:
        return self.current_profile_dir() / "assets" / "voice"

    def switch_to(self, name: str) -> bool:
        if name == self._active or not self._profile_exists(name):
            return False
        self._active = name
        self._config.set("profile.active", name)
        self.profile_changed.emit(name)
        return True