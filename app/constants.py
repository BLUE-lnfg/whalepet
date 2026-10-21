import os
import sys
from pathlib import Path

APP_NAME = "WhalePet"


def _resolve_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后：exe 所在目录
        return Path(sys.executable).resolve().parent
    # 开发模式：项目根目录（app/constants.py 的上两级）
    return Path(__file__).resolve().parent.parent


APP_DIR = _resolve_app_dir()

USER_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / APP_NAME
LOG_DIR = USER_DIR / "logs"
CONFIG_FILE = USER_DIR / "config.json"


def _resolve_profiles_dir() -> Path:
    # 优先级：程序根目录下的 profiles → PyInstaller _internal 里打包的那份
    candidates = [APP_DIR / "profiles"]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "profiles")
    for c in candidates:
        if c.is_dir():
            return c
    return candidates[0]


PROFILES_DIR = _resolve_profiles_dir()


def ensure_user_dirs():
    LOG_DIR.mkdir(parents=True, exist_ok=True)