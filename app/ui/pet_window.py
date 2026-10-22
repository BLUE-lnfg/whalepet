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
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_InputMethodEnabled, False)
        self.resize(320, 320)

        self._drag_offset = None
        self._press_pos = None
        self._moved = False
        self._mouse_through = False
        self._through_actions = []
        self._offset_y = int(self._config.get("pet.offset_y", 0))
        self._facing = "right"

        self._controller = None
        self._current_clip = None
        self._current_frame_idx = 0

        self._place_bottom()
        self._binder = ConfigBinder(config, self)
        self._binder.bind("pet.offset_y", self._on_offset_changed_external)

    def set_controller(self, controller):
        self._controller = controller
        controller.clip_changed.connect(self._on_clip_changed)
        controller.player.frame_changed.connect(self._on_frame_changed)
        self.clicked.connect(controller.trigger_click)

    def clear_display(self):
        self._current_clip = None
        self._current_frame_idx = 0
        self.update()

    def _on_clip_changed(self, clip: Clip):
        self._current_clip = clip
        self._current_frame_idx = 0
        self._apply_clip_size(clip)
        self.update()

    def _on_frame_changed(self, idx: int):
        self._current_frame_idx = idx
        self.update()

    @property
    def is_dragging(self):
        return self._drag_offset is not None and self._moved

    @property
    def facing(self):
        return self._facing

    def set_facing(self, facing: str):
        if facing not in ("right", "left") or facing == self._facing: return
        self._facing = facing
        self.update()
        self.facing_changed.emit(facing)

    def toggle_facing(self):
        self.set_facing("left" if self._facing == "right" else "right")

    def _apply_clip_size(self, clip: Clip):
        dpr = self.devicePixelRatioF()
        w, h = clip.out_size
        logical_w, logical_h = max(1, int(w / dpr)), max(1, int(h / dpr))
        old_center_x = self.frameGeometry().center().x()
        self.resize(logical_w, logical_h)
        self.move(self._clamp_pos(QPoint(old_center_x - logical_w // 2, 0)))

    def _place_bottom(self):
        scr = QApplication.primaryScreen().availableGeometry()
        self.move(
            QPoint(scr.x() + scr.width() - self.width() - 60, scr.y() + scr.height() - self.height() + self._offset_y))

    def _on_offset_changed_external(self, key):
        new_value = int(self._config.get("pet.offset_y", 0))
        if new_value == self._offset_y: return
        self._offset_y = new_value
        scr = self.screen().availableGeometry()
        self.move(self.x(), scr.y() + scr.height() - self.height() + new_value)

    def _clamp_pos(self, pos: QPoint, allow_vertical: bool = False) -> QPoint:
        scr = self.screen().availableGeometry()
        x = max(scr.x(), min(pos.x(), scr.x() + scr.width() - self.width()))
        if allow_vertical:
            vis = min(MIN_VISIBLE_PX, self.height())
            y = max(scr.y() - self.height() + vis, min(pos.y(), scr.y() + scr.height() - vis))
        else:
            y = scr.y() + scr.height() - self.height() + self._offset_y
        return QPoint(x, y)

    def walk_x_bounds(self):
        scr = self.screen().availableGeometry()
        return scr.x(), scr.x() + scr.width() - self.width()

    def paintEvent(self, event):
        if not self._current_clip: return
        frames = self._current_clip.frames_for_facing(self._facing)
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.drawPixmap(0, 0, frames[self._current_frame_idx])

    def add_through_action(self, action: QAction):
        self._through_actions.append(action)
        action.setChecked(self._mouse_through)
        action.toggled.connect(self.set_mouse_through)

    def set_mouse_through(self, enabled: bool):
        if enabled == self._mouse_through: return
        self._mouse_through = enabled
        was_visible = self.isVisible()
        self.setWindowFlag(Qt.WindowTransparentForInput, enabled)
        if was_visible: self.show()
        for a in self._through_actions:
            a.blockSignals(True);
            a.setChecked(enabled);
            a.blockSignals(False)

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
            if self._moved:
                self.move(self._clamp_pos(pos - self._drag_offset))
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._drag_offset is not None:
            if not self._moved: self.clicked.emit()
        self._drag_offset = None
        self._press_pos = None
        event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        act_through = menu.addAction("鼠标穿透")
        act_through.setCheckable(True);
        act_through.setChecked(self._mouse_through)
        self._through_actions.append(act_through)
        act_through.toggled.connect(self.set_mouse_through)
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