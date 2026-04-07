"""Thread-aware log capture for real-time pipeline log streaming.

Replaces sys.stdout / sys.stderr with wrappers that tee output to
per-thread queues. Only threads that explicitly register a queue
will have their output captured — all other threads are unaffected.

Usage:
    import queue
    from engine_v2.api.log_capture import install, register_thread, unregister_thread

    install()  # Call once at startup

    q = queue.Queue()
    register_thread(q)      # Start capturing in current thread
    ...                      # stdout/stderr from this thread goes to q
    unregister_thread()      # Stop capturing
"""

from __future__ import annotations

import queue
import re
import sys
import threading
from typing import TextIO


class _StreamTee:
    """Wraps a stream to tee output to per-thread queues.

    Only registered threads have output captured.
    All output still flows to the original stream.
    """

    def __init__(self, original: TextIO) -> None:
        self._original = original
        self._queues: dict[int, queue.Queue] = {}
        self._lock = threading.Lock()

    def register(self, q: queue.Queue) -> None:
        """Register current thread for output capture."""
        tid = threading.current_thread().ident
        if tid is not None:
            with self._lock:
                self._queues[tid] = q

    def unregister(self) -> None:
        """Unregister current thread from output capture."""
        tid = threading.current_thread().ident
        if tid is not None:
            with self._lock:
                self._queues.pop(tid, None)

    def write(self, data: str) -> int:
        result = self._original.write(data)
        if data and data.strip():
            tid = threading.current_thread().ident
            with self._lock:
                q = self._queues.get(tid)  # type: ignore[arg-type]
            if q:
                # Clean up tqdm carriage returns for streaming
                cleaned = data.replace("\r", "").strip()
                if cleaned:
                    try:
                        q.put_nowait(cleaned)
                    except queue.Full:
                        pass  # Drop if buffer is full
        return result

    def flush(self) -> None:
        self._original.flush()

    def isatty(self) -> bool:
        return self._original.isatty()

    def fileno(self) -> int:
        return self._original.fileno()

    @property
    def encoding(self) -> str:
        return self._original.encoding

    def __getattr__(self, name: str):
        return getattr(self._original, name)


# Module-level singletons
_stderr_tee: _StreamTee | None = None
_stdout_tee: _StreamTee | None = None
_installed = False


def install() -> None:
    """Install thread-aware stream captures. Call once at app startup."""
    global _stderr_tee, _stdout_tee, _installed
    if _installed:
        return
    _stderr_tee = _StreamTee(sys.stderr)
    _stdout_tee = _StreamTee(sys.stdout)
    sys.stderr = _stderr_tee  # type: ignore[assignment]
    sys.stdout = _stdout_tee  # type: ignore[assignment]
    _installed = True


def register_thread(q: queue.Queue) -> None:
    """Register current thread for log capture."""
    if _stderr_tee:
        _stderr_tee.register(q)
    if _stdout_tee:
        _stdout_tee.register(q)


def unregister_thread() -> None:
    """Unregister current thread from log capture."""
    if _stderr_tee:
        _stderr_tee.unregister()
    if _stdout_tee:
        _stdout_tee.unregister()


# ── tqdm line dedup ─────────────────────────────────────────────
# tqdm emits many updates per second. We only forward "significant"
# changes (percentage changed by >= 5 or reached 100%).

_TQDM_RE = re.compile(r"(\d+)%\|")
_last_tqdm: dict[int, dict[str, int]] = {}  # tid -> {prefix: last_pct}


def is_significant_tqdm(line: str) -> bool:
    """Return True if a tqdm line represents a significant update."""
    m = _TQDM_RE.search(line)
    if not m:
        return True  # Not a tqdm line — always forward
    pct = int(m.group(1))
    prefix = line[:m.start()].strip()
    tid = threading.current_thread().ident or 0
    if tid not in _last_tqdm:
        _last_tqdm[tid] = {}
    last = _last_tqdm[tid].get(prefix, -1)
    if pct >= 100 or pct - last >= 5:
        _last_tqdm[tid][prefix] = pct
        return True
    return False
