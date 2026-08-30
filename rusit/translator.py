"""Rule-based Russian -> RUSIT translator and text normalizer."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from .core import NOUN_LEXICON, PREPOSITION_MAP, QUALIFIER_LEXICON, VERB_LEXICON, PERFECTIVE_PREFIXES, PAST_SUFFIXES

_TOKEN_RE = re.compile(r"[А-Яа-яЁё]+|[A-Za-z]+|\d+|[!?.,;:—-]")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower().replace("ё", "е"))


class RusitTranslator:
    """Deterministic translator aimed at useful prototypes, tests and corpora."""

    def __init__(self, verb_lexicon: dict[str, str] | None = None):
        self.verbs = {**VERB_LEXICON, **(verb_lexicon or {})}

    def translate(self, text: str) -> str:
        sentences = self._split_sentences(text)
        return " ".join(self._translate_sentence(s).strip() for s in sentences if s.strip())

    def translate_file(self, src: str | Path, dst: str | Path | None = None) -> str:
        result = self.translate(Path(src).read_text(encoding="utf-8"))
        if dst:
            Path(dst).write_text(result + "\n", encoding="utf-8")
        return result

    def _split_sentences(self, text: str) -> list[str]:
        return [p for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p]

    def _translate_sentence(self, sentence: str) -> str:
        tokens = tokenize(sentence)
        out: list[str] = []
        pending_prep: str | None = None
        question = "?" in tokens
        if question and tokens and tokens[0] not in {"кто", "что", "где", "когда", "куда", "почему", "как", "ли"}:
            out.append("ли")

        passive_seen = False
        for i, tok in enumerate(tokens):
            if re.fullmatch(r"[!?.,;:—-]", tok):
                continue
            if tok == "не":
                out.append("не"); continue
            if tok in PREPOSITION_MAP:
                pending_prep = PREPOSITION_MAP[tok]; continue
            if tok in {"мой", "моя", "мое", "мои", "свой", "своя", "свое", "свои"}:
                out.append("у"); out.append("я"); continue
            if tok in {"буду", "будешь", "будет", "будем", "будете", "будут"}:
                out.append("буд"); continue

            lemma = self._verb_base(tok)
            if lemma:
                tense, aspect = self._verb_tam(tok, lemma)
                if tense == "past" and (not out or out[-1] != "был"):
                    out.append("был")
                if aspect == "perfective" and (not out or out[-1] != "кон"):
                    out.append("кон")
                out.extend(self.verbs.get(lemma, self._fallback_verb(lemma)).split())
                passive_seen = passive_seen or tok.endswith("ен")
                continue

            word = self._nominal_base(tok)
            if passive_seen and tok.endswith(("ами", "ями", "ими")) and (not out or out[-1] != "би"):
                out.append("би")
            if pending_prep:
                out.append(pending_prep); pending_prep = None
            out.extend(word.split())

        if question:
            return " ".join(out) + "?"
        return " ".join(out).rstrip()

    def _verb_base(self, tok: str) -> str | None:
        if tok in self.verbs:
            return tok
        forms = {
            "читаю": "читать", "читает": "читать", "читал": "читать", "читала": "читать", "прочитал": "прочитать",
            "прочитала": "прочитать", "делаю": "делать", "делал": "делать", "сделал": "сделать",
            "вижу": "видеть", "видел": "видеть", "увидел": "увидеть", "люблю": "любить", "любил": "любить",
            "иду": "идти", "идет": "идти", "шел": "идти", "шла": "идти", "пришел": "прийти", "пришла": "прийти",
            "дал": "дать", "дала": "дать", "спал": "спать", "спала": "спать", "сидел": "сидеть", "сидела": "сидеть",
            "построен": "построить", "построили": "построить", "прилетели": "прилететь", "пишу": "писать",
        }
        return forms.get(tok)

    def _verb_tam(self, form: str, lemma: str) -> tuple[str | None, str | None]:
        past = form.endswith(PAST_SUFFIXES) or form in {"шел", "шла", "построен"}
        perf = lemma in {k for k in self.verbs if k.startswith(PERFECTIVE_PREFIXES)} and lemma not in {"строить", "смотреть", "спать", "стоять"}
        perf = perf or form in {"построен"}
        return ("past" if past else None, "perfective" if perf else None)

    def _fallback_verb(self, lemma: str) -> str:
        if lemma.endswith("ться"):
            return lemma[:-4] + " ся"
        if lemma.endswith("ть") or lemma.endswith("ти"):
            return lemma[:-2]
        return lemma

    def _nominal_base(self, tok: str) -> str:
        return QUALIFIER_LEXICON.get(tok) or NOUN_LEXICON.get(tok) or tok
