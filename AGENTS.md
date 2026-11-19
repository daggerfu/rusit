# AGENTS.md — rusit

Python package/CLI for translating Russian into **RUSIT**, an analytic language
with immutable lexemes and grammatical particles (`был`, `буд`, `кон`, `не`,
`ли`, `ста`, `ся`, `би`, …). No services, network, build step, or deployment.

## Setup and commands

Run everything from the repo root: the default lexicon path is the relative
`rusit_lexicon.json`.

```bash
python3 -m pip install -e . pytest             # python3; `python` may not exist
python3 -m spacy download ru_core_news_sm      # модель нужна по умолчанию
python3 -m pytest tests -q                     # полный набор: 291 тест, ~35 с
python3 -m pytest tests/test_rusit_basic.py::TestBasicSVO::test_simple_present -q
```

`pyproject.toml` declares runtime dependencies `pymorphy3>=1.0` and `spacy>=3.7`
(both installed by `pip install -e .`); pytest and the Russian spaCy model are
declared separately and must be installed explicitly. spaCy is imported lazily,
but `use_spacy=True` is the default: loading the model is cached per process,
and `pymorphy3` still drives morphology. Disable spaCy with `use_spacy=False`
or CLI `--no-spacy`. There is no CI, lint, formatter, or typecheck config —
pytest is the only verification. The suite takes ~35 s because fixtures
construct `pymorphy3.MorphAnalyzer()`.

## Layout

- `rusit/tokenizer.py` — regex tokenization (`tokenize()`): `ё → е`, lowercasing,
  hyphenated composites kept as one token.
- `rusit/translator.py` — main implementation: lexicon loading, sentence
  splitting, token dispatch and output assembly; `RusitTranslator` combines the
  mixins below.
- `rusit/translator_constants.py` — pronoun/dative/possessive lookup tables.
- `rusit/translator_verbs.py` (`VerbsMixin`) — tense, aspect, participles,
  imperatives and TAM particle rules.
- `rusit/translator_nominals.py` (`NominalsMixin`) — noun phrases, number,
  quantifiers, prepositions and case fallbacks.
- `rusit/translator_syntax.py` (`SyntaxMixin`) — SVO/possessive/passive/
  fronting heuristics.
- `rusit/translator_spacy.py` (`SpacyMixin`) — spaCy doc/token mapping,
  dependency/POS/morph features and passive-agent lookup; spaCy itself is
  imported lazily in `rusit/translator.py`.
- `rusit/validator.py` — particle zone order and incompatibilities only
  (`ZONE_ORDER`, `INCOMPATIBLE`); not a full grammar checker.
- `rusit/cli.py` — `translate`, `validate`, `explain`, `corpus demo|score`,
  `lexicon init|export|add|remove|list`, `repl` (`echo` alias); also the `rusit`
  console script. `translate` supports `-i/--input` and `-o/--output`; file input
  is translated line by line, preserving blank lines (`-` means stdin/stdout).
  `--no-spacy` disables the default spaCy analysis.
- `rusit/markdown.py` — Markdown-aware translation: block structure and inline
  markup are masked with placeholders, only plain text is translated. Used by
  `translate_markdown()` and CLI auto-detection (`.md` suffix, `--format
  markdown`, `--markdown`).
- `tests/test_rusit.py` — docstring-only index of the split test suite;
  `tests/test_rusit_basic.py`, `test_rusit_nominals.py`, `test_rusit_syntax.py`,
  `test_validator.py`, `test_rusit_misc.py` — разделённый основной набор;
  `tests/test_cli.py` — file I/O tests;
  `tests/test_markdown.py` — Markdown preservation tests.
- `rusit/db.py` — optional SQLite lexicon (`lexicon init` imports JSON;
  `translate --db file.db` bypasses the JSON lexicon).
- `rusit/corpus.py` — 5-row demo corpus; `score` reports exact and validator
  counts (currently `{total: 5, exact: 5, valid: 5}`).
- `rusit/core.py` — legacy RUSIT 3.0 code, unused. The only lexicon is the root
  `rusit_lexicon.json` (v5.3.1, e.g. `читать → чита`); there is no copy inside
  the package.
- `tools/` — experimental batch scripts for book translation and quality checks
  (`translate_books.py`, `check_translation_quality.py`, `convert_to_patch.py`).
- `RUSIT_5.3.1.md` — normative language specification; not imported by code.

## Gotchas

- The project targets RUSIT 5.3.1 and requires `pymorphy3` at runtime.
- spaCy is enabled by default (`use_spacy=True`, CLI `--no-spacy` disables it).
  `SpacyMixin` supplies dependency/POS features for possessive and SVO choices,
  attributive participles and passive agents; `pymorphy3` remains the primary
  morphology backend. A Russian spaCy model (e.g. `ru_core_news_sm`) must be
  installed separately.
- Мутатив — всегда `ста` (§7.6); `станов` из ранних версий исключён. Perfective
  мутатива выражается сочетанием `кон ста` (§21.2), imperfective — одним `ста`.
- Число грамматически нейтральное (§3.2): форма существительного не
  различает один и несколько предметов. `много` появляется только от явного
  квантификатора/числительного/детерминанта, а не от окончаний русского слова.
- Прошедшее совершенное вида — одна граничная частица `кон` без `был`
  (§7.2); `был кон` сохраняется только для предшествования прошлому моменту.
- Прилагательные сохраняют полную каноническую форму (§5.2): усечения нет.
- Императив совпадает с канонической лексемой (§8): `чита!`, `вы чита!`, а не
  `читай`.
- The root `rusit_lexicon.json` is the single source of truth; the default path
  is relative, so run from the repo root or pass `lexicon_path` explicitly.
- Lexicon keys are normalized `ё → е` on load; unknown words pass through
  unchanged by design. There are no grammar exceptions to special-case.
- API `RusitTranslator.translate()` drops punctuation by default; pass
  `preserve_punctuation=True` to keep it. CLI and file input always preserve
  punctuation, attaching it to the preceding token (dashes stay spaced).

## Conventions

- Package version in `pyproject.toml` tracks the supported RUSIT spec version
  (currently `5.3.1`); keep them in sync when the spec revision changes.
- Commit subjects are short Russian summaries with an optional scope, e.g.
  `перевод: ...`, `тесты: ...`, `доки: ...`; avoid meaningless subjects like
  `1`, `а`, `и`, `много`.
- Code, comments, docstrings, error messages, and tests are written in Russian;
  keep them that way.
- Modules/tests use banner comments (`═══`), tests are grouped into topic
  classes, and bulk cases use `pytest.mark.parametrize`. Many assertions compare
  exact output strings, so behavior changes require deliberate test updates.
- When grammar changes are involved, consult `RUSIT_5.3.1.md`, but treat the
  current tests as the executable description of what the implementation does.
