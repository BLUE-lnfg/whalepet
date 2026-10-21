import sys
import winreg
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "WhalePet"


def get_launch_command() -> str:
    """当前程序的启动命令。
    开发模式：python.exe + main.py 的绝对路径
    打包后：exe 的绝对路径
    """
    exe = Path(sys.executable)
    if getattr(sys, "frozen", False):
        return f'"{exe}"'
    project_root = Path(__file__).resolve().parent.parent.parent
    main_py = project_root / "main.py"
    return f'"{exe}" "{main_py}"'


def is_registered() -> bool:
    """只看注册项是否存在，不比较内容。用于设置面板复选框状态。"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, APP_REG_NAME)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def is_up_to_date() -> bool:
    """注册项存在且值等于当前期望的启动命令。"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, APP_REG_NAME)
        return value == get_launch_command()
    except FileNotFoundError:
        return False
    except OSError:
        return False


def enable() -> bool:
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, get_launch_command())
        return True
    except OSError as e:
        print(f"[autostart] 启用失败：{e}")
        return False


def disable() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_REG_NAME)
        return True
    except FileNotFoundError:
        return True
    except OSError as e:
        print(f"[autostart] 禁用失败：{e}")
        return False


def sync_if_needed() -> bool:
    """启动时自检：注册项存在但路径过期 → 更新为新路径。
    返回 True 表示做了修正。绿色版被移动后，下一次启动即自动修好。
    """
    if not is_registered():
        return False
    if is_up_to_date():
        return False
    return enable()