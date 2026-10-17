"""Offline contract tests for personalized lyrics sent through the live Music adapter."""
from types import SimpleNamespace

import pytest

from app import main as api
from app import queue


def test_inline_lyrics_and_title_forwarded_to_probe(monkeypatch):
    calls = []
    monkeypatch.setattr(queue.profiles, "invalidate_snapshot", lambda profile: None)
    monkeypatch.setattr(queue, "verified_artifacts", lambda _id, profile: [{"sha256": "a" * 64}])
    monkeypatch.setattr(queue, "finish", lambda *args, **kwargs: calls.append(("finished", args, kwargs)))
    monkeypatch.setattr(queue, "event", lambda *args, **kwargs: None)
    record = {
        "id": "fixture-job",
        "request_id": "natal-test-001",
        "account_profile": "default",
        "payload": __import__("json").dumps({
            "account_profile": "default",
            "prompt": "Joyful Christmas music",
            "model": "Lyria 3.5",
            "duration_seconds": 75,
            "output_format": "wav",
            "instrumental": False,
            "lyrics": "[Verse]\nBom dia, Ana",
            "title": "A Magia do Natal",
        }),
    }

    def fake_runner(command, **kwargs):
        calls.append(("command", command))
        return SimpleNamespace(returncode=0)

    queue.process(record, runner=fake_runner)
    command = next(item[1] for item in calls if item[0] == "command")
    assert command[command.index("--lyrics") + 1] == "[Verse]\nBom dia, Ana"
    assert command[command.index("--title") + 1] == "A Magia do Natal"
    assert any(item[0] == "finished" and item[1][1] == "completed" for item in calls)


def test_lyrics_are_inline_and_not_instrumental():
    basic = {"request_id": "natal-test-001", "prompt": "Christmas", "lyrics": "Bom dia"}
    with pytest.raises(ValueError):
        api.MusicRequest(**{**basic, "duration_seconds": 25})
    assert api.MusicRequest(**basic).lyrics == "Bom dia"
