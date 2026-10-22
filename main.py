import sys
from PySide6.QtWidgets import QApplication
from app.constants import APP_NAME, CONFIG_FILE, ensure_user_dirs
from app.services.logger import install_logger
from app.config.manager import ConfigManager
from app.services.profile_manager import ProfileManager
from app.ui.pet_window import PetWindow
from app.services.tray import PetTray
from app.services.audio import VoicePlayer
from app.services.theme import ThemeWatcher
from app.animation.controller import PetController
from app.behavior.wander import WanderManager
from app.behavior.voice_behavior import VoiceBehavior
from app.ui.settings_dialog import SettingsDialog


def main():
    ensure_user_dirs()
    install_logger()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    ThemeWatcher(app)

    config = ConfigManager(CONFIG_FILE)
    pm = ProfileManager(config)

    window = PetWindow(config)
    controller = PetController(pm.current_actions_cache_dir())
    controller.load_all(window.devicePixelRatioF())
    window.set_controller(controller)
    controller.play_idle()
    window.show()

    wander = WanderManager(window, controller, config)
    wander.start()

    voice = VoicePlayer()
    vb = VoiceBehavior(window, controller, config, voice, pm)
    vb.start()

    settings = SettingsDialog(config, vb, window, pm)
    window.settings_requested.connect(settings.show_and_raise)

    tray = PetTray(app, window)
    tray.settings_requested.connect(settings.show_and_raise)
    tray.show()

    # ========== 修复后的动态热切换 ==========
    def on_profile_changed(new_name: str):
        print(f"\n[main] 切换角色 -> {new_name}，执行重载...")

        # 1. 彻底清空画面和播放器
        controller.clear()
        window.clear_display()
        wander._walk_timer.stop()
        wander._face_timer.stop()

        # 2. 更换控制器路径并重载
        controller._cache_root = pm.current_actions_cache_dir()
        controller.load_all(window.devicePixelRatioF())

        # 3. 强制重绘并恢复散步/翻面调度
        if controller.has("idle"):
            controller.play_idle()
        wander._schedule_walk()
        wander._schedule_face()
        print("[main] 重载完成")

    pm.profile_changed.connect(on_profile_changed)
    # ======================================

    sys.exit(app.exec())


if __name__ == "__main__":
    main()