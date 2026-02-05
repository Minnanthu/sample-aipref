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

    # Workaround: OpenAI API rejects empty string for `messages[*].name` (HTTP 400).
    #
    # AIPerf's ChatEndpoint sets `name` from `turn.texts[0].name` on a fast-path. The `Text.name`
    # default is "", and AIPerf may also construct messages from previous model outputs that carry
    # an empty name. On OpenAI, that becomes a 400 error.
    #
    # AIPerf uses multiprocessing, so we need the workaround to apply in spawned child processes.
    # To do that, we install a small `.pth` startup hook into the active environment's site-packages,
    # which imports a patch module on interpreter startup (including workers).
    try:
        import site
        from pathlib import Path

        patch_module_name = "aiperf_drop_empty_name_patch"

        # Find the active site-packages directory containing aiperf.
        sp_candidates = []
        for sp in site.getsitepackages():
            sp_path = Path(sp)
            if (sp_path / "aiperf").exists():
                sp_candidates.append(sp_path)
        sp_dir = sp_candidates[0] if sp_candidates else None

        if sp_dir is not None:
            patch_py = sp_dir / f"{patch_module_name}.py"
            patch_pth = sp_dir / f"{patch_module_name}.pth"

            patch_code = """\
from __future__ import annotations

# Imported at interpreter startup via .pth to patch multiprocessing workers too.
#
# Important: importing `aiperf.endpoints.openai_chat` too early can fail due to aiperf's
# import order / config initialization. So we try to patch, and if it fails we install a
# one-shot import hook that patches as soon as the module becomes importable.

from typing import Any
import builtins
import sys


def _strip_empty_name(msg: dict[str, Any]) -> None:
    name = msg.get("name", None)
    if name is None or (isinstance(name, str) and name.strip() == ""):
        msg.pop("name", None)


def _apply_patch() -> bool:
    try:
        from aiperf.endpoints.openai_chat import ChatEndpoint  # type: ignore
    except Exception:
        return False

    if getattr(ChatEndpoint, "_sample_drop_empty_name_patched", False):
        return True
    ChatEndpoint._sample_drop_empty_name_patched = True

    _orig_set_message_content = ChatEndpoint._set_message_content
    _orig_format_payload = ChatEndpoint.format_payload

    def _patched_set_message_content(self, message, turn):  # type: ignore[no-redef]
        _orig_set_message_content(self, message, turn)
        if isinstance(message, dict):
            _strip_empty_name(message)

    def _patched_format_payload(self, request_info):  # type: ignore[no-redef]
        payload = _orig_format_payload(self, request_info)
        msgs = payload.get("messages")
        if isinstance(msgs, list):
            for m in msgs:
                if isinstance(m, dict):
                    _strip_empty_name(m)
        return payload

    ChatEndpoint._set_message_content = _patched_set_message_content  # type: ignore[assignment]
    ChatEndpoint.format_payload = _patched_format_payload  # type: ignore[assignment]
    return True


if not _apply_patch():
    _orig_import = builtins.__import__

    def _import_hook(name, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-redef]
        mod = _orig_import(name, globals, locals, fromlist, level)
        if "aiperf.endpoints.openai_chat" in sys.modules:
            if _apply_patch():
                builtins.__import__ = _orig_import
        return mod

    builtins.__import__ = _import_hook
"""

            # Write patch module / pth only if missing or different.
            if (not patch_py.exists()) or (patch_py.read_text(encoding="utf-8") != patch_code):
                patch_py.write_text(patch_code, encoding="utf-8")
            if (not patch_pth.exists()) or (patch_pth.read_text(encoding="utf-8").strip() != f"import {patch_module_name}"):
                patch_pth.write_text(f"import {patch_module_name}\n", encoding="utf-8")

            # Apply patch in the current process too.
            __import__(patch_module_name)
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

