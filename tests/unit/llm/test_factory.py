from __future__ import annotations

from pathlib import Path

from bim_intelligence.config import Settings
from bim_intelligence.llm.client import ReplayClient
from bim_intelligence.llm.factory import create_client


def test_off_mode_constructs_no_client_without_key() -> None:
    assert create_client(Settings()) is None


def test_replay_mode_needs_no_key_or_network(tmp_path: Path) -> None:
    client = create_client(Settings(llm_mode="replay", llm_recordings_dir=tmp_path / "recordings"))
    assert isinstance(client, ReplayClient)
