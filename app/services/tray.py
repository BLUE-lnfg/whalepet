from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtWidgets import QSystemTrayIcon, QMenu


class PetTray(QSystemTrayIcon):
    # 自定义信号：通知主程序打开设置面板
    settings_requested = Signal()

    def __init__(self, app, pet_window):
        super().__init__(self._make_icon())
        self._app = app
        self._pet = pet_window

        # 构建托盘右键菜单
        menu = QMenu()

        # 1. 显示/隐藏
        act_show = menu.addAction("显示桌宠")
        act_hide = menu.addAction("隐藏桌宠")
        menu.addSeparator()

        # 2. 鼠标穿透（注册给 PetWindow 统一管理状态）
        act_through = menu.addAction("鼠标穿透")
        act_through.setCheckable(True)
        self._pet.add_through_action(act_through)
        menu.addSeparator()

        # 3. 设置
        act_settings = menu.addAction("设置...")
        act_settings.triggered.connect(self.settings_requested.emit)

        menu.addSeparator()

        # 4. 退出
        act_quit = menu.addAction("退出")

        # 绑定事件
        act_show.triggered.connect(self._show_pet)
        act_hide.triggered.connect(self._pet.hide)
        act_quit.triggered.connect(self._quit)

        self.setContextMenu(menu)
        self.setToolTip("鲸鱼娘桌宠")

    def _show_pet(self):
        self._pet.show()
        self._pet.raise_()
        self._pet.activateWindow()

    def _quit(self):
        self.hide()
        self._app.quit()

    def _make_icon(self) -> QIcon:
        """绘制一个蓝色的圆形图标作为托盘图标"""
        pix = QPixmap(64, 64)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(80, 160, 255))
        p.drawEllipse(QRectF(8, 8, 48, 48))
        p.end()
        return QIcon(pix)