import sys, winreg
from pathlib import Path

def get_launch_command() -> str:
    exe = Path(sys.executable)
    if getattr(sys, "frozen", False): return f'"{exe}"'
    return f'"{exe}" "{Path(__file__).parent.parent.parent / "main.py"}"'

def is_registered() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
            winreg.QueryValueEx(key, "WhalePet")
            return True
    except FileNotFoundError: return False
    except OSError: return False

def enable() -> bool:
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
            winreg.SetValueEx(key, "WhalePet", 0, winreg.REG_SZ, get_launch_command())
        return True
    except OSError: return False

def disable() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, "WhalePet")
        return True
    except FileNotFoundError: return True
    except OSError: return False