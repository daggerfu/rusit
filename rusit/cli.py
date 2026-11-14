"""Command line interface for RUSIT utilities."""
from __future__ import annotations

import argparse
import json
from .corpus import build_demo_corpus, score_file
from .db import LexiconDB
from .translator import RusitTranslator
from .validator import RusitValidator


def _cmd_lexicon(args) -> int:
    if args.action == "init":
        json_path = args.params[0] if args.params else "rusit_lexicon.json"
        with LexiconDB(args.db) as db:
            db.import_json(json_path)
        print(f"База {args.db} создана из {json_path}")
        return 0
    if args.action == "export":
        if not args.params:
            print("lexicon export: не указан путь к JSON-файлу")
            return 2
        with LexiconDB(args.db) as db:
            db.export_json(args.params[0])
        print(f"Лексикон выгружен в {args.params[0]}")
        return 0
    if args.action == "add":
        if len(args.params) < 2:
            print("lexicon add: нужны <секция> <ключ> [значение]")
            return 2
        section, key = args.params[0], args.params[1]
        value = args.params[2] if len(args.params) > 2 else None
        with LexiconDB(args.db) as db:
            db.add(section, key, value)
        print(f"Добавлено: {section}: {key}" + (f" → {value}" if value else ""))
        return 0
    if args.action == "remove":
        if len(args.params) < 2:
            print("lexicon remove: нужны <секция> <ключ>")
            return 2
        with LexiconDB(args.db) as db:
            removed = db.remove(args.params[0], args.params[1])
        print("Удалено" if removed else "Статья не найдена")
        return 0
    if args.action == "list":
        with LexiconDB(args.db) as db:
            if args.params:
                print(json.dumps(
                    dict(db.entries(args.params[0])),
                    ensure_ascii=False, indent=2,
                ))
            else:
                print(json.dumps(db.sections(), ensure_ascii=False, indent=2))
        return 0
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rusit", description="RUSIT 3.0 utility toolkit")
    sub = parser.add_subparsers(dest="cmd", required=True)
    tr = sub.add_parser("translate", help="translate Russian text to RUSIT")
    tr.add_argument("text", nargs="*", help="text to translate; stdin is used if omitted")
    tr.add_argument("--db", help="путь к SQLite-базе лексикона")
    val = sub.add_parser("validate", help="validate RUSIT text")
    val.add_argument("text", nargs="*", help="text to validate; stdin is used if omitted")
    exp = sub.add_parser("explain", help="print token-level RUSIT labels as JSON")
    exp.add_argument("text", nargs="*", help="text to explain; stdin is used if omitted")
    corp = sub.add_parser("corpus", help="create or score a CSV corpus")
    corp.add_argument("action", choices=["demo", "score"])
    corp.add_argument("path")
    lex = sub.add_parser("lexicon", help="управление SQLite-базой лексикона")
    lex.add_argument("action", choices=["init", "export", "add", "remove", "list"])
    lex.add_argument("db")
    lex.add_argument("params", nargs="*", help="аргументы действия")
    args = parser.parse_args(argv)

    text = " ".join(getattr(args, "text", []) or []).strip()
    if hasattr(args, "text") and not text:
        import sys
        text = sys.stdin.read().strip()

    if args.cmd == "translate":
        translator = (
            RusitTranslator(db_path=args.db) if args.db
            else RusitTranslator()
        )
        print(translator.translate(text)); return 0
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
    if args.cmd == "lexicon":
        return _cmd_lexicon(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
