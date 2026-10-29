"""Non-blocking exclusive file locks from the standard library (ADR-017).

``fcntl.flock`` on POSIX and ``msvcrt.locking`` on Windows both conflict between two separate
``open()`` calls on the same file, whether those calls come from two threads of one process or
from two processes. That is the property the session store relies on to serialise model
publication. POSIX ``lockf`` record locks are deliberately *not* used: they are per process and
would let two request threads hold the "same" lock at once.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import TracebackType

if sys.platform == "win32":
    import msvcrt

    def _try_lock(fd: int) -> bool:
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError:
            return False
        return True

    def _unlock(fd: int) -> None:
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _try_lock(fd: int) -> bool:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return False
        return True

    def _unlock(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_UN)


class FileLock:
    """An exclusive advisory lock on ``path``; ``acquire()`` never waits.

    The lock file is created on first use and is never deleted: removing a lock file while
    another holder has it open is the classic way to break file locks.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._fd: int | None = None

    @property
    def held(self) -> bool:
        return self._fd is not None

    def acquire(self) -> bool:
        """Take the lock if it is free; return ``False`` immediately if another holder has it."""
        if self._fd is not None:
            raise RuntimeError("FileLock is already held by this object.")
        fd = os.open(self._path, os.O_RDWR | os.O_CREAT, 0o644)
        if not _try_lock(fd):
            os.close(fd)
            return False
        self._fd = fd
        return True

    def release(self) -> None:
        if self._fd is None:
            return
        try:
            _unlock(self._fd)
        finally:
            os.close(self._fd)
            self._fd = None

    def __enter__(self) -> FileLock:
        if not self.acquire():
            raise BlockingIOError(f"Lock {self._path.name!r} is held elsewhere.")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.release()
