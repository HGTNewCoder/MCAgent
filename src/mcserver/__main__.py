"""Allow ``python -m mcserver``."""

from mcserver.cli.main import main

if __name__ == "__main__":
    raise SystemExit(main())
