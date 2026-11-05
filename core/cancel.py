import os
import threading
from pathlib import Path
from typing import Iterable, List, Optional


class ProcessCancelled(Exception):
    """Dilempar ketika pengguna membatalkan proses yang sedang berjalan."""


def check_cancel(cancel_event: Optional[threading.Event]) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise ProcessCancelled()


# --- Registry folder yang sedang diproses -----------------------------------
_lock = threading.Lock()
_active: dict = {}


def _key(path) -> str:
    # normcase supaya di Windows "C:\\Foto" dan "c:\\foto" dianggap folder yang sama
    return os.path.normcase(os.path.realpath(str(path)))


def is_folder_active(path) -> bool:
    with _lock:
        return _key(path) in _active


def claim_folders(paths: Iterable[Path]) -> List[Path]:
    """Tandai folder sebagai 'sedang diproses'.

    Semua-atau-tidak-sama-sekali: kalau ada satu saja folder yang sudah aktif,
    tidak ada folder yang ditandai dan daftar folder yang bentrok dikembalikan.
    Mengembalikan list kosong kalau semua berhasil di-claim.
    """
    paths = list(paths)
    with _lock:
        busy = [p for p in paths if _key(p) in _active]
        if busy:
            return busy
        for p in paths:
            _active[_key(p)] = str(p)
    return []


def release_folders(paths: Iterable[Path]) -> None:
    with _lock:
        for p in paths:
            _active.pop(_key(p), None)
