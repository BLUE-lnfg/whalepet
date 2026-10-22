import sys
from collections import deque
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from app.constants import LOG_DIR

MAX_MEMORY_LINES = 2000
MAX_LOG_FILES = 20


class LogBus(QObject):
    log_emitted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._history: deque[str] = deque(maxlen=MAX_MEMORY_LINES)

    def emit_line(self, line: str):
        self._history.append(line)
        self.log_emitted.emit(line)

    def history(self) -> list[str]:
        return list(self._history)


_bus: LogBus | None = None


def bus() -> LogBus:
    global _bus
    if _bus is None:
        _bus = LogBus()
    return _bus


def _classify(text: str) -> str:
    lowered = text.lower()
    if any(k in lowered for k in ("error", "traceback", "exception", "失败", "错误", "严重")):
        return "ERROR"
    if any(k in lowered for k in ("warn", "警告", "过期", "跳过")):
        return "WARN"
    return "INFO"


class _TeeWriter:
    def __init__(self, original, file_handle, is_stderr: bool):
        self._original = original
        self._file = file_handle
        self._is_stderr = is_stderr
        self._buffer = ""

    def write(self, text: str) -> int:
        if not text:
            return 0
        if self._original is not None:
            try:
                self._original.write(text)
                self._original.flush()
            except Exception:
                pass
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line:
                self._emit(line)
        return len(text)

    def _emit(self, line: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        level = _classify(line)
        formatted = f"[{timestamp}] [{level}] {line}"
        if self._file is not None:
            try:
                self._file.write(formatted + "\n")
                self._file.flush()
            except Exception:
                pass
        bus().emit_line(formatted)

    def flush(self):
        if self._original is not None:
            try:
                self._original.flush()
            except Exception:
                pass
        if self._file is not None:
            try:
                self._file.flush()
            except Exception:
                pass

    def isatty(self) -> bool:
        return False


_installed = False
_log_file = None


def _prune_old_logs(keep: int = MAX_LOG_FILES):
    try:
        files = sorted(
            LOG_DIR.glob("session_*.log"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in files[keep:]:
            try:
                old.unlink()
            except Exception:
                pass
    except Exception:
        pass


def install_logger() -> Path | None:
    global _installed, _log_file
    if _installed:
        return None

    log_path: Path | None = None
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        session = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = LOG_DIR / f"session_{session}.log"
        _log_file = open(log_path, "w", encoding="utf-8")
        _prune_old_logs()
    except Exception:
        _log_file = None

    bus()

    orig_out = sys.stdout
    orig_err = sys.stderr
    sys.stdout = _TeeWriter(orig_out, _log_file, is_stderr=False)
    sys.stderr = _TeeWriter(orig_err, _log_file, is_stderr=True)

    _installed = True
    return log_path


def shutdown_logger():
    global _log_file
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception:
        pass
    if _log_file is not None:
        try:
            _log_file.close()
        except Exception:
            pass
        _log_file = None


def current_log_path() -> Path | None:
    return Path(_log_file.name) if _log_file is not None else None