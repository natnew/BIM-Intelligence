"""``FileLock``: exclusive and non-blocking on both platforms CI runs (ADR-017)."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from bim_intelligence.store.locking import FileLock


def test_second_acquire_from_another_handle_fails_immediately(tmp_path: Path) -> None:
    path = tmp_path / "x.lock"
    first, second = FileLock(path), FileLock(path)
    assert first.acquire() is True
    assert first.held
    assert second.acquire() is False
    assert not second.held
    first.release()
    assert not first.held
    assert second.acquire() is True
    second.release()


def test_lock_conflicts_across_threads(tmp_path: Path) -> None:
    path = tmp_path / "x.lock"
    results: list[bool] = []
    with FileLock(path):
        thread = threading.Thread(target=lambda: results.append(FileLock(path).acquire()))
        thread.start()
        thread.join(timeout=10)
    assert results == [False]


def test_context_manager_raises_when_held_elsewhere(tmp_path: Path) -> None:
    path = tmp_path / "x.lock"
    with FileLock(path), pytest.raises(BlockingIOError), FileLock(path):
        pass


def test_double_acquire_on_one_object_is_a_programming_error(tmp_path: Path) -> None:
    lock = FileLock(tmp_path / "x.lock")
    assert lock.acquire()
    with pytest.raises(RuntimeError):
        lock.acquire()
    lock.release()
    lock.release()  # idempotent


def test_lock_file_persists_after_release(tmp_path: Path) -> None:
    path = tmp_path / "x.lock"
    with FileLock(path):
        assert path.exists()
    assert path.exists(), "deleting lock files is how file locks break"
