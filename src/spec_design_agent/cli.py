# ABOUTME: Command-line entrypoint. `spec-design-agent spec --request <file>` runs one bounded
# ABOUTME: Spec & Design job and prints a single JSON result to stdout. Logs go to stderr.

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .logging_ import error_message
from .run import run_spec_design
from .types import RequestValidationError

USAGE = """spec-design-agent spec --request <path> [--provider <name>] [--model <id>]

Exit codes:
  0   spec_ready       spec.md committed, ready for human Design Review
  10  needs_decision   a material decision is missing
  20  blocked          an input/integrity/access/environment precondition failed
  30  failed           an unexpected execution failure occurred
  2   usage error
  1   internal error"""


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    parser = argparse.ArgumentParser(prog="spec-design-agent", add_help=False)
    parser.add_argument("command", nargs="?")
    parser.add_argument("--request")
    parser.add_argument("--provider")
    parser.add_argument("--model")
    parser.add_argument("-h", "--help", action="store_true")
    args, _unknown = parser.parse_known_args(argv)

    if args.help:
        print(USAGE)
        return 0
    if args.command != "spec" or not args.request:
        print(USAGE, file=sys.stderr)
        return 2

    try:
        raw_request = json.loads(Path(args.request).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"Cannot read request file: {error_message(error)}", file=sys.stderr)
        return 2

    from .config import load_config

    try:
        cfg = load_config(provider=args.provider, model=args.model)
        outcome = run_spec_design(raw_request, config=cfg)
    except RequestValidationError as error:
        print(json.dumps({"status": "blocked", "error": "invalid_request", "details": error.errors}, indent=2))
        return 2
    except Exception as error:  # noqa: BLE001
        print(error_message(error), file=sys.stderr)
        return 1

    print(json.dumps(outcome.result.to_json(), indent=2))
    return outcome.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
