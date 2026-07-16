"""Backward-compatible GUI shim — prefer ``uv run mcserver-gui``."""

from mcserver.cli.gui import main

if __name__ == "__main__":
    main()
