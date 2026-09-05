"""РУСИТ 4.1 — линейный транслятор с полным TAM и обновлённым словарём."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Set, List, Optional

import pymorphy3

# Фазовые маркеры
PHASE_MARKERS = {
    "начать": "нач", "начинать": "нач",
    "перестать": "перест", "переставать": "перест",
    "продолжить": "прод", "продолжать": "прод",
    "стать": "ста", "становиться": "станов",
}

_TOKEN_RE = re.compile(r"[А-Яа-яЁё]+|[A-Za-z]+|\d+|[!?.,;:—-]")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower().replace("ё", "е"))


class RusitTranslator:
    def __init__(self, lexicon_path: str | Path = "rusit_lexicon.json"):
        with open(lexicon_path, encoding="utf-8") as f:
            data = json.load(f)

        self.verbs: Dict[str, str] = data.get("verbs", {})
        self.aspect_verbs: Dict[str, str] = data.get("aspect_verbs", {})
        self.telic_verbs: Set[str] = set(data.get("telic_verbs", []))
        self.qualifiers: Dict[str, str] = data.get("qualifiers", {})
        self.relative_adjectives: Set[str] = set(data.get("relative_adjectives", []))
        self.nouns: Dict[str, str] = data.get("nouns", {})
        self.prepositions: Dict[str, str] = data.get("prepositions", {})
        self.conjunctions: Dict[str, str] = data.get("conjunctions", {})
        self.pronouns: Dict[str, str] = data.get("pronouns", {})
        self.modal_predicates: Dict[str, str] = data.get("modal_predicates", {})
        self.discourse_markers: Dict[str, str] = data.get("discourse_markers", {})
        self.adverbs_blacklist: Set[str] = set(data.get("adverbs_blacklist", []))

        self.morph = pymorphy3.MorphAnalyzer()

    def translate(self, text: str) -> str:
        sentences = self._split_sentences(text)
        return " ".join(self._translate_sentence(s).strip() for s in sentences if s.strip())

    def _split_sentences(self, text: str) -> list[str]:
        return [p for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p]

    def _translate_sentence(self, sentence: str) -> str:
        tokens = tokenize(sentence)
        out: list[str] = []
        pending_prep: Optional[str] = None

        question = "?" in tokens
        if question and tokens and tokens[0] not in {
            "кто", "что", "где", "когда", "куда", "почему", "как", "ли"
        }:
            out.append("ли")

        passive_seen = False
        numeral_just_seen = False

        for i, tok in enumerate(tokens):
            if re.fullmatch(r"[!?.,;:—-]", tok):
                continue

            # Союзы
            if tok in self.conjunctions:
                out.append(self.conjunctions[tok])
                continue

            # Дискурсивные маркеры
            if tok in self.discourse_markers:
                out.append(self.discourse_markers[tok])
                continue

            if tok == "не":
                out.append("не")
                continue

            # Модальные предикаторы
            if tok in self.modal_predicates:
                out.append(self.modal_predicates[tok])
                continue

            # Предлоги
            if tok in self.prepositions:
                pending_prep = self.prepositions[tok]
                continue

            # Местоимения (притяжательные обрабатываем особым образом)
            if tok in {"мой", "моя", "мое", "мои", "свой", "своя", "свое", "свои"}:
                out.append("у")
                out.append("я")
                continue

            # Будущее время "быть"
            if tok in {"буду", "будешь", "будет", "будем", "будете", "будут"}:
                out.append("буд")
                continue

            # Связка "есть"
            if tok in {"есть", "является", "находится"}:
                out.append("есть")
                continue

            # Глагол
            verb_result = self._process_verb_linear(tok)
            if verb_result is not None:
                out.extend(verb_result)
                numeral_just_seen = False
                continue

            # Местоимение (не притяжательное)
            if tok in self.pronouns:
                word = self.pronouns[tok]
            else:
                word = self._nominal_base(tok)

            # Множественное число
            if self._is_plural_noun(tok) and not numeral_just_seen:
                out.append("много")

            # Пассив
            if passive_seen and self._is_instrumental(tok):
                out.append("би")

            if pending_prep:
                out.append(pending_prep)
                pending_prep = None

            out.extend(word.split())

            if self._is_numeral(tok):
                numeral_just_seen = True
            else:
                numeral_just_seen = False

        if question:
            return " ".join(out) + "?"
        return " ".join(out).rstrip()

    def _process_verb_linear(self, tok: str) -> Optional[List[str]]:
        if tok in self.adverbs_blacklist:
            return None

        parses = self.morph.parse(tok)
        if not parses:
            return None

        verb_parse = None
        for p in parses:
            if p.tag.POS in ("VERB", "INFN"):
                verb_parse = p
                break
        if verb_parse is None:
            return None

        lemma = verb_parse.normal_form

        # Фазовые маркеры
        if lemma in PHASE_MARKERS:
            return [PHASE_MARKERS[lemma]]

        # Ателический результат (получ/перест)
        if lemma in self.aspect_verbs:
            return self.aspect_verbs[lemma].split()

        result = []
        tag = verb_parse.tag

        # Время
        tense = None
        if "past" in tag:
            tense = "был"
        elif "futr" in tag:
            tense = "буд"

        # Совершенный вид
        is_perfective = "perf" in tag
        aspect_marker = None
        if is_perfective:
            if lemma in self.telic_verbs:
                aspect_marker = "кон"
            else:
                aspect_marker = "кон"  # фолбэк для совершенного вида

        if tense:
            result.append(tense)
        if aspect_marker:
            result.append(aspect_marker)

        # Лексема
        lexeme = self.verbs.get(lemma)
        if not lexeme:
            lexeme = self._fallback_verb(lemma)
        result.extend(lexeme.split())

        # Возвратность
        if lemma.endswith("ся") or lemma.endswith("сь"):
            result.append("ся")

        return result if result else None

    def _fallback_verb(self, lemma: str) -> str:
        if lemma.endswith("ться"):
            stem = lemma[:-4]
            return stem + " ся"
        if lemma.endswith(("ть", "ти", "чь")):
            stem = lemma[:-2]
        else:
            stem = lemma
        for suffix in ("ива", "ыва", "ова", "ева", "а", "я", "е", "и", "ну"):
            if stem.endswith(suffix) and len(stem) > 2:
                stem = stem[: -len(suffix)]
                break
        if len(stem) < 2:
            stem = lemma[:2]
        return stem

    def _nominal_base(self, tok: str) -> str:
        if tok in self.qualifiers:
            return self.qualifiers[tok]
        if tok in self.nouns:
            return self.nouns[tok]
        if tok in self.relative_adjectives:
            return tok  # относительные прилагательные остаются в полной форме
        parses = self.morph.parse(tok)
        if not parses:
            return tok
        p = parses[0]
        pos = p.tag.POS
        if pos == "NOUN":
            return p.normal_form
        if pos == "ADJF":
            lemma = p.normal_form
            if lemma in self.relative_adjectives:
                return lemma
            if self._is_qualitative_adjective(lemma):
                return self._truncate_adjective(lemma)
            else:
                return lemma
        if pos == "ADVB":
            return tok
        return p.normal_form

    def _is_qualitative_adjective(self, lemma: str) -> bool:
        relative_suffixes = ("ск", "ов", "ев", "ин", "н", "ическ", "тельн")
        for suffix in relative_suffixes:
            if lemma.endswith(suffix):
                return False
        return True

    def _truncate_adjective(self, lemma: str) -> str:
        if lemma.endswith(("ый", "ий", "ой")):
            return lemma[:-2]
        if lemma.endswith(("ая", "ое", "ые")):
            return lemma[:-2]
        return lemma

    def _is_instrumental(self, tok: str) -> bool:
        parses = self.morph.parse(tok)
        if not parses:
            return False
        return parses[0].tag.POS == "NOUN" and "ablt" in parses[0].tag

    def _is_plural_noun(self, tok: str) -> bool:
        parses = self.morph.parse(tok)
        for p in parses:
            if p.tag.POS == "NOUN" and "plur" in str(p.tag):
                return True
        return False

    def _is_numeral(self, tok: str) -> bool:
        if re.fullmatch(r"\d+", tok):
            return True
        parses = self.morph.parse(tok)
        if parses:
            return parses[0].tag.POS == "NUMR"
        return False