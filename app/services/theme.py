import winreg
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

def is_system_dark() -> bool:
    try:
        scheme = QGuiApplication.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Dark: return True
        if scheme == Qt.ColorScheme.Light: return False
    except Exception: pass
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
            return winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 0
    except OSError: return False

def build_qss(dark: bool) -> str:
    bg = "#202020" if dark else "#f3f3f3"
    card = "#2d2d2d" if dark else "#ffffff"
    border = "#3d3d3d" if dark else "#e0e0e0"
    text = "#e8e8e8" if dark else "#1a1a1a"
    subtext = "#a0a0a0" if dark else "#666666"
    input_bg = "#2d2d2d" if dark else "#ffffff"
    input_border = "#4d4d4d" if dark else "#d0d0d0"
    hover = "#383838" if dark else "#f0f0f0"
    return f"""
    QWidget {{ background-color: {bg}; color: {text}; font-family: "Segoe UI", "Microsoft YaHei"; font-size: 14px; }}
    QWidget#SettingsRoot {{ background-color: {bg}; border: 1px solid {border}; border-radius: 8px; }}
    QWidget#TitleBar {{ background-color: transparent; }}
    QLabel#TitleText {{ font-size: 15px; font-weight: 600; }}
    QPushButton#CloseBtn {{ background: transparent; border: none; font-size: 16px; color: {subtext}; padding: 4px 10px; }}
    QPushButton#CloseBtn:hover {{ background-color: #e81123; color: white; }}
    QListWidget {{ background-color: transparent; border: none; outline: none; padding: 8px 6px; }}
    QListWidget::item {{ padding: 10px 14px; border-radius: 6px; margin: 2px 4px; }}
    QListWidget::item:selected {{ background-color: {hover}; }}
    QListWidget::item:hover {{ background-color: {hover}; }}
    QGroupBox {{ background-color: {card}; border: 1px solid {border}; border-radius: 8px; margin-top: 10px; padding: 18px 16px 14px 16px; font-weight: 600; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 14px; padding: 0 6px; }}
    QLabel#Hint {{ color: {subtext}; font-size: 12px; }}
    QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {{ background-color: {input_bg}; border: 1px solid {input_border}; border-radius: 4px; padding: 5px 8px; min-height: 22px; }}
    QPushButton {{ background-color: #0078d4; color: white; border: none; border-radius: 4px; padding: 7px 18px; }}
    QPushButton#Secondary {{ background-color: transparent; color: {text}; border: 1px solid {input_border}; }}
    """

class ThemeWatcher(QObject):
    def __init__(self, app: QApplication):
        super().__init__()
        self._app = app
        self._dark = None
        try: QGuiApplication.styleHints().colorSchemeChanged.connect(self.apply)
        except Exception: pass
        self.apply()

    def apply(self, *_):
        dark = is_system_dark()
        if dark == self._dark: return
        self._dark = dark
        self._app.setStyle("Fusion")
        self._app.setStyleSheet(build_qss(dark))