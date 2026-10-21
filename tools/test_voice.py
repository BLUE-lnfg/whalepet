import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QUrl, QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import QSoundEffect

from app.constants import PROFILES_DIR

VOICE_ROOT = PROFILES_DIR / "default" / "assets" / "voice"


def scan():
    print(f"语音根目录：{VOICE_ROOT}")
    if not VOICE_ROOT.exists():
        print("  目录不存在！")
        return
    for lang_dir in sorted(VOICE_ROOT.iterdir()):
        if not lang_dir.is_dir():
            continue
        print(f"\n[{lang_dir.name}]")
        found_any = False
        for sub in ["", "click", "special/no_interaction", "special/late_night"]:
            folder = lang_dir / sub if sub else lang_dir
            if not folder.is_dir():
                continue
            files = sorted(p for p in folder.iterdir() if p.is_file())
            if not files:
                continue
            found_any = True
            label = sub if sub else "(根目录=闲置)"
            print(f"  {label}: {len(files)} 个文件")
            for f in files[:3]:
                print(f"    - {f.name}  ({f.stat().st_size} bytes)")
            if len(files) > 3:
                print(f"    ... 还有 {len(files) - 3} 个")
        if not found_any:
            print("  (空)")


def pick_first_wav() -> Path | None:
    for lang_dir in sorted(VOICE_ROOT.iterdir()) if VOICE_ROOT.exists() else []:
        if not lang_dir.is_dir():
            continue
        for sub in ["", "click"]:
            folder = lang_dir / sub if sub else lang_dir
            if folder.is_dir():
                wavs = sorted(p for p in folder.iterdir()
                              if p.is_file() and p.suffix.lower() == ".wav")
                if wavs:
                    return wavs[0]
    return None


def main():
    app = QApplication(sys.argv)

    print("=" * 50)
    print("1. 扫描素材")
    print("=" * 50)
    scan()

    print("\n" + "=" * 50)
    print("2. 播放测试")
    print("=" * 50)
    wav = pick_first_wav()
    if wav is None:
        print("找不到任何 .wav 文件，无法测试播放")
        return
    print(f"测试文件：{wav}")

    effect = QSoundEffect()
    effect.setVolume(1.0)
    effect.setSource(QUrl.fromLocalFile(str(wav)))

    # status 变化时打印，这是关键诊断信息
    effect.statusChanged.connect(
        lambda s: print(f"  QSoundEffect status = {s}")
    )
    effect.playingChanged.connect(
        lambda p: print(f"  playing = {p}")
    )

    def try_play():
        print(f"  当前 status = {effect.status()}")
        print(f"  isLoaded = {effect.isLoaded()}")
        print(f"  调用 play()")
        effect.play()
        QTimer.singleShot(3000, lambda: (print("  3 秒后退出"), app.quit()))

    QTimer.singleShot(800, try_play)
    app.exec()


if __name__ == "__main__":
    main()