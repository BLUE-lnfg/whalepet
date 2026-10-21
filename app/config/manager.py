import json
from pathlib import Path

from PySide6.QtCore import QObject, Signal

# 配置结构版本号。改了 config 结构（删/改名/改语义）就 +1，并在 _migrate 里加迁移逻辑
CURRENT_SCHEMA = 1


class ConfigManager(QObject):
    changed = Signal(str)

    def __init__(self, path: Path):
        super().__init__()
        self._path = path
        self._data: dict = {}
        self.load()

    def load(self):
        if not self._path.exists():
            self._data = {"schema": CURRENT_SCHEMA}
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._data = data if isinstance(data, dict) else {}
        except Exception as e:
            print(f"[config] 读取失败：{e}，使用空配置")
            self._data = {}
        self._migrate()

    def _migrate(self):
        """把旧版本配置升级到 CURRENT_SCHEMA。每次结构变化只加一步，历史迁移永远保留。"""
        old = int(self._data.get("schema", 0))
        if old == CURRENT_SCHEMA:
            return

        if old < 1:
            # 从 v0（无 schema 字段）升级到 v1：
            # 1) 删掉废弃的 chatter.* 段（被 voice.* 取代）
            self._data.pop("chatter", None)
            # 2) 其它历史遗留清理，按需加
            pass

        self._data["schema"] = CURRENT_SCHEMA
        self.save()
        print(f"[config] 已从 schema {old} 迁移到 {CURRENT_SCHEMA}")

    def save(self):
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"[config] 保存失败：{e}")

    def get(self, key: str, default=None):
        node = self._data
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, key: str, value):
        parts = key.split(".")
        node = self._data
        for part in parts[:-1]:
            if not isinstance(node.get(part), dict):
                node[part] = {}
            node = node[part]
        node[parts[-1]] = value
        self.save()
        self.changed.emit(key)