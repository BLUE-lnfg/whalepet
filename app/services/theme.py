import winreg

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
REG_KEY = "AppsUseLightTheme"


def is_system_dark() -> bool:
    """优先用 Qt 的 colorScheme；Unknown 时回退注册表。"""
    try:
        scheme = QGuiApplication.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return True
        if scheme == Qt.ColorScheme.Light:
            return False
    except Exception:
        pass
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
            value, _ = winreg.QueryValueEx(key, REG_KEY)
            return value == 0
    except OSError:
        return False  # 其它 Windows 版本或读不到，默认浅色


def build_qss(dark: bool) -> str:
    if dark:
        bg = "#202020"
        card = "#2d2d2d"
        border = "#3d3d3d"
        text = "#e8e8e8"
        subtext = "#a0a0a0"
        input_bg = "#2d2d2d"
        input_border = "#4d4d4d"
        hover = "#383838"
    else:
        bg = "#f3f3f3"
        card = "#ffffff"
        border = "#e0e0e0"
        text = "#1a1a1a"
        subtext = "#666666"
        input_bg = "#ffffff"
        input_border = "#d0d0d0"
        hover = "#f0f0f0"

    return f"""
QWidget {{
    background-color: {bg};
    color: {text};
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 14px;
}}
QWidget#SettingsRoot {{
    background-color: {bg};
    border: 1px solid {border};
    border-radius: 8px;
}}
QWidget#TitleBar {{
    background-color: transparent;
}}
QLabel#TitleText {{
    font-size: 15px;
    font-weight: 600;
    color: {text};
}}
QPushButton#CloseBtn {{
    background: transparent;
    border: none;
    font-size: 16px;
    color: {subtext};
    padding: 4px 10px;
    border-radius: 4px;
}}
QPushButton#CloseBtn:hover {{
    background-color: #e81123;
    color: white;
}}
QListWidget {{
    background-color: transparent;
    border: none;
    outline: none;
    padding: 8px 6px;
}}
QListWidget::item {{
    padding: 10px 14px;
    border-radius: 6px;
    margin: 2px 4px;
    color: {text};
}}
QListWidget::item:selected {{
    background-color: {hover};
    color: {text};
}}
QListWidget::item:hover {{
    background-color: {hover};
}}
QScrollArea {{
    background-color: transparent;
    border: none;
}}
QGroupBox {{
    background-color: {card};
    border: 1px solid {border};
    border-radius: 8px;
    margin-top: 10px;
    padding: 18px 16px 14px 16px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: {text};
}}
QLabel {{
    background: transparent;
}}
QLabel#Hint {{
    color: {subtext};
    font-size: 12px;
}}
QCheckBox {{
    spacing: 10px;
    background: transparent;
}}
QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {input_bg};
    border: 1px solid {input_border};
    border-radius: 4px;
    padding: 5px 8px;
    min-height: 22px;
    color: {text};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {input_bg};
    border: 1px solid {input_border};
    selection-background-color: {hover};
    color: {text};
}}
QPushButton {{
    background-color: #0078d4;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 7px 18px;
}}
QPushButton:hover {{
    background-color: #106ebe;
}}
QPushButton:pressed {{
    background-color: #005a9e;
}}
QPushButton#Secondary {{
    background-color: transparent;
    color: {text};
    border: 1px solid {input_border};
}}
QPushButton#Secondary:hover {{
    background-color: {hover};
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: {input_border};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
    background: #0078d4;
}}
"""


class ThemeWatcher(QObject):
    theme_changed = Signal(bool)  # True = dark

    def __init__(self, app: QApplication, parent=None):
        super().__init__(parent)
        self._app = app
        self._current_dark: bool | None = None
        try:
            hints = QGuiApplication.styleHints()
            hints.colorSchemeChanged.connect(self._on_system_changed)
        except Exception:
            pass
        self.apply()

    def _on_system_changed(self, *_):
        self.apply()

    def apply(self):
        dark = is_system_dark()
        if dark == self._current_dark:
            return
        self._current_dark = dark
        self._app.setStyle("Fusion")
        self._app.setStyleSheet(build_qss(dark))
        self.theme_changed.emit(dark)

