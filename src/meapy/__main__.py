"""meapy CLI entrypoint.

Invoked as ``python -m meapy`` (and by the Docker image's ENTRYPOINT). Keeps
the surface intentionally tiny: ``--version`` for version info and ``--help``
for usage. Add subcommands here if/when the package grows a richer CLI.
"""

from __future__ import annotations

import argparse
import sys

from meapy import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="meapy",
        description="MEA Carbon Capture Process Analysis Library",
    )
    parser.add_argument("--version", action="version", version=f"meapy {__version__}")
    parser.parse_args(argv)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
