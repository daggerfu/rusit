"""Command line interface for RUSIT utilities."""
from __future__ import annotations

import argparse
import json
from .corpus import build_demo_corpus, score_file
from .translator import RusitTranslator
from .validator import RusitValidator


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rusit", description="RUSIT 3.0 utility toolkit")
    sub = parser.add_subparsers(dest="cmd", required=True)
    tr = sub.add_parser("translate", help="translate Russian text to RUSIT")
    tr.add_argument("text", nargs="*", help="text to translate; stdin is used if omitted")
    val = sub.add_parser("validate", help="validate RUSIT text")
    val.add_argument("text", nargs="*", help="text to validate; stdin is used if omitted")
    exp = sub.add_parser("explain", help="print token-level RUSIT labels as JSON")
    exp.add_argument("text", nargs="*", help="text to explain; stdin is used if omitted")
    corp = sub.add_parser("corpus", help="create or score a CSV corpus")
    corp.add_argument("action", choices=["demo", "score"])
    corp.add_argument("path")
    args = parser.parse_args(argv)

    text = " ".join(getattr(args, "text", []) or []).strip()
    if hasattr(args, "text") and not text:
        import sys
        text = sys.stdin.read().strip()

    if args.cmd == "translate":
        print(RusitTranslator().translate(text)); return 0
    if args.cmd == "validate":
        result = RusitValidator().validate(text)
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return 0 if result.ok else 1
    if args.cmd == "explain":
        print(json.dumps(RusitValidator().explain(text), ensure_ascii=False, indent=2)); return 0
    if args.cmd == "corpus" and args.action == "demo":
        build_demo_corpus(args.path); return 0
    if args.cmd == "corpus" and args.action == "score":
        print(json.dumps(score_file(args.path), ensure_ascii=False, indent=2)); return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
