import sys
import traceback
from pathlib import Path

print("[1] 脚本启动")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
print(f"[2] ROOT = {ROOT}")

try:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    print("[3] PySide6 导入 OK")
except Exception:
    traceback.print_exc()
    sys.exit(1)

try:
    from app.constants import APP_NAME, CONFIG_FILE, PROFILES_DIR, ensure_user_dirs
    print("[4] app.constants 导入 OK")
except Exception:
    traceback.print_exc()
    sys.exit(1)

try:
    from app.config.manager import ConfigManager
    print("[5] ConfigManager 导入 OK")
except Exception:
    traceback.print_exc()
    sys.exit(1)

try:
    from app.ui.pet_window import PetWindow
    print("[6] PetWindow 导入 OK")
except Exception:
    traceback.print_exc()
    sys.exit(1)

try:
    from app.services.audio import VoicePlayer
    print("[7] VoicePlayer 导入 OK")
except Exception:
    traceback.print_exc()
    sys.exit(1)

try:
    from app.animation.controller import PetController
    print("[8] PetController 导入 OK")
except Exception:
    traceback.print_exc()
    sys.exit(1)

try:
    from app.behavior.voice_behavior import VoiceBehavior
    print("[9] VoiceBehavior 导入 OK")
except Exception:
    traceback.print_exc()
    sys.exit(1)

# 关键检查
if not hasattr(VoiceBehavior, "debug_info"):
    print("!!! VoiceBehavior 没有 debug_info 方法 —— voice_behavior.py 是旧版！")
    print("!!! 请先替换 app/behavior/voice_behavior.py 为最新版")
    sys.exit(2)
print("[10] VoiceBehavior 有 debug_info 方法 OK")

ensure_user_dirs()
app = QApplication(sys.argv)
print("[11] QApplication 创建 OK")

config = ConfigManager(CONFIG_FILE)
print(f"[12] ConfigManager OK，现有配置：{config._data}")

window = PetWindow(config)
print("[13] PetWindow 创建 OK")

cache_root = PROFILES_DIR / "default" / ".cache" / "actions"
controller = PetController(cache_root)
controller.load_all(window.devicePixelRatioF())
print("[14] PetController 加载 OK")

window.set_controller(controller)
if controller.has("idle"):
    controller.play_idle()
window.show()
print("[15] 桌宠窗口显示")

voice = VoicePlayer()
voice_behavior = VoiceBehavior(window, controller, config, voice)
print("[16] VoiceBehavior 创建 OK")

try:
    info = voice_behavior.debug_info()
    print(f"[17] debug_info OK：")
    for k, v in info.items():
        print(f"       {k} = {v}")
except Exception:
    traceback.print_exc()
    print("[17] debug_info 失败")

# 5 秒后退出
QTimer.singleShot(5000, app.quit)
print("[18] 进入事件循环，5 秒后自动退出")
app.exec()
print("[19] 正常退出")