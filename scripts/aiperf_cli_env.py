#!/usr/bin/env python3
"""
Run AIPerf CLI with Cyclopts Env config enabled.

Why:
- Upstream `aiperf` CLI is built on Cyclopts, which supports env vars via `cyclopts.config.Env`.
- The packaged `aiperf` CLI in this repo doesn't enable Env config by default, so env vars like
  `AIPERF_PROFILE_API_KEY` are not picked up unless we inject Env config.

This wrapper enables it without modifying site-packages.
"""

from __future__ import annotations


def main() -> None:
    from cyclopts.config import Env

    # Import the upstream CLI App
    from aiperf.cli import app

    # Workaround: OpenAI API rejects empty string for `messages[0].name` (HTTP 400).
    # AIPerf's ChatEndpoint hotfix may set `name` from `turn.texts[0].name`, which defaults to "".
    # We strip the field when it's empty/blank, without modifying site-packages.
    try:
        from aiperf.endpoints.openai_chat import ChatEndpoint  # type: ignore

        _orig_set_message_content = ChatEndpoint._set_message_content

        def _patched_set_message_content(self, message, turn):  # type: ignore[no-redef]
            _orig_set_message_content(self, message, turn)
            name = message.get("name", None)
            if name is None or (isinstance(name, str) and name.strip() == ""):
                message.pop("name", None)

        ChatEndpoint._set_message_content = _patched_set_message_content  # type: ignore[assignment]

        _orig_format_payload = ChatEndpoint.format_payload

        def _patched_format_payload(self, request_info):  # type: ignore[no-redef]
            payload = _orig_format_payload(self, request_info)
            msgs = payload.get("messages")
            if isinstance(msgs, list):
                for msg in msgs:
                    if not isinstance(msg, dict):
                        continue
                    name = msg.get("name", None)
                    if name is None or (isinstance(name, str) and name.strip() == ""):
                        msg.pop("name", None)
            return payload

        ChatEndpoint.format_payload = _patched_format_payload  # type: ignore[assignment]
    except Exception:
        # Best-effort patch; don't block CLI startup if upstream module layout changes.
        pass

    # Enable env var parsing:
    # - prefix: AIPERF_
    # - command: True => e.g. `profile` subcommand uses `AIPERF_PROFILE_*`
    #
    # In particular, `--api-key` becomes `AIPERF_PROFILE_API_KEY`.
    app._config = (Env(prefix="AIPERF_", command=True, show=False),)

    # Execute CLI
    app()


if __name__ == "__main__":
    main()

