"""Command line interface for RUSIT utilities."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from .corpus import build_demo_corpus, score_file
from .db import LexiconDB
from .markdown import looks_like_markdown, translate_markdown
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
    parser = argparse.ArgumentParser(prog="rusit", description="RUSIT 5.3.1 utility toolkit")
    sub = parser.add_subparsers(dest="cmd", required=True)
    tr = sub.add_parser("translate", help="translate Russian text to RUSIT")
    tr.add_argument("text", nargs="*", help="text to translate; stdin is used if omitted")
    tr.add_argument(
        "-i", "--input", "--input-file", "--from-file",
        dest="input", metavar="PATH",
        help="читать текст из файла ('-' — stdin)",
    )
    tr.add_argument(
        "-o", "--output", "--output-file", "--to-file",
        dest="output", metavar="PATH",
        help="записать перевод в файл ('-' — stdout)",
    )
    tr.add_argument(
        "--format", choices=["auto", "text", "markdown"], default="auto",
        help="формат документа: auto (по расширению/содержимому), "
             "text или markdown",
    )
    tr.add_argument(
        "--markdown", dest="format", action="store_const",
        const="markdown", default=argparse.SUPPRESS,
        help="то же, что --format markdown",
    )
    tr.add_argument("--db", help="путь к SQLite-базе лексикона")
    tr.add_argument(
        "--spacy", action="store_true", default=True,
        help="использовать spaCy (по умолчанию)",
    )
    tr.add_argument(
        "--no-spacy", dest="spacy", action="store_false",
        help="отключить spaCy и использовать только pymorphy3",
    )
    tr.add_argument(
        "--spacy-model", default="ru_core_news_sm",
        help="имя spaCy-модели (по умолчанию: ru_core_news_sm)",
    )
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
    repl = sub.add_parser(
        "repl", aliases=["echo"],
        help="интерактивный режим: русский → РУСИТ построчно",
    )
    repl.add_argument("--db", help="путь к SQLite-базе лексикона")
    repl.add_argument(
        "--spacy", action="store_true", default=True,
        help="использовать spaCy (по умолчанию)",
    )
    repl.add_argument(
        "--no-spacy", dest="spacy", action="store_false",
        help="отключить spaCy и использовать только pymorphy3",
    )
    repl.add_argument(
        "--spacy-model", default="ru_core_news_sm",
        help="имя spaCy-модели (по умолчанию: ru_core_news_sm)",
    )
    args = parser.parse_args(argv)

    text = " ".join(getattr(args, "text", []) or []).strip()

    if args.cmd in {"repl", "echo"}:
        translator = RusitTranslator(
            db_path=getattr(args, "db", None),
            use_spacy=args.spacy,
            spacy_model=getattr(args, "spacy_model", "ru_core_news_sm"),
        )
        prompt = sys.stdin.isatty() and sys.stdout.isatty()
        try:
            while True:
                if prompt:
                    try:
                        line = input("ru> ")
                    except EOFError:
                        print()
                        break
                else:
                    line = sys.stdin.readline()
                    if not line:
                        break
                    line = line.rstrip("\n\r")
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped in {"/exit", "/quit", ":q", ":quit"}:
                    break
                print(translator.translate(line, preserve_punctuation=True))
        except KeyboardInterrupt:
            if prompt:
                print()
        return 0

    if args.cmd == "translate":
        from_file = False
        if args.input:
            if text:
                print(
                    "translate: нельзя одновременно указать текст и --input",
                    file=sys.stderr,
                )
                return 2
            if args.input == "-":
                text = sys.stdin.read()
            else:
                try:
                    text = Path(args.input).read_text(encoding="utf-8")
                except OSError as exc:
                    print(
                        f"translate: не удалось прочитать {args.input}: {exc}",
                        file=sys.stderr,
                    )
                    return 2
            from_file = True
        elif not text:
            text = sys.stdin.read().strip()

        translator = RusitTranslator(
            db_path=args.db,
            use_spacy=args.spacy,
            spacy_model=getattr(args, "spacy_model", "ru_core_news_sm"),
        )
        markdown_suffixes = {
            ".md", ".markdown", ".mdown", ".mkd", ".mdx",
        }
        markdown_file = bool(
            args.input
            and args.input != "-"
            and Path(args.input).suffix.lower() in markdown_suffixes
        )
        markdown = args.format == "markdown" or (
            args.format == "auto"
            and (markdown_file or looks_like_markdown(text))
        )

        if markdown:
            translated = translator.translate_markdown(text)
        elif from_file:
            translated = "\n".join(
                translator.translate(
                    line, preserve_punctuation=True
                )
                for line in text.splitlines()
            )
        else:
            translated = translator.translate(
                text, preserve_punctuation=True
            )

        if args.output and args.output != "-":
            output = translated
            if output and not output.endswith("\n"):
                output += "\n"
            try:
                Path(args.output).write_text(output, encoding="utf-8")
            except OSError as exc:
                print(
                    f"translate: не удалось записать {args.output}: {exc}",
                    file=sys.stderr,
                )
                return 2
        else:
            if translated and not translated.endswith("\n"):
                translated += "\n"
            sys.stdout.write(translated)
        return 0

    if hasattr(args, "text") and not text:
        text = sys.stdin.read()
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
