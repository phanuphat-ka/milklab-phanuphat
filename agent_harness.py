"""Compatibility entrypoint for running the agent harness from the repo root."""

from scripts.agent_harness import main


if __name__ == "__main__":
    raise SystemExit(main())
