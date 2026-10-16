"""Single-process, nonblocking maintenance lock (separate from live worker)."""
from __future__ import annotations
import os
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def lock_maintenance(path: Path):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0)
        if os.name=="nt":
            import msvcrt
            try:
                msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
            except OSError:
                raise BlockingIOError("maintenance_already_running") from None
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
        else:
            import fcntl
            try:
                fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError:
                raise BlockingIOError("maintenance_already_running") from None
            try:
                yield
            finally:
                fcntl.flock(handle,fcntl.LOCK_UN)


def maintenance_active(path: Path) -> bool:
    try:
        with lock_maintenance(path):
            return False
    except BlockingIOError:
        return True
