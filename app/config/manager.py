import json
from pathlib import Path
from PySide6.QtCore import QObject, Signal

CURRENT_SCHEMA = 1

class ConfigManager(QObject):
    changed = Signal(str)

    def __init__(self, path: Path):
        super().__init__()
        self._path = path
        self._data = {}
        self.load()

    def load(self):
        if not self._path.exists():
            self._data = {"schema": CURRENT_SCHEMA}
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._data = data if isinstance(data, dict) else {}
        except Exception:
            self._data = {}
        self._migrate()

    def _migrate(self):
        old = int(self._data.get("schema", 0))
        if old == CURRENT_SCHEMA: return
        if old < 1: self._data.pop("chatter", None)
        self._data["schema"] = CURRENT_SCHEMA
        self.save()

    def save(self):
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception: pass

    def get(self, key: str, default=None):
        node = self._data
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node: return default
            node = node[part]
        return node

    def set(self, key: str, value):
        parts = key.split(".")
        node = self._data
        for part in parts[:-1]:
            if not isinstance(node.get(part), dict): node[part] = {}
            node = node[part]
        old = node.get(parts[-1])
        node[parts[-1]] = value
        self.save()
        if old != value:
            print(f"[config] {key} = {value!r}（原值 {old!r}）")
            self.changed.emit(key)