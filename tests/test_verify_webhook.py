"""Tests for the verify_webhook re-export and the ColonyVerifyWebhook tool."""

from __future__ import annotations

import hashlib
import hmac
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crewai_colony import ColonyVerifyWebhook, verify_webhook


def _sign(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


SECRET = "shh-this-is-a-shared-secret"
PAYLOAD = b'{"event":"post_created","post":{"id":"p1","title":"Hello"}}'


# ── Re-export ──────────────────────────────────────────────────────


class TestReExport:
    def test_is_sdk_function(self) -> None:
        """``crewai_colony.verify_webhook`` *is* the SDK function — no
        wrapper. We re-export rather than re-implement so callers
        automatically pick up SDK security fixes."""
        from colony_sdk import verify_webhook as sdk_fn

        assert verify_webhook is sdk_fn

    def test_valid_signature(self) -> None:
        sig = _sign(PAYLOAD, SECRET)
        assert verify_webhook(PAYLOAD, sig, SECRET) is True

    def test_invalid_signature(self) -> None:
        assert verify_webhook(PAYLOAD, "deadbeef" * 8, SECRET) is False

    def test_signature_with_sha256_prefix(self) -> None:
        """Frameworks that normalise to ``sha256=<hex>`` should still work."""
        sig = _sign(PAYLOAD, SECRET)
        assert verify_webhook(PAYLOAD, f"sha256={sig}", SECRET) is True

    def test_str_payload(self) -> None:
        body = '{"event":"post_created"}'
        sig = _sign(body.encode(), SECRET)
        assert verify_webhook(body, sig, SECRET) is True


# ── Tool wrapper ───────────────────────────────────────────────────


class TestColonyVerifyWebhookTool:
    def test_in_package_namespace(self) -> None:
        """Importable from the package root, not just from .tools."""
        from crewai_colony import ColonyVerifyWebhook as Imported

        assert Imported is ColonyVerifyWebhook

    def test_not_in_default_toolkit(self) -> None:
        """Verification doesn't need an authenticated client, so it's a
        standalone tool — same pattern as ColonyRegister. It must NOT be
        in ALL_TOOLS so that ``ColonyToolkit().get_tools()`` doesn't
        include it (would force a non-applicable secret param)."""
        from crewai_colony.tools import ALL_TOOLS

        assert ColonyVerifyWebhook not in ALL_TOOLS

    def test_run_valid(self) -> None:
        sig = _sign(PAYLOAD, SECRET)
        tool = ColonyVerifyWebhook()
        result = tool._run(payload=PAYLOAD.decode(), signature=sig, secret=SECRET)
        assert "valid" in result.lower()
        assert result.startswith("OK")

    def test_run_invalid(self) -> None:
        tool = ColonyVerifyWebhook()
        result = tool._run(payload=PAYLOAD.decode(), signature="deadbeef" * 8, secret=SECRET)
        assert "invalid" in result.lower()
        assert result.startswith("Error")

    def test_run_with_sha256_prefix(self) -> None:
        sig = _sign(PAYLOAD, SECRET)
        tool = ColonyVerifyWebhook()
        result = tool._run(payload=PAYLOAD.decode(), signature=f"sha256={sig}", secret=SECRET)
        assert result.startswith("OK")

    def test_run_handles_unexpected_error(self) -> None:
        """If the underlying ``verify_webhook`` raises (e.g. exotic input),
        the tool catches it and formats the message rather than crashing
        the crew run."""
        tool = ColonyVerifyWebhook()
        with patch("crewai_colony.tools.verify_webhook", side_effect=ValueError("bad payload")):
            result = tool._run(payload="x", signature="y", secret="z")
        assert "Error" in result
        assert "bad payload" in result

    async def test_arun_valid(self) -> None:
        sig = _sign(PAYLOAD, SECRET)
        tool = ColonyVerifyWebhook()
        result = await tool._arun(payload=PAYLOAD.decode(), signature=sig, secret=SECRET)
        assert result.startswith("OK")

    async def test_arun_invalid(self) -> None:
        tool = ColonyVerifyWebhook()
        result = await tool._arun(payload=PAYLOAD.decode(), signature="0" * 64, secret=SECRET)
        assert result.startswith("Error")
