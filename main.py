import sys
from PySide6.QtWidgets import QApplication

from app.constants import APP_NAME, CONFIG_FILE, PROFILES_DIR, ensure_user_dirs
from app.services.logger import install_logger, shutdown_logger
from app.config.manager import ConfigManager
from app.ui.pet_window import PetWindow
from app.services.tray import PetTray
from app.services.audio import VoicePlayer
from app.services.theme import ThemeWatcher
from app.services import autostart
from app.animation.controller import PetController
from app.behavior.wander import WanderManager
from app.behavior.voice_behavior import VoiceBehavior
from app.ui.settings_dialog import SettingsDialog


def main():
    ensure_user_dirs()

    # 尽早安装日志系统，后续所有 print 都会写入文件 + 日志窗口
    log_path = install_logger()
    if log_path is not None:
        print(f"[main] 日志文件：{log_path}")

    # 开机自启路径自愈
    if autostart.sync_if_needed():
        print("[autostart] 注册表路径已过期，已自动更新为新路径")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)

    theme = ThemeWatcher(app)

    config = ConfigManager(CONFIG_FILE)
    window = PetWindow(config)

    cache_root = PROFILES_DIR / "default" / ".cache" / "actions"
    controller = PetController(cache_root)
    controller.load_all(window.devicePixelRatioF())
    window.set_controller(controller)
    if controller.has("idle"):
        controller.play_idle()

    window.show()

    wander = WanderManager(window, controller, config)
    wander.start()

    voice = VoicePlayer()
    vb = VoiceBehavior(window, controller, config, voice)
    vb.start()

    settings = SettingsDialog(config, vb, window)

    window.settings_requested.connect(settings.show_and_raise)

    tray = PetTray(app, window)
    tray.settings_requested.connect(settings.show_and_raise)
    tray.show()

    exit_code = app.exec()
    shutdown_logger()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()