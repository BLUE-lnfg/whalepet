import os

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QStackedWidget, QScrollArea, QGroupBox, QFormLayout, QLabel,
    QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox, QPushButton,
    QLineEdit, QMessageBox, QPlainTextEdit,
)

from app.config.manager import ConfigManager
from app.behavior.voice_behavior import VoiceBehavior
from app.ui.pet_window import PetWindow
from app.services import autostart
from app.services.logger import bus as log_bus
from app.constants import USER_DIR, LOG_DIR


def _card(title: str) -> tuple[QGroupBox, QFormLayout]:
    box = QGroupBox(title)
    form = QFormLayout(box)
    form.setLabelAlignment(Qt.AlignLeft)
    form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
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
        self._layout.setSpacing(12)
        self._layout.addStretch()
        self.setWidget(self._body)

    def add(self, w: QWidget):
        self._layout.insertWidget(self._layout.count() - 1, w)

    def refresh_from_config(self):
        pass


# ============================================================
# 语音页
# ============================================================

class VoicePage(_Page):
    def __init__(self, config: ConfigManager, vb: VoiceBehavior):
        super().__init__()
        self._config = config
        self._vb = vb

        info = vb.debug_info()

        box1, f1 = _card("语音")
        self.cb_enabled = QCheckBox("启用语音")
        self.cb_enabled.setChecked(info["enabled"])
        self.cb_enabled.toggled.connect(
            lambda v: self._config.set("voice.enabled", bool(v))
        )
        f1.addRow(self.cb_enabled)

        self.cb_click = QCheckBox("点击时播放语音")
        self.cb_click.setChecked(info["click_enabled"])
        self.cb_click.toggled.connect(
            lambda v: self._config.set("voice.click_enabled", bool(v))
        )
        f1.addRow(self.cb_click)

        self.combo_lang = QComboBox()
        self.combo_lang.addItem("中文", "zh-CN")
        self.combo_lang.addItem("日本語", "ja-JP")
        idx = self.combo_lang.findData(info["language"])
        if idx >= 0:
            self.combo_lang.setCurrentIndex(idx)
        self.combo_lang.currentIndexChanged.connect(
            lambda _: self._config.set(
                "voice.language", self.combo_lang.currentData()
            )
        )
        f1.addRow("语音语种", self.combo_lang)
        self.add(box1)

        box2, f2 = _card("定时触发")
        self.spin_idle_min = QSpinBox()
        self.spin_idle_min.setRange(10, 86400)
        self.spin_idle_min.setSuffix(" 秒")
        self.spin_idle_min.setValue(int(info["idle_interval"][0]))
        self.spin_idle_min.valueChanged.connect(
            lambda v: self._config.set("voice.idle_min_interval_s", v)
        )
        f2.addRow("闲置语音最短间隔", self.spin_idle_min)

        self.spin_idle_max = QSpinBox()
        self.spin_idle_max.setRange(10, 86400)
        self.spin_idle_max.setSuffix(" 秒")
        self.spin_idle_max.setValue(int(info["idle_interval"][1]))
        self.spin_idle_max.valueChanged.connect(
            lambda v: self._config.set("voice.idle_max_interval_s", v)
        )
        f2.addRow("闲置语音最长间隔", self.spin_idle_max)

        self.spin_no_inter = QSpinBox()
        self.spin_no_inter.setRange(0, 86400)
        self.spin_no_inter.setSuffix(" 秒")
        self.spin_no_inter.setValue(int(info["no_interaction_timeout_s"]))
        self.spin_no_inter.valueChanged.connect(
            lambda v: self._config.set("voice.no_interaction_timeout_s", v)
        )
        f2.addRow("无交互特殊语音阈值", self.spin_no_inter)

        self.cb_late = QCheckBox("启用熬夜特殊语音")
        self.cb_late.setChecked(info["late_night_enabled"])
        self.cb_late.toggled.connect(
            lambda v: self._config.set("voice.late_night_enabled", bool(v))
        )
        f2.addRow(self.cb_late)

        self.edit_late = QLineEdit(str(info["late_night_time"]))
        self.edit_late.setPlaceholderText("HH:MM，例如 22:30")
        self.edit_late.editingFinished.connect(
            lambda: self._config.set("voice.late_night_time", self.edit_late.text().strip())
        )
        f2.addRow("熬夜触发时间", self.edit_late)

        f2.addRow(_hint("修改后立即生效。间隔单位为秒，300 = 5 分钟，3600 = 1 小时。"))
        self.add(box2)

        box3, f3 = _card("素材与测试")
        f3.addRow(_hint(
            f"闲置池：{info['counts']['idle']} 个 wav    "
            f"点击：{info['counts']['click']} 个    "
            f"无交互：{info['counts']['no_interaction']} 个    "
            f"熬夜：{info['counts']['late_night']} 个"
        ))

        btn_row = QHBoxLayout()
        for label, cat in [
            ("试听闲置", "idle"),
            ("试听点击", "click"),
            ("试听无交互", "no_interaction"),
            ("试听熬夜", "late_night"),
        ]:
            b = QPushButton(label)
            b.setObjectName("Secondary")
            b.clicked.connect(lambda checked=False, c=cat: self._test(c))
            btn_row.addWidget(b)
        btn_row.addStretch()
        f3.addRow(btn_row)
        self.add(box3)

    def refresh_from_config(self):
        cfg = self._config

        v = bool(cfg.get("voice.enabled", True))
        if self.cb_enabled.isChecked() != v:
            self.cb_enabled.blockSignals(True)
            self.cb_enabled.setChecked(v)
            self.cb_enabled.blockSignals(False)

        v = bool(cfg.get("voice.click_enabled", True))
        if self.cb_click.isChecked() != v:
            self.cb_click.blockSignals(True)
            self.cb_click.setChecked(v)
            self.cb_click.blockSignals(False)

        lang = str(cfg.get("voice.language", "zh-CN"))
        idx = self.combo_lang.findData(lang)
        if idx >= 0 and self.combo_lang.currentIndex() != idx:
            self.combo_lang.blockSignals(True)
            self.combo_lang.setCurrentIndex(idx)
            self.combo_lang.blockSignals(False)

    def _test(self, category: str):
        result = self._vb.debug_trigger(category)
        if result["ok"]:
            QMessageBox.information(
                self, "试听", f"正在播放：{result['file'].name}\n（{result['source']}）"
            )
        else:
            QMessageBox.warning(self, "试听失败", result["reason"])


# ============================================================
# 行为页
# ============================================================

class BehaviorPage(_Page):
    def __init__(self, config: ConfigManager):
        super().__init__()
        self._config = config

        def get(key, default):
            return config.get(key, default)

        box1, f1 = _card("自动散步")
        self.cb_walk = QCheckBox("启用自动散步")
        self.cb_walk.setChecked(bool(get("behavior.walk.enabled", True)))
        self.cb_walk.toggled.connect(
            lambda v: config.set("behavior.walk.enabled", bool(v))
        )
        f1.addRow(self.cb_walk)

        self.spin_speed = QSpinBox()
        self.spin_speed.setRange(20, 400)
        self.spin_speed.setSuffix(" px/s")
        self.spin_speed.setValue(int(get("behavior.walk.speed_px_per_s", 80)))
        self.spin_speed.valueChanged.connect(
            lambda v: config.set("behavior.walk.speed_px_per_s", v)
        )
        f1.addRow("散步速度", self.spin_speed)

        self.spin_min_dist = QSpinBox()
        self.spin_min_dist.setRange(20, 2000)
        self.spin_min_dist.setSuffix(" px")
        self.spin_min_dist.setValue(int(get("behavior.walk.min_distance", 120)))
        self.spin_min_dist.valueChanged.connect(
            lambda v: config.set("behavior.walk.min_distance", v)
        )
        f1.addRow("单次最短距离", self.spin_min_dist)

        self.spin_max_dist = QSpinBox()
        self.spin_max_dist.setRange(20, 3000)
        self.spin_max_dist.setSuffix(" px")
        self.spin_max_dist.setValue(int(get("behavior.walk.max_distance", 380)))
        self.spin_max_dist.valueChanged.connect(
            lambda v: config.set("behavior.walk.max_distance", v)
        )
        f1.addRow("单次最长距离", self.spin_max_dist)

        self.spin_walk_min = QSpinBox()
        self.spin_walk_min.setRange(5, 86400)
        self.spin_walk_min.setSuffix(" 秒")
        self.spin_walk_min.setValue(int(get("behavior.walk.min_interval_s", 25)))
        self.spin_walk_min.valueChanged.connect(
            lambda v: config.set("behavior.walk.min_interval_s", v)
        )
        f1.addRow("散步最短间隔", self.spin_walk_min)

        self.spin_walk_max = QSpinBox()
        self.spin_walk_max.setRange(5, 86400)
        self.spin_walk_max.setSuffix(" 秒")
        self.spin_walk_max.setValue(int(get("behavior.walk.max_interval_s", 70)))
        self.spin_walk_max.valueChanged.connect(
            lambda v: config.set("behavior.walk.max_interval_s", v)
        )
        f1.addRow("散步最长间隔", self.spin_walk_max)
        self.add(box1)

        box2, f2 = _card("随机朝向")
        self.spin_turn_min = QDoubleSpinBox()
        self.spin_turn_min.setRange(1, 600)
        self.spin_turn_min.setSuffix(" 秒")
        self.spin_turn_min.setDecimals(1)
        self.spin_turn_min.setValue(float(get("behavior.facing.turn_min_s", 8)))
        self.spin_turn_min.valueChanged.connect(
            lambda v: config.set("behavior.facing.turn_min_s", float(v))
        )
        f2.addRow("翻面最短间隔", self.spin_turn_min)

        self.spin_turn_max = QDoubleSpinBox()
        self.spin_turn_max.setRange(1, 600)
        self.spin_turn_max.setSuffix(" 秒")
        self.spin_turn_max.setDecimals(1)
        self.spin_turn_max.setValue(float(get("behavior.facing.turn_max_s", 20)))
        self.spin_turn_max.valueChanged.connect(
            lambda v: config.set("behavior.facing.turn_max_s", float(v))
        )
        f2.addRow("翻面最长间隔", self.spin_turn_max)

        self.spin_turn_prob = QDoubleSpinBox()
        self.spin_turn_prob.setRange(0.0, 1.0)
        self.spin_turn_prob.setSingleStep(0.05)
        self.spin_turn_prob.setDecimals(2)
        self.spin_turn_prob.setValue(float(get("behavior.facing.turn_probability", 0.5)))
        self.spin_turn_prob.valueChanged.connect(
            lambda v: config.set("behavior.facing.turn_probability", float(v))
        )
        f2.addRow("翻面概率", self.spin_turn_prob)
        f2.addRow(_hint("翻面只在 idle 状态、且未在散步时发生。0.5 表示每次检查有 50% 概率翻面。"))
        self.add(box2)


# ============================================================
# 外观页
# ============================================================

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

        form.addRow(_hint(
            "偏移为正数时窗口下移（人物脚上移到任务栏上方），"
            "负数时窗口上移。也可以用右键菜单的“调整纵向位置”拖动设置。"
        ))
        self.add(box)

    def refresh_from_config(self):
        v = int(self._config.get("pet.offset_y", 0))
        if self.spin_offset.value() != v:
            self.spin_offset.blockSignals(True)
            self.spin_offset.setValue(v)
            self.spin_offset.blockSignals(False)

    def _on_offset_changed(self, value: int):
        # 只写 config，位置由 PetWindow 订阅 pet.offset_y 自动应用
        self._config.set("pet.offset_y", int(value))

    def _reset(self):
        self._pet.reset_position()
        # reset_position 内部会 set config，触发 changed，refresh_from_config 自动同步 spinbox


# ============================================================
# 系统页
# ============================================================

class SystemPage(_Page):
    def __init__(self, config: ConfigManager):
        super().__init__()
        self._config = config

        box, form = _card("开机自启动")
        self.cb_autostart = QCheckBox("随 Windows 启动")
        self.cb_autostart.setChecked(autostart.is_registered())
        self.cb_autostart.toggled.connect(self._on_toggle)
        form.addRow(self.cb_autostart)

        cmd_label = QLabel(autostart.get_launch_command())
        cmd_label.setWordWrap(True)
        cmd_label.setObjectName("Hint")
        form.addRow("启动命令", cmd_label)

        form.addRow(_hint(
            "开发模式下启动命令是 Python + main.py；打包成 exe 后会自动切换为直接运行 exe。"
            "如果以后移动了程序目录，下一次启动时会自动更新注册表路径。"
        ))
        self.add(box)

        box2, f2 = _card("数据与日志")
        btn_data = QPushButton("打开配置目录")
        btn_data.setObjectName("Secondary")
        btn_data.clicked.connect(self._open_data_dir)
        f2.addRow(btn_data)

        btn_log = QPushButton("打开日志目录")
        btn_log.setObjectName("Secondary")
        btn_log.clicked.connect(self._open_log_dir)
        f2.addRow(btn_log)

        f2.addRow(_hint(f"配置目录：{USER_DIR}"))
        self.add(box2)

    def _on_toggle(self, enabled: bool):
        ok = autostart.enable() if enabled else autostart.disable()
        if not ok:
            QMessageBox.warning(
                self, "操作失败",
                "写入注册表失败。可能是权限问题或系统策略限制。",
            )
            self.cb_autostart.blockSignals(True)
            self.cb_autostart.setChecked(not enabled)
            self.cb_autostart.blockSignals(False)

    def _open_data_dir(self):
        USER_DIR.mkdir(parents=True, exist_ok=True)
        os.startfile(str(USER_DIR))

    def _open_log_dir(self):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        os.startfile(str(LOG_DIR))


# ============================================================
# 日志页
# ============================================================

class LogPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        toolbar = QHBoxLayout()
        self._count_label = QLabel("0 条")
        self._count_label.setObjectName("Hint")

        btn_clear = QPushButton("清空显示")
        btn_clear.setObjectName("Secondary")
        btn_clear.clicked.connect(self._clear)

        btn_copy = QPushButton("复制全部")
        btn_copy.setObjectName("Secondary")
        btn_copy.clicked.connect(self._copy_all)

        btn_open = QPushButton("打开日志目录")
        btn_open.setObjectName("Secondary")
        btn_open.clicked.connect(self._open_log_dir)

        toolbar.addWidget(self._count_label)
        toolbar.addStretch()
        toolbar.addWidget(btn_clear)
        toolbar.addWidget(btn_copy)
        toolbar.addWidget(btn_open)
        layout.addLayout(toolbar)

        self._view = QPlainTextEdit()
        self._view.setReadOnly(True)
        font = QFont("Consolas")
        font.setStyleHint(QFont.Monospace)
        font.setPointSize(9)
        self._view.setFont(font)
        self._view.setMaximumBlockCount(2000)
        self._view.setLineWrapMode(QPlainTextEdit.NoWrap)
        layout.addWidget(self._view, 1)

        for line in log_bus().history():
            self._view.appendPlainText(line)
        self._update_count()

        log_bus().log_emitted.connect(self._on_log)

    def _on_log(self, line: str):
        self._view.appendPlainText(line)
        sb = self._view.verticalScrollBar()
        sb.setValue(sb.maximum())
        self._update_count()

    def _clear(self):
        self._view.clear()
        self._update_count()

    def _update_count(self):
        n = self._view.blockCount()
        self._count_label.setText(f"{n} 条（内存上限 2000）")

    def _copy_all(self):
        QGuiApplication.clipboard().setText(self._view.toPlainText())

    def _open_log_dir(self):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        os.startfile(str(LOG_DIR))


# ============================================================
# 设置面板主窗口
# ============================================================

class SettingsDialog(QWidget):
    def __init__(self, config: ConfigManager, vb: VoiceBehavior, pet: PetWindow):
        super().__init__()
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setWindowTitle("桌宠设置")
        self.resize(820, 600)

        self._config = config
        self._drag_pos: QPoint | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._root = QWidget()
        self._root.setObjectName("SettingsRoot")
        outer.addWidget(self._root)

        root_layout = QVBoxLayout(self._root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        title_bar = QWidget()
        title_bar.setObjectName("TitleBar")
        title_bar.setFixedHeight(44)
        tb = QHBoxLayout(title_bar)
        tb.setContentsMargins(16, 0, 8, 0)

        title = QLabel("设置")
        title.setObjectName("TitleText")
        tb.addWidget(title)
        tb.addStretch()

        btn_close = QPushButton("✕")
        btn_close.setObjectName("CloseBtn")
        btn_close.setFixedSize(32, 32)
        btn_close.clicked.connect(self.close)
        tb.addWidget(btn_close)
        root_layout.addWidget(title_bar)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self._nav = QListWidget()
        self._nav.setFixedWidth(170)
        for text in ("语音", "行为", "外观", "系统", "日志"):
            self._nav.addItem(QListWidgetItem(text))
        self._nav.currentRowChanged.connect(self._on_nav_changed)
        body_layout.addWidget(self._nav)

        self._stack = QStackedWidget()

        self._voice_page = VoicePage(config, vb)
        self._behavior_page = BehaviorPage(config)
        self._appearance_page = AppearancePage(config, pet)
        self._system_page = SystemPage(config)
        self._log_page = LogPage()

        self._stack.addWidget(self._voice_page)
        self._stack.addWidget(self._behavior_page)
        self._stack.addWidget(self._appearance_page)
        self._stack.addWidget(self._system_page)
        self._stack.addWidget(self._log_page)

        body_layout.addWidget(self._stack, 1)

        root_layout.addWidget(body, 1)
        self._nav.setCurrentRow(0)

        self._config.changed.connect(self._on_config_changed)

    def _on_config_changed(self, key: str):
        if key.startswith("voice."):
            self._voice_page.refresh_from_config()
        elif key == "pet.offset_y":
            self._appearance_page.refresh_from_config()

    def _on_nav_changed(self, row: int):
        if 0 <= row < self._stack.count():
            self._stack.setCurrentIndex(row)

    def show_and_raise(self):
        self._voice_page.refresh_from_config()
        self._behavior_page.refresh_from_config()
        self._appearance_page.refresh_from_config()
        self._system_page.refresh_from_config()

        self.show()
        self.raise_()
        self.activateWindow()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.position().y() < 44:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and (event.buttons() & Qt.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()