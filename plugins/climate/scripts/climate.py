#!/usr/bin/env python3

import sys


MIN_PYTHON = (3, 10)


def main() -> int:
    if sys.version_info < MIN_PYTHON:
        sys.stderr.write(
            "Climate requires Python 3.10 or newer. "
            "Use python3, python, or py -3 with a supported Python 3 installation.\n"
        )
        return 1

    from climate_plugin.cli import main as cli_main

    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
