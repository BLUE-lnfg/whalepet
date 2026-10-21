import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.assets.converter import import_action
from app.constants import PROFILES_DIR

# ===== 导入参数，想更清晰/更省内存就改这两个 =====
TARGET_LONGEST = 480   # 最长边像素，480 覆盖到 150% 系统缩放
TARGET_FPS = 60        # 目标帧率
# =================================================


def main():
    actions_dir = PROFILES_DIR / "default" / "assets" / "actions"
    cache_root = PROFILES_DIR / "default" / ".cache" / "actions"

    if not actions_dir.exists():
        print(f"找不到动作目录：{actions_dir}")
        return

    force = "--force" in sys.argv
    if force:
        print("强制重新导入所有动作")

    total = 0
    for action_dir in sorted(actions_dir.iterdir()):
        if not action_dir.is_dir():
            continue
        print(f"\n[{action_dir.name}]")
        m = import_action(
            action_dir,
            cache_root / action_dir.name,
            TARGET_LONGEST,
            TARGET_FPS,
            force=force,
        )
        if m is None:
            print("  跳过：目录内没有 .gif / .webm")
        else:
            total += 1
            print(
                f"  {m.src_frames} 帧 @ {m.src_fps}fps  →  "
                f"{m.frame_count} 帧 @ {m.out_fps}fps, "
                f"{m.out_size[0]}x{m.out_size[1]}, 时长 {m.duration}s"
            )
    print(f"\n共导入 {total} 个动作")


if __name__ == "__main__":
    main()