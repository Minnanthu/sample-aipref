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

