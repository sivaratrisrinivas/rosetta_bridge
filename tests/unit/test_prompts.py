from __future__ import annotations

from rosetta_bridge.inference.prompts import build_user_prompt, get_system_prompt


def test_system_prompt_has_role() -> None:
    prompt = get_system_prompt()
    assert "Data Architect" in prompt


def test_user_prompt_scrubs_pii_samples() -> None:
    columns = [
        {"name": "email", "type": "varchar", "samples": ["a@example.com", "b@example.com"]},
        {"name": "status", "type": "varchar", "samples": ["active", "closed"]},
    ]

    prompt = build_user_prompt("users", columns, scrub_pii=True)

    assert "a@example.com" not in prompt
    assert "b@example.com" not in prompt
    assert "active" in prompt
    assert "closed" in prompt

