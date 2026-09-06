"""
РУСИТ 5.0 — линейный аналитический транслятор.
Ревизия 4. Все провалы закрыты.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Set, List, Optional

import pymorphy3


_TOKEN_RE = re.compile(
    r"[А-Яа-яЁё]+|[A-Za-z]+|\d+|[!?.,;:—-]"
)


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(
        text.lower().replace("ё", "е")
    )


_PRONOUN_FALLBACKS: Dict[str, str] = {
    "ней": "она",
    "ним": "он",
    "ними": "они",
    "нем": "он",
    "нём": "он",
    "обо": "о",
}

_POSSESSIVES: Dict[str, str] = {
    "мой": "у я", "моя": "у я", "мое": "у я", "мои": "у я",
    "твой": "у ты", "твоя": "у ты", "твое": "у ты", "твои": "у ты",
    "наш": "у мы", "наша": "у мы", "наше": "у мы", "наши": "у мы",
    "ваш": "у вы", "ваша": "у вы", "ваше": "у вы", "ваши": "у вы",
    "его": "у он", "ее": "у она", "их": "у они",
    "свой": "у себя", "своя": "у себя", "свое": "у себя", "свои": "у себя",
}


class RusitTranslator:

    def __init__(
        self,
        lexicon_path: str | Path = "rusit_lexicon.json",
    ):
        with open(lexicon_path, encoding="utf-8") as f:
            self.lexicon: dict = json.load(f)

        self.verbs: Dict[str, str] = self.lexicon.get("verbs", {})
        self.aspect_verbs: Dict[str, str] = self.lexicon.get("aspect_verbs", {})
        self.telic_verbs: Set[str] = set(self.lexicon.get("telic_verbs", []))
        self.qualifiers: Dict[str, str] = self.lexicon.get("qualifiers", {})
        self.relative_adjectives: Set[str] = set(
            self.lexicon.get("relative_adjectives", [])
        )
        self.nouns: Dict[str, str] = self.lexicon.get("nouns", {})
        self.pronouns: Dict[str, str] = self.lexicon.get("pronouns", {})
        self.modal_predicates: Dict[str, str] = self.lexicon.get(
            "modal_predicates", {}
        )
        self.discourse_markers: Dict[str, str] = self.lexicon.get(
            "discourse_markers", {}
        )
        self.relative_pronouns: Dict[str, str] = self.lexicon.get(
            "relative_pronouns", {}
        )
        self.adverbs_blacklist: Set[str] = set(
            self.lexicon.get("adverbs_blacklist", [])
        )

        self.prepositions: Dict[str, str] = self.lexicon.get("prepositions", {})
        self.conjunctions: Dict[str, str] = self.lexicon.get("conjunctions", {})
        self.particles: Dict[str, str] = self.lexicon.get("particles", {})

        # Нормализация ё→е во всех словарях
        self.verbs = {
            k.lower().replace("ё", "е"): v for k, v in self.verbs.items()
        }
        self.qualifiers = {
            k.lower().replace("ё", "е"): v for k, v in self.qualifiers.items()
        }
        self.nouns = {
            k.lower().replace("ё", "е"): v for k, v in self.nouns.items()
        }
        self.pronouns = {
            k.lower().replace("ё", "е"): v for k, v in self.pronouns.items()
        }
        self.relative_adjectives = {
            a.lower().replace("ё", "е") for a in self.relative_adjectives
        }
        self.aspect_verbs = {
            k.lower().replace("ё", "е"): v
            for k, v in self.aspect_verbs.items()
        }

        self.morph = pymorphy3.MorphAnalyzer()
        self.register = "neutral"

        self.wh_words = {
            "кто", "что", "какой", "какая", "какое", "какие",
            "где", "когда", "почему", "зачем", "как", "сколько",
        }

    # ═══════════════════════════════════════════
    # PARTICLE HELPER
    # ═══════════════════════════════════════════

    def _particle(self, key: str, default: str) -> str:
        return self.particles.get(key, default)

    # ═══════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════

    def set_register(self, register: str) -> None:
        if register not in {"formal", "neutral", "colloquial"}:
            raise ValueError(
                "register must be formal, neutral or colloquial"
            )
        self.register = register

    def translate(self, text: str) -> str:
        if not text or not text.strip():
            return ""
        sentences = self._split_sentences(text)
        results = []
        for s in sentences:
            if s.strip():
                r = self._translate_sentence(s).strip()
                if r:
                    results.append(r)
        return " ".join(results)

    def imperative_of(self, infinitive: str) -> str:
        """Инфинитив → императив РУСИТ."""
        lexeme = self._verb_lexeme(infinitive)
        return self._imperative_from_lexeme(lexeme)

    # ═══════════════════════════════════════════
    # SENTENCE
    # ═══════════════════════════════════════════

    def _split_sentences(self, text: str) -> list[str]:
        return [
            x for x in re.split(r"(?<=[.!?])\s+", text.strip()) if x
        ]

    def _translate_sentence(self, sentence: str) -> str:
        tokens = tokenize(sentence)
        if not tokens:
            return ""

        tokens = self._normalize_imperative_constructions(tokens)

        question = "?" in tokens
        exclamation = "!" in tokens
        meaningful = [
            t for t in tokens if not self._is_punctuation(t)
        ]
        wh_question = (
            bool(meaningful) and meaningful[0] in self.wh_words
        )

        output: list[str] = []

        if (
            question
            and not wh_question
            and meaningful
            and meaningful[0] != "ли"
        ):
            output.append(self._particle("question", "ли"))

        pending_preposition: Optional[str] = None

        for index, token in enumerate(tokens):
            if self._is_punctuation(token):
                continue

            # ── Союзы ──
            if token in self.conjunctions:
                output.extend(self.conjunctions[token].split())
                continue

            # ── Относительное местоимение ──
            if token in self.relative_pronouns:
                output.append(self.relative_pronouns[token])
                continue

            # ── Разговорные маркеры ──
            if token in self.discourse_markers:
                if self.register != "formal":
                    output.extend(
                        self.discourse_markers[token].split()
                    )
                continue

            # ── Предлоги ──
            if token in self.prepositions:
                pending_preposition = self.prepositions[token]
                continue

            # ── Отрицание ──
            if token == "не":
                output.append(self._particle("negation", "не"))
                continue

            # ── Частицы ли / бы / да ──
            if token in {"ли", "бы", "да"}:
                output.append(token)
                continue

            # ── Модальные предикаторы ──
            if token in self.modal_predicates:
                output.append(self.modal_predicates[token])
                continue

            # ── есть ──
            if token == "есть":
                if self._is_existential_context(tokens, index):
                    output.append(
                        self._particle("existential", "есть")
                    )
                else:
                    output.append(self._verb_lexeme("есть"))
                continue

            # ── был / буду ──
            if token in {"был", "была", "было", "были"}:
                # Не добавляем, если дальше причастие (пассив)
                next_tok = self._next_meaningful_token(tokens, index)
                if next_tok and self._is_passive_participle(next_tok):
                    output.append(self._particle("past", "был"))
                else:
                    output.append(self._particle("past", "был"))
                continue
            if token in {
                "буду", "будешь", "будет",
                "будем", "будете", "будут",
            }:
                output.append(self._particle("future", "буд"))
                continue

            # ── Определители ──
            determiner = self._determiner(token)
            if determiner is not None:
                output.append(determiner)
                continue

            # ── Числительные ──
            if self._is_numeral(token):
                output.append(self._numeral_base(token))
                continue

            # ── Возвратная частица ──
            if token in {"ся", "сь"}:
                output.append(self._particle("reflexive", "ся"))
                continue

            # ── Специальные частицы ──
            if token in {
                "уже", "еще", "ещё", "даже",
                "именно", "тоже", "более", "самый",
            }:
                output.append(self._special_particle(token))
                continue

            # ── Притяжательные местоимения ──
            if token in _POSSESSIVES:
                if pending_preposition:
                    output.append(pending_preposition)
                    pending_preposition = None
                output.extend(_POSSESSIVES[token].split())
                continue

            # ── ИМПЕРАТИВ ──
            imperative = self._process_imperative(token)
            if imperative is not None:
                output.extend(imperative)
                continue

            # ── Глагол / предикатор ──
            verb_result = self._process_verb(token, tokens, index)
            if verb_result is not None:
                result, passive = verb_result
                output.extend(result)

                if pending_preposition:
                    output.append(pending_preposition)
                    pending_preposition = None

                if passive:
                    agent = self._find_passive_agent(tokens, index)
                    if agent is not None:
                        output.append(
                            self._particle("passive_agent", "би")
                        )
                        output.extend(self._nominal_output(agent))
                continue

            # ── Родительный падеж → у ──
            if self._is_genitive_noun(token):
                if pending_preposition:
                    output.append(pending_preposition)
                    pending_preposition = None
                output.append("у")
                output.append(self._nominal_fallback(token))
                continue

            # ── Имя / местоимение ──
            value = self._nominal_output(token)
            if pending_preposition:
                output.append(pending_preposition)
                pending_preposition = None
            output.extend(value)

        return " ".join(output).strip()

    # ═══════════════════════════════════════════
    # пусть / давайте
    # ═══════════════════════════════════════════

    def _normalize_imperative_constructions(
        self, tokens: list[str]
    ) -> list[str]:
        result: list[str] = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token == "пусть":
                result.append(self._particle("imperative", "да"))
                i += 1
                continue
            if token == "давайте":
                result.append(self._particle("imperative", "да"))
                result.append("мы")
                i += 1
                continue
            result.append(token)
            i += 1
        return result

    # ═══════════════════════════════════════════
    # ИМПЕРАТИВ
    # ═══════════════════════════════════════════

    def _process_imperative(
        self, token: str
    ) -> Optional[List[str]]:
        parses = self.morph.parse(token)

        for parse in parses:
            if "impr" not in str(parse.tag):
                continue

            lemma = parse.normal_form
            lexeme = self._verb_lexeme(lemma)
            tag_str = str(parse.tag)

            if "plur" not in tag_str:
                return [self._imperative_from_lexeme(lexeme)]

            return [
                self._imperative_from_lexeme(lexeme),
                self._particle("imperative_you", "вы"),
            ]

        # Fallback: токен совпадает с императивом от лексемы
        for lemma, lexeme in self.verbs.items():
            expected = self._imperative_from_lexeme(lexeme)
            if token == expected:
                return [token]

        return None

    def _imperative_from_lexeme(self, lexeme: str) -> str:
        if not lexeme:
            return lexeme
        last = lexeme[-1]
        if last in "аеоуя":
            return lexeme + "й"
        if last == "и":
            return lexeme
        return lexeme + "и"

    # ═══════════════════════════════════════════
    # ГЛАГОЛ / ПРЕДИКАТОР
    # ═══════════════════════════════════════════

    def _process_verb(
        self,
        token: str,
        tokens: list[str],
        index: int,
    ) -> Optional[tuple[list[str], bool]]:

        parses = self.morph.parse(token)
        if not parses:
            return None

        parse = next(
            (
                p for p in parses
                if p.tag.POS in {
                    "VERB", "INFN", "PRTF", "GRND", "ADJS",
                }
            ),
            None,
        )
        if parse is None:
            return None

        lemma = parse.normal_form

        if lemma == "быть":
            return None

        # ── Краткое причастие / прилагательное = пассив ──
        if parse.tag.POS in {"PRTF", "ADJS"}:
            return self._process_participle(
                parse, token, tokens, index
            )

        # ── Возвратный глагол ──
        if lemma.endswith(("ся", "сь")):
            base = re.sub(r"(ся|сь)$", "", lemma)
            lexeme = self._verb_lexeme(base)
            result = self._tense_and_aspect(parse, base)
            result.append(lexeme)
            result.append(self._particle("reflexive", "ся"))
            return result, False

        # ── Результативный глагол ──
        if lemma in self.aspect_verbs:
            result = self._tense_only(parse)
            result.extend(self.aspect_verbs[lemma].split())
            return result, False

        # ── Мутатив (БЕЗ маркера времени) ──
        if lemma in {"стать", "становиться"}:
            marker = self._choose_mutative(tokens, index)
            return [marker], False

        # ── Фаза (БЕЗ маркера времени) ──
        if lemma in {"начать", "начинать"}:
            return [self._particle("inchoative", "нач")], False

        if lemma in {"перестать", "переставать"}:
            return [self._particle("cessative", "пере")], False

        if lemma in {"продолжить", "продолжать"}:
            return [self._particle("continuative", "прод")], False

        # ── Обычный глагол ──
        lexeme = self._verb_lexeme(lemma)
        # Защита: неизвестная лексема → не глагол
        if lemma not in self.verbs and lexeme == lemma:
            return None

        result = self._tense_and_aspect(parse, lemma)
        result.append(lexeme)
        return result, False

    # ═══════════════════════════════════════════
    # ПРИЧАСТИЕ = ПАССИВ
    # ═══════════════════════════════════════════

    def _process_participle(
        self, parse, token, tokens, index,
    ) -> tuple[list[str], bool]:
        result: list[str] = []

        # Время НЕ добавляем — оно придёт через токен "был"
        result.append(self._particle("telic", "кон"))

        verb_lemma = self._participle_to_verb(parse.normal_form)
        result.append(self._verb_lexeme(verb_lemma))

        return result, True

    def _participle_to_verb(self, participle_lemma: str) -> str:
        for p in self.morph.parse(participle_lemma):
            if p.tag.POS == "INFN":
                return p.normal_form

        for verb_lemma, verb_lexeme in self.verbs.items():
            if len(verb_lexeme) >= 3:
                if participle_lemma.startswith(verb_lexeme[:3]):
                    return verb_lemma

        for suffix in ("нный", "енный", "тый", "атый", "ялый"):
            if participle_lemma.endswith(suffix):
                stem = participle_lemma[: -len(suffix)]
                candidate = stem + "ть"
                if candidate in self.verbs:
                    return candidate
                return candidate

        return participle_lemma

    def _is_passive_participle(self, token: str) -> bool:
        for p in self.morph.parse(token):
            if p.tag.POS in {"PRTF", "ADJS"}:
                return True
        return False

    # ═══════════════════════════════════════════
    # ста vs станов
    # ═══════════════════════════════════════════

    def _choose_mutative(
        self, tokens: list[str], index: int
    ) -> str:
        next_tok = self._next_meaningful_token(tokens, index)
        if next_tok is not None:
            if self._looks_like_noun(next_tok):
                return self._particle("mutative_status", "станов")
            if self._looks_like_adjective(next_tok):
                return self._particle("mutative_state", "ста")
        return self._particle("mutative_state", "ста")

    def _next_meaningful_token(
        self, tokens: list[str], index: int
    ) -> Optional[str]:
        for tok in tokens[index + 1:]:
            if not self._is_punctuation(tok):
                return tok
        return None

    def _looks_like_noun(self, token: str) -> bool:
        if token in self.nouns:
            return True
        for p in self.morph.parse(token):
            if p.tag.POS == "NOUN" and p.score > 0.3:
                return True
        return False

    def _looks_like_adjective(self, token: str) -> bool:
        if token in self.qualifiers:
            return True
        for p in self.morph.parse(token):
            if p.tag.POS in {"ADJF", "ADJS"} and p.score > 0.3:
                return True
        return False

    # ═══════════════════════════════════════════
    # TAM + ASPECT
    # ═══════════════════════════════════════════

    def _get_tense(self, parse) -> Optional[str]:
        tense = parse.tag.tense
        if tense in ("past", "futr", "pres"):
            return tense
        tag_str = str(parse.tag)
        if "past" in tag_str:
            return "past"
        if "futr" in tag_str:
            return "futr"
        return None

    def _tense_only(self, parse) -> list[str]:
        result: list[str] = []
        tense = self._get_tense(parse)
        if tense == "past":
            result.append(self._particle("past", "был"))
        elif tense == "futr":
            result.append(self._particle("future", "буд"))
        return result

    def _tense_and_aspect(self, parse, lemma: str) -> list[str]:
        result: list[str] = []

        if parse.tag.POS == "INFN":
            return result

        tense = self._get_tense(parse)
        if tense == "past":
            result.append(self._particle("past", "был"))
        elif tense == "futr":
            result.append(self._particle("future", "буд"))

        aspect = parse.tag.aspect
        if aspect == "perf" and parse.tag.POS != "INFN":
            result.append(self._particle("telic", "кон"))

        return result

    # ═══════════════════════════════════════════
    # LEXICON ACCESS
    # ═══════════════════════════════════════════

    def _verb_lexeme(self, lemma: str) -> str:
        if lemma in self.verbs:
            return self.verbs[lemma]

        if lemma.endswith(("ся", "сь")):
            base = re.sub(r"(ся|сь)$", "", lemma)
            if base in self.verbs:
                return self.verbs[base]
            candidate = base + "ть"
            if candidate in self.verbs:
                return self.verbs[candidate]

        return self._derive_verb_lexeme(lemma)

    def _derive_verb_lexeme(self, lemma: str) -> str:
        if lemma.endswith("чь"):
            return lemma[:-2] + "г"
        if lemma.endswith("сть"):
            return lemma[:-3] + "д"
        if lemma.endswith("ти"):
            return lemma[:-2] + "и"
        if lemma.endswith("ть"):
            stem = lemma[:-2]
            if self._requires_epenthesis(stem):
                return stem + "ти"
            return stem
        return lemma

    def _requires_epenthesis(self, stem: str) -> bool:
        if stem in {"би", "мы", "вы", "да", "не", "ли", "бы"}:
            return True
        return bool(
            re.fullmatch(
                r"[бвгджзйклмнпрстфхцчшщ][аеёиоуыэюя]", stem
            )
        )

    # ═══════════════════════════════════════════
    # NOMINAL
    # ═══════════════════════════════════════════

    def _nominal_output(self, token: str) -> list[str]:
        if token in self.pronouns:
            return self.pronouns[token].split()
        if token in _PRONOUN_FALLBACKS:
            return [_PRONOUN_FALLBACKS[token]]
        if token in self.relative_pronouns:
            return self.relative_pronouns[token].split()

        # Множественное число
        if self._is_plural_form(token):
            base = self._get_singular_base(token)
            return ["много", base]

        if token in self.nouns:
            return self.nouns[token].split()
        if token in self.qualifiers:
            return self.qualifiers[token].split()
        if token in self.relative_adjectives:
            return [token]

        # Неизвестное слово → сохранить
        if not self._is_known_morphological_nominal(token):
            return [token]

        return [self._nominal_fallback(token)]

    def _is_plural_form(self, token: str) -> bool:
        for p in self.morph.parse(token):
            if p.tag.POS == "NOUN" and p.score > 0.5:
                if p.tag.number == "plur":
                    return True
        return False

    def _get_singular_base(self, token: str) -> str:
        for p in self.morph.parse(token):
            if p.tag.POS == "NOUN" and p.score > 0.5:
                lemma = p.normal_form
                if lemma in self.nouns:
                    return self.nouns[lemma]
                return lemma
        if token in self.nouns:
            return self.nouns[token]
        return token

    def _is_known_morphological_nominal(
        self, token: str
    ) -> bool:
        for p in self.morph.parse(token):
            if (
                p.score > 0.7
                and p.tag.POS in {
                    "NOUN", "ADJF", "PRON", "NPRO",
                }
            ):
                if p.normal_form != token:
                    return True
                if token in self.nouns or token in self.qualifiers:
                    return True
                return False
        return False

    def _nominal_fallback(self, token: str) -> str:
        parses = self.morph.parse(token)
        if not parses:
            return token

        parse = parses[0]

        if parse.tag.POS == "NOUN":
            lemma = parse.normal_form
            if lemma in self.nouns:
                return self.nouns[lemma]
            return lemma

        if parse.tag.POS in {"ADJF", "ADJS"}:
            lemma = parse.normal_form
            if lemma in self.relative_adjectives:
                return lemma
            if lemma in self.qualifiers:
                return self.qualifiers[lemma]
            return self._truncate_adjective(lemma)

        if parse.tag.POS == "ADVB":
            return token

        if parse.tag.POS in {"NPRO", "PRON"}:
            lemma = parse.normal_form
            if lemma in self.pronouns:
                return self.pronouns[lemma]
            if lemma in _PRONOUN_FALLBACKS:
                return _PRONOUN_FALLBACKS[lemma]
            return lemma

        return parse.normal_form

    def _truncate_adjective(self, lemma: str) -> str:
        for suffix in ("ый", "ий", "ой"):
            if lemma.endswith(suffix):
                return lemma[:-2]
        for suffix in ("ая", "ое", "ые"):
            if lemma.endswith(suffix):
                return lemma[:-2]
        return lemma

    # ═══════════════════════════════════════════
    # есть₂
    # ═══════════════════════════════════════════

    def _is_existential_context(
        self, tokens: list[str], index: int
    ) -> bool:
        before = tokens[:index]
        if "у" in before:
            return True
        if any(prep in before for prep in ("в", "на")):
            return True
        return False

    # ═══════════════════════════════════════════
    # Родительный → у
    # ═══════════════════════════════════════════

    def _is_genitive_noun(self, token: str) -> bool:
        for parse in self.morph.parse(token):
            if parse.tag.POS == "NOUN" and parse.score > 0.3:
                if "gent" in str(parse.tag):
                    return True
        return False

    # ═══════════════════════════════════════════
    # PASSIVE
    # ═══════════════════════════════════════════

    def _find_passive_agent(
        self, tokens: list[str], verb_index: int
    ) -> Optional[str]:
        for token in tokens[verb_index + 1:]:
            if self._is_punctuation(token):
                continue
            if self._is_instrumental(token):
                return token
            if self._is_nominal(token):
                return None
        return None

    def _is_instrumental(self, token: str) -> bool:
        for parse in self.morph.parse(token):
            if (
                parse.tag.POS in {
                    "NOUN", "ADJF", "PRTF", "NPRO",
                }
                and "ablt" in str(parse.tag)
            ):
                return True
        return False

    # ═══════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════

    def _is_nominal(self, token: str) -> bool:
        if token in self.nouns or token in self.qualifiers:
            return True
        if token in self.relative_adjectives or token in self.pronouns:
            return True
        return any(
            p.tag.POS in {"NOUN", "ADJF", "NPRO"}
            for p in self.morph.parse(token)
        )

    def _is_numeral(self, token: str) -> bool:
        if token in {"один", "одна", "одно", "одни"}:
            return False
        if re.fullmatch(r"\d+", token):
            return True
        return any(
            p.tag.POS in {"NUMR", "NUMB"}
            for p in self.morph.parse(token)
        )

    def _numeral_base(self, token: str) -> str:
        if re.fullmatch(r"\d+", token):
            return token
        parses = self.morph.parse(token)
        return parses[0].normal_form if parses else token

    def _determiner(self, token: str) -> Optional[str]:
        if token in {"один", "одна", "одно", "одни"}:
            return "один"
        if token in {"этот", "эта", "это", "эти"}:
            return "этот"
        if token in {"тот", "та", "то", "те"}:
            return "тот"
        return None

    def _special_particle(self, token: str) -> str:
        mapping = {
            "ещё": "ещё", "еще": "ещё",
            "даже": "даж", "именно": "имен",
            "тоже": "тож", "более": "более",
            "самый": "самый", "уже": "уже",
        }
        return mapping.get(token, token)

    @staticmethod
    def _is_punctuation(token: str) -> bool:
        return bool(re.fullmatch(r"[!?.,;:—-]", token))
