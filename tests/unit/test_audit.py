from __future__ import annotations

from rosetta_bridge.codegen.audit import render_audit_log


def test_render_audit_log_has_header_and_rows() -> None:
    output = render_audit_log(
        [
            ("users", "email", "User email address"),
            ("users", "status", "Account status"),
        ]
    )

    assert "| Table | Original Column | Inferred Meaning |" in output
    assert "| users | email | User email address |" in output
