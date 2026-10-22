from typing import Callable

from PySide6.QtCore import QObject

from app.config.manager import ConfigManager


class ConfigBinder(QObject):
    """把一组 config key 绑定到回调。"""

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config
        self._handlers: dict[str, list[Callable[[str], None]]] = {}
        config.changed.connect(self._dispatch)

    def bind(self, keys, callback: Callable[[str], None]) -> "ConfigBinder":
        if isinstance(keys, str):
            keys = [keys]
        for k in keys:
            self._handlers.setdefault(k, []).append(callback)
        return self

    def _dispatch(self, key: str):
        for cb in self._handlers.get(key, ()):
            try:
                cb(key)
            except Exception as e:
                print(f"[binder] 处理 {key} 时出错：{e}")