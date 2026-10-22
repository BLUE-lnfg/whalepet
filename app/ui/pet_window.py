from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QAction, QCursor, QPainter
from PySide6.QtWidgets import QApplication, QMenu, QToolTip, QWidget

from app.animation.clip import Clip
from app.config.binder import ConfigBinder
from app.config.manager import ConfigManager

CLICK_DISTANCE_THRESHOLD = 5
MIN_VISIBLE_PX = 60


class PetWindow(QWidget):
    clicked = Signal()
    drag_started = Signal()
    facing_changed = Signal(str)
    settings_requested = Signal()

    def __init__(self, config: ConfigManager):
        super().__init__()

        self._config = config

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(320, 320)

        self._drag_offset: QPoint | None = None
        self._press_pos: QPoint | None = None
        self._moved = False

        self._mouse_through = False
        self._through_actions: list[QAction] = []

        self._offset_y: int = int(self._config.get("pet.offset_y", 0))

        self._vertical_unlock_armed = False
        self._vertical_dragging = False

        self._facing: str = "right"

        self._controller = None
        self._current_clip: Clip | None = None
        self._current_frame_idx = 0

        self._place_bottom()

        self._binder = ConfigBinder(config, self)
        self._binder.bind("pet.offset_y", self._on_offset_changed_external)

    # ---------- 外部改 offset 的响应 ----------

    def _on_offset_changed_external(self, key: str):
        new_value = int(self._config.get("pet.offset_y", 0))
        self._apply_offset(new_value)

    def _apply_offset(self, value: int):
        value = int(value)
        if value == self._offset_y:
            return
        self._offset_y = value
        screen = self.screen().availableGeometry()
        y = screen.y() + screen.height() - self.height() + value
        self.move(self.x(), y)

    def set_offset(self, value: int):
        self._config.set("pet.offset_y", int(value))

    # ---------- controller 接线 ----------

    def set_controller(self, controller):
        self._controller = controller
        controller.clip_changed.connect(self._on_clip_changed)
        controller.player.frame_changed.connect(self._on_frame_changed)
        self.clicked.connect(controller.trigger_click)

    def _on_clip_changed(self, clip: Clip):
        self._current_clip = clip
        self._current_frame_idx = 0
        self._apply_clip_size(clip)
        self.update()

    def _on_frame_changed(self, idx: int):
        self._current_frame_idx = idx
        self.update()

    @property
    def is_dragging(self) -> bool:
        return self._drag_offset is not None and self._moved

    # ---------- 朝向 ----------

    @property
    def facing(self) -> str:
        return self._facing

    def set_facing(self, facing: str):
        if facing not in ("right", "left") or facing == self._facing:
            return
        old = self._facing
        self._facing = facing
        self.update()
        self.facing_changed.emit(facing)
        print(f"[pet] 朝向：{old} → {facing}")

    def toggle_facing(self):
        self.set_facing("left" if self._facing == "right" else "right")

    # ---------- 尺寸 & 位置 ----------

    def _apply_clip_size(self, clip: Clip):
        dpr = self.devicePixelRatioF()
        w, h = clip.out_size
        logical_w = max(1, int(round(w / dpr)))
        logical_h = max(1, int(round(h / dpr)))

        old_center_x = self.frameGeometry().center().x()

        self.resize(logical_w, logical_h)
        new_x = old_center_x - logical_w // 2
        self.move(self._clamp_pos(QPoint(new_x, 0)))

    def _place_bottom(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.x() + screen.width() - self.width() - 60
        y = screen.y() + screen.height() - self.height() + self._offset_y
        self.move(QPoint(x, y))

    def _clamp_pos(self, pos: QPoint, allow_vertical: bool = False) -> QPoint:
        screen = self.screen().availableGeometry()
        x = max(screen.x(), min(pos.x(), screen.x() + screen.width() - self.width()))

        if allow_vertical:
            vis = min(MIN_VISIBLE_PX, self.height())
            y_min = screen.y() - self.height() + vis
            y_max = screen.y() + screen.height() - vis
            y = max(y_min, min(pos.y(), y_max))
        else:
            y = screen.y() + screen.height() - self.height() + self._offset_y
        return QPoint(x, y)

    def walk_x_bounds(self) -> tuple[int, int]:
        screen = self.screen().availableGeometry()
        return screen.x(), screen.x() + screen.width() - self.width()

    # ---------- 纵向调整 ----------

    def toggle_arm_vertical_unlock(self):
        if self._vertical_unlock_armed:
            self._vertical_unlock_armed = False
            self.unsetCursor()
            print("[pet] 纵向调整：已取消")
        else:
            self._vertical_unlock_armed = True
            self.setCursor(Qt.SizeVerCursor)
            QToolTip.showText(
                QCursor.pos(),
                "下次拖动可上下移动，松手后自动锁定",
                self,
            )
            print("[pet] 纵向调整：已激活，下次拖动生效")

    def _persist_offset_from_position(self):
        screen = self.screen().availableGeometry()
        base_y = screen.y() + screen.height() - self.height()
        new_offset = self.y() - base_y
        self.set_offset(new_offset)
        print(f"[pet] 纵向偏移已更新为 {new_offset}")

    def reset_position(self):
        screen = self.screen().availableGeometry()
        self.set_offset(0)
        x = screen.x() + screen.width() - self.width() - 60
        self.move(x, self.y())
        print("[pet] 已复位到屏幕底部")

    # ---------- 绘制 ----------

    def paintEvent(self, event):
        if self._current_clip is None:
            return
        frames = self._current_clip.frames_for_facing(self._facing)
        pix = frames[self._current_frame_idx]
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.drawPixmap(0, 0, pix)

    # ---------- 鼠标穿透 ----------

    def add_through_action(self, action: QAction):
        self._through_actions.append(action)
        action.setChecked(self._mouse_through)
        action.toggled.connect(self.set_mouse_through)

    def set_mouse_through(self, enabled: bool):
        if enabled == self._mouse_through:
            return
        self._mouse_through = enabled
        was_visible = self.isVisible()
        self.setWindowFlag(Qt.WindowTransparentForInput, enabled)
        if was_visible:
            self.show()
        for a in self._through_actions:
            a.blockSignals(True)
            a.setChecked(enabled)
            a.blockSignals(False)
        print(f"[pet] 鼠标穿透：{'开' if enabled else '关'}")

    # ---------- 拖动 & 点击 ----------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self._drag_offset = self._press_pos - self.frameGeometry().topLeft()
            self._moved = False
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and (event.buttons() & Qt.LeftButton):
            pos = event.globalPosition().toPoint()
            if not self._moved and (pos - self._press_pos).manhattanLength() > CLICK_DISTANCE_THRESHOLD:
                self._moved = True
                self.drag_started.emit()
                if self._vertical_unlock_armed:
                    self._vertical_dragging = True
                    self._vertical_unlock_armed = False
            if self._moved:
                target = pos - self._drag_offset
                self.move(self._clamp_pos(target, allow_vertical=self._vertical_dragging))
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._drag_offset is not None:
            if not self._moved:
                self.clicked.emit()
            elif self._vertical_dragging:
                self._persist_offset_from_position()
                self._vertical_dragging = False
                self.unsetCursor()
        self._drag_offset = None
        self._press_pos = None
        event.accept()

    # ---------- 右键菜单 ----------

    def contextMenuEvent(self, event):
        menu = QMenu(self)

        act_through = menu.addAction("鼠标穿透")
        act_through.setCheckable(True)
        act_through.setChecked(self._mouse_through)
        self._through_actions.append(act_through)
        act_through.toggled.connect(self.set_mouse_through)

        menu.addSeparator()

        label = "取消纵向调整" if self._vertical_unlock_armed else "调整纵向位置"
        act_adjust = menu.addAction(label)
        act_adjust.triggered.connect(self.toggle_arm_vertical_unlock)

        act_reset = menu.addAction("复位到屏幕底部")
        act_reset.triggered.connect(self.reset_position)

        menu.addSeparator()

        act_voice = menu.addAction("语音")
        act_voice.setCheckable(True)
        act_voice.setChecked(bool(self._config.get("voice.enabled", True)))
        act_voice.toggled.connect(
            lambda v: self._config.set("voice.enabled", bool(v))
        )

        lang_menu = menu.addMenu("语音语种")
        current_lang = str(self._config.get("voice.language", "zh-CN"))
        act_zh = lang_menu.addAction("中文")
        act_ja = lang_menu.addAction("日本語")
        act_zh.setCheckable(True)
        act_ja.setCheckable(True)
        act_zh.setChecked(current_lang == "zh-CN")
        act_ja.setChecked(current_lang == "ja-JP")
        act_zh.triggered.connect(lambda: self._config.set("voice.language", "zh-CN"))
        act_ja.triggered.connect(lambda: self._config.set("voice.language", "ja-JP"))

        menu.addSeparator()

        act_settings = menu.addAction("设置…")
        act_settings.triggered.connect(self.settings_requested.emit)

        menu.addSeparator()
        act_hide = menu.addAction("隐藏桌宠")
        menu.addSeparator()
        act_quit = menu.addAction("退出")

        chosen = menu.exec(event.globalPos())
        if chosen == act_hide:
            self.hide()
        elif chosen == act_quit:
            QApplication.instance().quit()