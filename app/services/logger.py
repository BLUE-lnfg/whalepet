import sys
from collections import deque
from datetime import datetime
from PySide6.QtCore import QObject, Signal
from app.constants import LOG_DIR

class LogBus(QObject):
    log_emitted = Signal(str)
    def __init__(self):
        super().__init__()
        self._history = deque(maxlen=2000)
    def emit_line(self, line: str):
        self._history.append(line)
        self.log_emitted.emit(line)
    def history(self): return list(self._history)

_bus = None
def bus() -> LogBus:
    global _bus
    if _bus is None: _bus = LogBus()
    return _bus

class _TeeWriter:
    def __init__(self, original, is_stderr=False):
        self._original = original
        self._buffer = ""
    def write(self, text: str) -> int:
        if not text: return 0
        if self._original:
            try: self._original.write(text); self._original.flush()
            except Exception: pass
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line: self._emit(line)
        return len(text)
    def _emit(self, line: str):
        ts = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{ts}] {line}"
        bus().emit_line(formatted)
    def flush(self):
        if self._original:
            try: self._original.flush()
            except Exception: pass

def install_logger():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    bus()
    sys.stdout = _TeeWriter(sys.stdout)
    sys.stderr = _TeeWriter(sys.stderr, True)