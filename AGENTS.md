# AGENTS.md — rusit

Python package/CLI for translating Russian into **RUSIT**, an analytic language
with immutable lexemes and grammatical particles (`был`, `буд`, `кон`, `не`,
`ли`, `ста`, `ся`, `би`, …). No services, network, build step, or deployment.

## Setup and commands

Run everything from the repo root: the default lexicon path is the relative
`rusit_lexicon.json`.

```bash
python3 -m pip install -e . pymorphy3 pytest   # python3; `python` may not exist
python3 -m pytest tests -q                     # full suite: 236 tests (slow, 1–3 min)
python3 -m pytest tests/test_rusit.py::TestBasicSVO::test_simple_present -q
```

`pyproject.toml` declares no dependencies, but `rusit/translator.py` hard-imports
`pymorphy3`; pytest is also undeclared. There is no CI, lint, formatter, or
typecheck config — pytest is the only verification. The suite is slow because
each fixture constructs `pymorphy3.MorphAnalyzer()`.

## Layout

- `rusit/translator.py` — main implementation: regex tokenization, pymorphy3
  morphology, lexicon lookups, TAM/aspect/phase/passive rules.
- `rusit/validator.py` — particle zone order and incompatibilities only
  (`ZONE_ORDER`, `INCOMPATIBLE`); not a full grammar checker.
- `rusit/cli.py` — `translate`, `validate`, `explain`, `corpus demo|score`,
  `lexicon init|export|add|remove|list`; also the `rusit` console script.
  `translate` supports `-i/--input` and `-o/--output`; file input is translated
  line by line, preserving blank lines (`-` means stdin/stdout).
- `rusit/markdown.py` — Markdown-aware translation: block structure and inline
  markup are masked with placeholders, only plain text is translated. Used by
  `translate_markdown()` and CLI auto-detection (`.md` suffix, `--format
  markdown`, `--markdown`).
- `tests/test_rusit.py` — main suite; `tests/test_cli.py` — file I/O tests;
  `tests/test_markdown.py` — Markdown preservation tests.
- `rusit/db.py` — optional SQLite lexicon (`lexicon init` imports JSON;
  `translate --db file.db` bypasses the JSON lexicon).
- `rusit/corpus.py` — 5-row demo corpus; `score` reports exact and validator
  counts (currently `{total: 5, exact: 2, valid: 5}`, so exact ≠ total).
- `rusit/core.py` and `rusit/rusit_lexicon.json` — legacy RUSIT 3.0 code/data,
  unused. Root `rusit_lexicon.json` is the live v5.0 lexicon.
- `RUSIT_5.3.1.md` — normative language specification; not imported by code.

## Gotchas

- `README.md` still calls the project RUSIT 3.0, but the code needs `pymorphy3`
  and implements RUSIT 5.0 against the 5.3.1 spec.
- `use_spacy` and the `tr_spacy` test fixture are misleading: the argument is
  accepted but ignored, and spaCy is never used. Do not add spaCy.
- CLI `explain` is broken: it calls the nonexistent `RusitValidator.explain`
  and raises `AttributeError`. `validate` works and exits 1 on invalid input.
- Мутатив — всегда `ста` (§7.6); `станов` из ранних версий исключён. Perfective
  мутатива выражается сочетанием `кон ста` (§21.2), imperfective — одним `ста`.
- Прилагательные сохраняют полную каноническую форму (§5.2): усечения нет.
- Императив совпадает с канонической лексемой (§8): `чита!`, `вы чита!`, а не
  `читай`.
- Lexicon keys are normalized `ё → е` on load; unknown words pass through
  unchanged by design. There are no grammar exceptions to special-case.
- API `RusitTranslator.translate()` drops punctuation by default; pass
  `preserve_punctuation=True` to keep it. CLI and file input always preserve
  punctuation, attaching it to the preceding token (dashes stay spaced).

## Conventions

- Code, comments, docstrings, error messages, and tests are written in Russian;
  keep them that way.
- Modules/tests use banner comments (`═══`), tests are grouped into topic
  classes, and bulk cases use `pytest.mark.parametrize`. Many assertions compare
  exact output strings, so behavior changes require deliberate test updates.
- When grammar changes are involved, consult `RUSIT_5.3.1.md`, but treat the
  current tests as the executable description of what the implementation does.
