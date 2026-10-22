import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.assets.converter import import_action
from app.constants import BUILTIN_PROFILES_DIR, USER_PROFILES_DIR, CACHE_ROOT

TARGET_LONGEST = 480
TARGET_FPS = 60


def find_profiles() -> list[tuple[str, Path]]:
    result = {}
    for base in (BUILTIN_PROFILES_DIR, USER_PROFILES_DIR):
        if not base.is_dir(): continue
        for d in base.iterdir():
            if d.is_dir() and (d / "assets").is_dir():
                result[d.name] = d
    return sorted(result.items())


def main():
    args = sys.argv[1:]
    force = "--force" in args
    target_name = None
    for a in args:
        if a.startswith("--profile="):
            target_name = a.split("=", 1)[1]

    profiles = find_profiles()
    if target_name:
        profiles = [(n, p) for n, p in profiles if n == target_name]

    total_actions = 0
    for name, profile_dir in profiles:
        print(f"\n========== profile: {name} ==========")
        actions_dir = profile_dir / "assets" / "actions"
        cache_root = CACHE_ROOT / name / "actions"

        if not actions_dir.is_dir(): continue

        for action_dir in sorted(actions_dir.iterdir()):
            if not action_dir.is_dir(): continue
            print(f"\n[{action_dir.name}]")
            m = import_action(action_dir, cache_root / action_dir.name, TARGET_LONGEST, TARGET_FPS, force=force)
            if m: total_actions += 1

    print(f"\n共导入 {total_actions} 个动作，缓存目录：{CACHE_ROOT}")


if __name__ == "__main__":
    main()