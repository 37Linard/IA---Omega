import logging
import os
import threading
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

log = logging.getLogger(__name__)

WATCH_DIR = os.path.join(os.path.dirname(__file__), "workspace")
PDF_EXT   = ".pdf"

# Debounce: evita re-indexar arquivo que ainda está sendo escrito
_pending: dict[str, float] = {}
_lock = threading.Lock()
_DEBOUNCE = 2.0  # segundos


class _Handler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            self._schedule(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._schedule(event.dest_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._schedule(event.src_path)

    def _schedule(self, path: str):
        if not path.lower().endswith(PDF_EXT):
            return
        with _lock:
            _pending[path] = time.monotonic()


def _debounce_loop():
    """Thread que processa PDFs pendentes após debounce."""
    while True:
        time.sleep(0.5)
        now = time.monotonic()
        to_process = []
        with _lock:
            for path, ts in list(_pending.items()):
                if now - ts >= _DEBOUNCE:
                    to_process.append(path)
                    del _pending[path]

        for path in to_process:
            if not os.path.isfile(path):
                continue
            fname = os.path.basename(path)
            log.info("WATCHER: novo PDF detectado → %s", fname)
            try:
                from rag import get_rag_index
                result = get_rag_index().index_pdf(path)
                log.info("WATCHER: indexado %s — %s", fname, result)
            except Exception as e:
                log.warning("WATCHER: erro ao indexar %s — %s", fname, e)


_observer: Observer | None = None


def start():
    global _observer
    if _observer is not None:
        return

    os.makedirs(WATCH_DIR, exist_ok=True)

    _observer = Observer()
    _observer.schedule(_Handler(), WATCH_DIR, recursive=False)
    _observer.start()

    t = threading.Thread(target=_debounce_loop, daemon=True)
    t.start()

    log.info("WATCHER: monitorando %s", WATCH_DIR)


def stop():
    global _observer
    if _observer:
        _observer.stop()
        _observer.join()
        _observer = None
