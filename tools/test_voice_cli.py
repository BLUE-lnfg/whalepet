import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app.constants import APP_NAME, CONFIG_FILE, PROFILES_DIR, ensure_user_dirs
from app.config.manager import ConfigManager
from app.services.audio import VoicePlayer
from app.animation.controller import PetController
from app.ui.pet_window import PetWindow
from app.behavior.voice_behavior import VoiceBehavior

TEST_DURATION_S = 60
FAST_MIN_S = 5
FAST_MAX_S = 8


def main():
    ensure_user_dirs()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME + "-CLI-Test")
    app.setQuitOnLastWindowClosed(False)

    config = ConfigManager(CONFIG_FILE)

    # 语音开关强制打开（测试用，不改 config.json）
    if not config.get("voice.enabled", True):
        print("!!! config.json 里 voice.enabled 是 false，本次测试强制开启（不写回文件）")
        config._data.setdefault("voice", {})["enabled"] = True

    window = PetWindow(config)
    # 不调用 show()，不需要显示桌宠

    cache_root = PROFILES_DIR / "default" / ".cache" / "actions"
    controller = PetController(cache_root)
    # 用屏幕 dpr 加载和主程序一致
    controller.load_all(window.devicePixelRatioF())
    window.set_controller(controller)
    if controller.has("idle"):
        controller.play_idle()

    voice = VoicePlayer()
    vb = VoiceBehavior(window, controller, config, voice)

    # 加速 idle 定时器（只改内存，不写 config.json）
    config._data.setdefault("voice", {})
    config._data["voice"]["idle_min_interval_s"] = FAST_MIN_S
    config._data["voice"]["idle_max_interval_s"] = FAST_MAX_S

    # 记录播放历史
    played: list[str] = []

    def on_played(path: str):
        name = Path(path).name
        played.append(path)
        print(f"[{len(played):>2}] +{elapsed_ms():>5}ms  idle 播放：{name}")

    voice.played.connect(on_played)

    # 计时器
    from PySide6.QtCore import QElapsedTimer
    elapsed = QElapsedTimer()
    elapsed.start()

    def elapsed_ms() -> int:
        return elapsed.elapsed()

    # 启动 idle 调度
    vb._schedule_idle()

    print("=" * 60)
    print(f"开始 {TEST_DURATION_S} 秒自动验证")
    print(f"闲置间隔已加速到 {FAST_MIN_S}–{FAST_MAX_S} 秒（只改内存）")
    print(f"语音开关：{vb.debug_info()['enabled']}  语言：{vb.debug_info()['language']}")
    print(f"闲置池素材：{vb.debug_info()['counts']['idle']} 个")
    print("=" * 60)

    QTimer.singleShot(TEST_DURATION_S * 1000, app.quit)
    app.exec()

    # ===== 结论 =====
    print()
    print("=" * 60)
    print("验证结果")
    print("=" * 60)
    total = len(played)
    unique = set(played)
    consecutive_repeats = sum(
        1 for i in range(1, len(played)) if played[i] == played[i - 1]
    )

    print(f"总触发次数：      {total}")
    print(f"去重后不同文件：  {len(unique)}")
    print(f"连续重复次数：    {consecutive_repeats}（应为 0）")
    print()

    if total == 0:
        print("✗ 一次都没触发")
        print("  可能原因：")
        print("    1. 闲置池目录里没有 wav")
        print("    2. controller.current_action 一直是 idle？不该发生，检查 clip 是否加载")
        print("    3. VoiceBehavior.start() 后没有正确调度 idle 定时器")
        sys.exit(1)

    if consecutive_repeats > 0:
        print(f"✗ 出现了 {consecutive_repeats} 次连续重复，不重复逻辑有 bug")
        sys.exit(2)

    if len(unique) == 1 and total > 1:
        print(f"⚠ 闲置池只有 1 个文件，重复是正常的")
        print("✓ 定时器链路正常工作")
        sys.exit(0)

    print("✓ 随机语音触发链路正常")
    print("✓ 不连续重复逻辑正常")
    sys.exit(0)


if __name__ == "__main__":
    main()