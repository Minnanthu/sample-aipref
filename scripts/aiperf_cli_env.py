#!/usr/bin/env python3
"""
Cyclopts の Env 設定を有効化した状態で AIPerf CLI を実行するラッパーです。

目的:
- 上流の `aiperf` CLI は Cyclopts 製で、`cyclopts.config.Env` により環境変数からの設定読み込みに対応しています。
- しかし、このリポジトリで使う `aiperf` 実行では Env 設定が有効になっていないケースがあり、
  `AIPERF_PROFILE_API_KEY` のような環境変数が反映されないことがあります。

このラッパーは、site-packages を直接書き換えずに Env 設定を有効化します。
"""

from __future__ import annotations


def main() -> None:
    from cyclopts.config import Env

    # 上流の CLI App を import
    from aiperf.cli import app

    # 回避策: OpenAI API は `messages[*].name` が空文字だと 400 を返します。
    #
    # AIPerf の ChatEndpoint には高速経路があり、`turn.texts[0].name` をそのまま `name` に入れます。
    # ところが `Text.name` のデフォルトは ""（空文字）で、さらに AIPerf は過去のモデル出力から
    # message を再構築する際に空の name を持ち回る場合があります。OpenAI ではこれが 400 になります。
    #
    # AIPerf は multiprocessing を使うため、親プロセスだけでなく spawn された子プロセス（worker）にも
    # 回避策が適用される必要があります。そこで、実行中の環境の site-packages に `.pth` を置き、
    # Python 起動時（worker 含む）にパッチモジュールが自動 import されるようにしています。
    try:
        import site
        from pathlib import Path

        patch_module_name = "aiperf_drop_empty_name_patch"

        # aiperf が入っている site-packages を特定
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

# `.pth` 経由で Python 起動時に import され、multiprocessing の子プロセス（worker）にもパッチを当てます。
#
# 注意: `aiperf.endpoints.openai_chat` を早い段階で import すると、AIPerf 側の import 順/設定初期化の関係で
# 失敗することがあります。まずは素直にパッチ適用を試み、失敗した場合は import hook を入れて
# モジュールが import 可能になったタイミングで一度だけパッチを適用します。

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

            # パッチモジュール / pth は、無い場合または内容が変わった場合のみ書き込みます。
            if (not patch_py.exists()) or (patch_py.read_text(encoding="utf-8") != patch_code):
                patch_py.write_text(patch_code, encoding="utf-8")
            if (not patch_pth.exists()) or (patch_pth.read_text(encoding="utf-8").strip() != f"import {patch_module_name}"):
                patch_pth.write_text(f"import {patch_module_name}\n", encoding="utf-8")

            # 現在のプロセスにも即時適用します。
            __import__(patch_module_name)
    except Exception:
        # ベストエフォート: 上流の構成が変わっても CLI 起動を止めない。
        pass

    # 環境変数からの設定読み込みを有効化:
    # - prefix: AIPERF_
    # - command: True => 例: `profile` サブコマンドは `AIPERF_PROFILE_*` を使用
    #
    # In particular, `--api-key` becomes `AIPERF_PROFILE_API_KEY`.
    app._config = (Env(prefix="AIPERF_", command=True, show=False),)

    # CLI 実行
    app()


if __name__ == "__main__":
    main()

