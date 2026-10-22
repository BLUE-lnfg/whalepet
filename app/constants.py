import os
import sys
from pathlib import Path

APP_NAME = "WhalePet"


def _resolve_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent

APP_DIR = _resolve_app_dir()

# 用户数据目录 (%APPDATA%\WhalePet)
USER_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / APP_NAME
LOG_DIR = USER_DIR / "logs"
CONFIG_FILE = USER_DIR / "config.json"

# 用户自建的形象目录（用户自己往这里丢 zip 或文件夹）
USER_PROFILES_DIR = USER_DIR / "profiles"

# 所有 profile 的帧缓存（统一放在这里，不放在安装目录，避免权限问题）
CACHE_ROOT = USER_DIR / "cache"

def _resolve_builtin_profiles_dir() -> Path:
    """内置形象目录"""
    candidates = [APP_DIR / "profiles"]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "profiles")
    for c in candidates:
        if c.is_dir():
            return c
    return candidates[0]

BUILTIN_PROFILES_DIR = _resolve_builtin_profiles_dir()


def ensure_user_dirs():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    USER_PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)