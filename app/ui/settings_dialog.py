import os
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QStackedWidget, QScrollArea, QGroupBox, QFormLayout, QLabel, QCheckBox,
    QComboBox, QSpinBox, QDoubleSpinBox, QPushButton, QLineEdit, QPlainTextEdit,
    QMessageBox
)

from app.config.manager import ConfigManager
from app.behavior.voice_behavior import VoiceBehavior
from app.ui.pet_window import PetWindow
from app.services.profile_manager import ProfileManager
from app.services import autostart
from app.services.logger import bus as log_bus
from app.constants import USER_DIR, LOG_DIR


def _card(title: str) -> tuple[QGroupBox, QFormLayout]:
    box = QGroupBox(title)
    form = QFormLayout(box)
    form.setHorizontalSpacing(24)
    form.setVerticalSpacing(12)
    return box, form


def _hint(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("Hint")
    lab.setWordWrap(True)
    return lab


class _Page(QScrollArea):
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._body = QWidget()
        self._layout = QVBoxLayout(self._body)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.addStretch()
        self.setWidget(self._body)

    def add(self, w): self._layout.insertWidget(self._layout.count() - 1, w)

    def refresh_from_config(self): pass


# ==========================================
# 新增：形象选择页
# ==========================================
class ProfilePage(_Page):
    def __init__(self, config: ConfigManager, pm: ProfileManager):
        super().__init__()
        self._pm = pm

        box, form = _card("选择桌宠形象")
        self.list_widget = QListWidget()
        self.list_widget.setMinimumHeight(200)
        form.addRow(self.list_widget)

        self.btn_refresh = QPushButton("刷新列表")
        self.btn_refresh.setObjectName("Secondary")
        self.btn_refresh.clicked.connect(self._load_profiles)
        form.addRow(self.btn_refresh)
        self.add(box)

        self._load_profiles()

        # 监听切换信号，同步高亮
        self._pm.profile_changed.connect(self._on_profile_changed)

    def _load_profiles(self):
        self.list_widget.clear()
        profiles = self._pm.list_profiles()
        current = self._pm.active_name()

        for p in profiles:
            text = f"{p.display_name} ({p.name})" + (" [内置]" if p.is_builtin else " [用户]")
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, p.name)
            self.list_widget.addItem(item)
            if p.name == current:
                self.list_widget.setCurrentItem(item)

        self.list_widget.currentItemChanged.connect(self._on_item_changed)

    def _on_item_changed(self, current, previous):
        if current is None: return
        name = current.data(Qt.UserRole)
        if name != self._pm.active_name():
            self._pm.switch_to(name)

    def _on_profile_changed(self, name):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) == name:
                self.list_widget.blockSignals(True)
                self.list_widget.setCurrentItem(item)
                self.list_widget.blockSignals(False)
                break


# ==========================================
# 语音页
# ==========================================
class VoicePage(_Page):
    def __init__(self, config: ConfigManager, vb: VoiceBehavior):
        super().__init__()
        self._config = config
        self._vb = vb
        info = vb.debug_info()

        box1, f1 = _card("语音")
        self.cb_enabled = QCheckBox("启用语音")
        self.cb_enabled.setChecked(info["enabled"])
        self.cb_enabled.toggled.connect(lambda v: self._config.set("voice.enabled", bool(v)))
        f1.addRow(self.cb_enabled)

        self.cb_click = QCheckBox("点击时播放语音")
        self.cb_click.setChecked(info["click_enabled"])
        self.cb_click.toggled.connect(lambda v: self._config.set("voice.click_enabled", bool(v)))
        f1.addRow(self.cb_click)

        self.combo_lang = QComboBox()
        self.combo_lang.addItem("中文", "zh-CN")
        self.combo_lang.addItem("日本語", "ja-JP")
        idx = self.combo_lang.findData(info["language"])
        if idx >= 0: self.combo_lang.setCurrentIndex(idx)
        self.combo_lang.currentIndexChanged.connect(
            lambda _: self._config.set("voice.language", self.combo_lang.currentData()))
        f1.addRow("语音语种", self.combo_lang)
        self.add(box1)

        box2, f2 = _card("定时触发")
        self.spin_idle_min = QSpinBox()
        self.spin_idle_min.setRange(10, 86400);
        self.spin_idle_min.setSuffix(" 秒")
        self.spin_idle_min.setValue(int(info["idle_interval"][0]))
        self.spin_idle_min.valueChanged.connect(lambda v: self._config.set("voice.idle_min_interval_s", v))
        f2.addRow("闲置语音最短间隔", self.spin_idle_min)

        self.spin_idle_max = QSpinBox()
        self.spin_idle_max.setRange(10, 86400);
        self.spin_idle_max.setSuffix(" 秒")
        self.spin_idle_max.setValue(int(info["idle_interval"][1]))
        self.spin_idle_max.valueChanged.connect(lambda v: self._config.set("voice.idle_max_interval_s", v))
        f2.addRow("闲置语音最长间隔", self.spin_idle_max)

        self.spin_no_inter = QSpinBox()
        self.spin_no_inter.setRange(0, 86400);
        self.spin_no_inter.setSuffix(" 秒")
        self.spin_no_inter.setValue(int(info["no_interaction_timeout_s"]))
        self.spin_no_inter.valueChanged.connect(lambda v: self._config.set("voice.no_interaction_timeout_s", v))
        f2.addRow("无交互特殊语音阈值", self.spin_no_inter)

        self.cb_late = QCheckBox("启用熬夜特殊语音")
        self.cb_late.setChecked(info["late_night_enabled"])
        self.cb_late.toggled.connect(lambda v: self._config.set("voice.late_night_enabled", bool(v)))
        f2.addRow(self.cb_late)

        self.edit_late = QLineEdit(str(info["late_night_time"]))
        self.edit_late.setPlaceholderText("HH:MM，例如 22:30")
        self.edit_late.editingFinished.connect(
            lambda: self._config.set("voice.late_night_time", self.edit_late.text().strip()))
        f2.addRow("熬夜触发时间", self.edit_late)
        self.add(box2)


# ==========================================
# 行为页
# ==========================================
class BehaviorPage(_Page):
    def __init__(self, config: ConfigManager):
        super().__init__()
        self._config = config

        def get(key, default): return config.get(key, default)

        box1, f1 = _card("自动散步")
        self.cb_walk = QCheckBox("启用自动散步")
        self.cb_walk.setChecked(bool(get("behavior.walk.enabled", True)))
        self.cb_walk.toggled.connect(lambda v: config.set("behavior.walk.enabled", bool(v)))
        f1.addRow(self.cb_walk)

        self.spin_speed = QSpinBox()
        self.spin_speed.setRange(20, 400);
        self.spin_speed.setSuffix(" px/s")
        self.spin_speed.setValue(int(get("behavior.walk.speed_px_per_s", 80)))
        self.spin_speed.valueChanged.connect(lambda v: config.set("behavior.walk.speed_px_per_s", v))
        f1.addRow("散步速度", self.spin_speed)

        self.spin_min_dist = QSpinBox()
        self.spin_min_dist.setRange(20, 2000);
        self.spin_min_dist.setSuffix(" px")
        self.spin_min_dist.setValue(int(get("behavior.walk.min_distance", 120)))
        self.spin_min_dist.valueChanged.connect(lambda v: config.set("behavior.walk.min_distance", v))
        f1.addRow("单次最短距离", self.spin_min_dist)

        self.spin_max_dist = QSpinBox()
        self.spin_max_dist.setRange(20, 3000);
        self.spin_max_dist.setSuffix(" px")
        self.spin_max_dist.setValue(int(get("behavior.walk.max_distance", 380)))
        self.spin_max_dist.valueChanged.connect(lambda v: config.set("behavior.walk.max_distance", v))
        f1.addRow("单次最长距离", self.spin_max_dist)

        self.spin_walk_min = QSpinBox()
        self.spin_walk_min.setRange(5, 86400);
        self.spin_walk_min.setSuffix(" 秒")
        self.spin_walk_min.setValue(int(get("behavior.walk.min_interval_s", 25)))
        self.spin_walk_min.valueChanged.connect(lambda v: config.set("behavior.walk.min_interval_s", v))
        f1.addRow("散步最短间隔", self.spin_walk_min)

        self.spin_walk_max = QSpinBox()
        self.spin_walk_max.setRange(5, 86400);
        self.spin_walk_max.setSuffix(" 秒")
        self.spin_walk_max.setValue(int(get("behavior.walk.max_interval_s", 70)))
        self.spin_walk_max.valueChanged.connect(lambda v: config.set("behavior.walk.max_interval_s", v))
        f1.addRow("散步最长间隔", self.spin_walk_max)
        self.add(box1)

        box2, f2 = _card("随机朝向")
        self.spin_turn_min = QDoubleSpinBox()
        self.spin_turn_min.setRange(1, 600);
        self.spin_turn_min.setSuffix(" 秒");
        self.spin_turn_min.setDecimals(1)
        self.spin_turn_min.setValue(float(get("behavior.facing.turn_min_s", 8)))
        self.spin_turn_min.valueChanged.connect(lambda v: config.set("behavior.facing.turn_min_s", float(v)))
        f2.addRow("翻面最短间隔", self.spin_turn_min)

        self.spin_turn_max = QDoubleSpinBox()
        self.spin_turn_max.setRange(1, 600);
        self.spin_turn_max.setSuffix(" 秒");
        self.spin_turn_max.setDecimals(1)
        self.spin_turn_max.setValue(float(get("behavior.facing.turn_max_s", 20)))
        self.spin_turn_max.valueChanged.connect(lambda v: config.set("behavior.facing.turn_max_s", float(v)))
        f2.addRow("翻面最长间隔", self.spin_turn_max)
        self.add(box2)


# ==========================================
# 外观页
# ==========================================
class AppearancePage(_Page):
    def __init__(self, config: ConfigManager, pet: PetWindow):
        super().__init__()
        self._config = config
        self._pet = pet

        box, form = _card("桌宠位置")
        self.spin_offset = QSpinBox()
        self.spin_offset.setRange(-1000, 1000)
        self.spin_offset.setSuffix(" px")
        self.spin_offset.setValue(int(config.get("pet.offset_y", 0)))
        self.spin_offset.valueChanged.connect(self._on_offset_changed)
        form.addRow("纵向偏移", self.spin_offset)

        btn_reset = QPushButton("复位到屏幕底部")
        btn_reset.setObjectName("Secondary")
        btn_reset.clicked.connect(self._reset)
        form.addRow(btn_reset)
        self.add(box)

    def refresh_from_config(self):
        v = int(self._config.get("pet.offset_y", 0))
        if self.spin_offset.value() != v:
            self.spin_offset.blockSignals(True)
            self.spin_offset.setValue(v)
            self.spin_offset.blockSignals(False)

    def _on_offset_changed(self, value: int):
        self._config.set("pet.offset_y", int(value))

    def _reset(self):
        self._pet.reset_position()


# ==========================================
# 系统页
# ==========================================
class SystemPage(_Page):
    def __init__(self, config: ConfigManager):
        super().__init__()
        box, form = _card("开机自启动")
        self.cb_autostart = QCheckBox("随 Windows 启动")
        self.cb_autostart.setChecked(autostart.is_registered())
        self.cb_autostart.toggled.connect(self._on_toggle)
        form.addRow(self.cb_autostart)

        btn_data = QPushButton("打开配置目录")
        btn_data.setObjectName("Secondary")
        btn_data.clicked.connect(lambda: os.startfile(str(USER_DIR)))
        form.addRow(btn_data)
        self.add(box)

    def _on_toggle(self, enabled: bool):
        ok = autostart.enable() if enabled else autostart.disable()
        if not ok:
            self.cb_autostart.blockSignals(True)
            self.cb_autostart.setChecked(not enabled)
            self.cb_autostart.blockSignals(False)


# ==========================================
# 日志页
# ==========================================
class LogPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self._view = QPlainTextEdit()
        self._view.setReadOnly(True)
        font = QFont("Consolas");
        font.setStyleHint(QFont.Monospace);
        font.setPointSize(9)
        self._view.setFont(font);
        self._view.setMaximumBlockCount(2000)
        layout.addWidget(self._view)

        for line in log_bus().history(): self._view.appendPlainText(line)
        log_bus().log_emitted.connect(self._view.appendPlainText)


# ==========================================
# 主窗口
# ==========================================
class SettingsDialog(QWidget):
    def __init__(self, config: ConfigManager, vb: VoiceBehavior, pet: PetWindow, pm: ProfileManager):
        super().__init__()
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.resize(850, 600)
        self._drag_pos = None

        outer = QVBoxLayout(self);
        outer.setContentsMargins(0, 0, 0, 0)
        self._root = QWidget();
        self._root.setObjectName("SettingsRoot");
        outer.addWidget(self._root)
        rl = QVBoxLayout(self._root);
        rl.setContentsMargins(0, 0, 0, 0);
        rl.setSpacing(0)

        title_bar = QWidget();
        title_bar.setFixedHeight(44)
        tb = QHBoxLayout(title_bar);
        tb.setContentsMargins(16, 0, 8, 0)
        tb.addWidget(QLabel("设置"))
        tb.addStretch()
        btn_close = QPushButton("✕");
        btn_close.setObjectName("CloseBtn")
        btn_close.clicked.connect(self.close);
        tb.addWidget(btn_close)
        rl.addWidget(title_bar)

        body = QWidget();
        bl = QHBoxLayout(body);
        bl.setContentsMargins(0, 0, 0, 0);
        bl.setSpacing(0)
        self._nav = QListWidget();
        self._nav.setFixedWidth(170)
        for txt in ("形象", "语音", "行为", "外观", "系统", "日志"): self._nav.addItem(txt)
        bl.addWidget(self._nav)

        self._stack = QStackedWidget()
        self._p_profile = ProfilePage(config, pm)
        self._p_voice = VoicePage(config, vb)
        self._p_behavior = BehaviorPage(config)
        self._p_appearance = AppearancePage(config, pet)
        self._stack.addWidget(self._p_profile)
        self._stack.addWidget(self._p_voice)
        self._stack.addWidget(self._p_behavior)
        self._stack.addWidget(self._p_appearance)
        self._stack.addWidget(SystemPage(config))
        self._stack.addWidget(LogPage())
        bl.addWidget(self._stack, 1)
        rl.addWidget(body, 1)

        self._nav.currentRowChanged.connect(self._stack.setCurrentIndex)
        self._nav.setCurrentRow(0)
        config.changed.connect(lambda k: self._p_appearance.refresh_from_config() if k == "pet.offset_y" else None)

    def show_and_raise(self):
        self._p_appearance.refresh_from_config()
        self.show();
        self.raise_();
        self.activateWindow()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and e.position().y() < 44:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and (e.buttons() & Qt.LeftButton): self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None