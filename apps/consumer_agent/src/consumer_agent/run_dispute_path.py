from __future__ import annotations

import json

from .flow import run_dispute_flow


def run() -> dict:
    return run_dispute_flow()


def main() -> None:
    result = run()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
