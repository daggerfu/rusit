"""
РУСИТ 5.3.1 — линейный аналитический транслятор.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Optional, Set

import pymorphy3

from .tokenizer import tokenize
from .translator_constants import (
    _AMBIGUOUS_POSSESSIVES,
    _DATIVE_PRONOUNS,
    _POSSESSIVES,
    _PRONOUN_FALLBACKS,
    _STANDALONE_POSSESSIVE_LEMMAS,
)
from .translator_nominals import NominalsMixin
from .translator_spacy import SpacyMixin
from .translator_syntax import SyntaxMixin
from .translator_verbs import VerbsMixin


_NLP_CACHE: dict[str, object] = {}


class RusitTranslator(SpacyMixin, SyntaxMixin, VerbsMixin, NominalsMixin):

    def __init__(
        self,
        lexicon_path: str | Path = "rusit_lexicon.json",
        db_path: str | Path | None = None,
        use_spacy: bool = True,
        spacy_model: str = "ru_core_news_sm",
    ):
        if db_path is not None:
            from .db import load_lexicon

            self.lexicon: dict = load_lexicon(db_path)
        else:
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
        self.adverbs: Dict[str, str] = self.lexicon.get("adverbs", {})
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
            k.lower().replace("ё", "е"): v.replace("ё", "е")
            for k, v in self.qualifiers.items()
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
        self.adverbs = {
            k.lower().replace("ё", "е"): v for k, v in self.adverbs.items()
        }

        self.morph = pymorphy3.MorphAnalyzer()
        self.register = "neutral"
        self.use_spacy = use_spacy
        self.spacy_model = spacy_model
        self.nlp = None
        self._spacy_doc = None
        self._spacy_token_map: dict[int, int] = {}
        self._spacy_reverse_map: dict[int, int] = {}
        if use_spacy:
            try:
                import spacy
            except ImportError as exc:
                raise RuntimeError(
                    "spaCy не установлен. Установите пакет spacy и "
                    "русскую модель (например, ru_core_news_sm)."
                ) from exc
            self.nlp = _NLP_CACHE.get(spacy_model)
            if self.nlp is None:
                try:
                    self.nlp = spacy.load(spacy_model)
                except Exception as exc:
                    raise RuntimeError(
                        f"Не удалось загрузить spaCy-модель '{spacy_model}'. "
                        "Установите модель, например: "
                        "python3 -m spacy download ru_core_news_sm"
                    ) from exc
                _NLP_CACHE[spacy_model] = self.nlp

        self.wh_words = {
            "кто", "что", "какой", "какая", "какое", "какие",
            "который", "которая", "которое", "которые",
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


    def translate(
        self, text: str, preserve_punctuation: bool = False
    ) -> str:
        if not text or not text.strip():
            return ""
        sentences = self._split_sentences(text)
        results = []
        for s in sentences:
            if s.strip():
                r = self._translate_sentence(
                    s, preserve_punctuation=preserve_punctuation
                ).strip()
                if r:
                    results.append(r)
        return " ".join(results)


    def translate_markdown(self, text: str) -> str:
        """Перевести Markdown, сохранив разметку и структуру."""
        from .markdown import translate_markdown

        return translate_markdown(text, self)


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


    def _translate_sentence(
        self, sentence: str, preserve_punctuation: bool = False
    ) -> str:
        tokens = tokenize(sentence)
        if not tokens:
            return ""
        self._prepare_spacy(tokens, sentence)
        original_tokens = list(tokens)

        tokens = self._normalize_imperative_constructions(tokens)

        # Причастные обороты → «который» + клауза (§15.3):
        # перестройка порядка, а не замена окончаний.
        tokens = self._restructure_participles(tokens)

        # После перестройки токены уже не совпадают с исходным разбором.
        if tokens != original_tokens:
            self._prepare_spacy(tokens)

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
        preposition_applied = False
        pending_possession: Optional[list[str]] = None
        pending_comparison = False
        deferred_objects: list[list[str]] = []
        # Индекс последнего выданного сказуемого: нужен, чтобы отличать
        # дополнение своей клаузы от подлежащего/топика следующей.
        last_predicate_index: Optional[int] = None
        emitted_tam: set[str] = set()
        suppress_plural_marker = False
        consumed: set[int] = set()
        # «Мне надо идти» → «надо я иди»: дательный субъект
        # откладывается до модального предикатора (§12).
        deferred_modal_subject: Optional[list[str]] = None

        for index, token in enumerate(tokens):
            if self._is_punctuation(token):
                if preserve_punctuation:
                    self._append_punctuation(output, token)
                if (
                    token in {",", ";", ":"}
                    and self._starts_new_clause(tokens, index)
                ):
                    # Новая клауза со своим подлежащим: свой TAM.
                    emitted_tam.clear()
                continue
            if index in consumed:
                continue

            # ── Союзы ──
            if token in self.conjunctions:
                output.extend(self.conjunctions[token].split())
                if self._starts_new_clause(tokens, index):
                    emitted_tam.clear()
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
                if deferred_modal_subject:
                    output.extend(deferred_modal_subject)
                    deferred_modal_subject = None
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
                emitted_tam.add("был")
                continue
            if token in {
                "буду", "будешь", "будет",
                "будем", "будете", "будут",
            }:
                output.append(self._particle("future", "буд"))
                emitted_tam.add("буд")
                continue

            # ── Сравнительная степень (§5.4) ──
            # «он выше меня» → «он более высокий чем я».
            # Суффикс сравнительной степени заменяется словом «более»,
            # полная форма прилагательного сохраняется (§5.2),
            # стандарт сравнения вводится союзом «чем».
            if self._comparison_context(tokens, index):
                positive = self._comparative_positive(token)
                if positive is not None:
                    if pending_preposition:
                        output.append(pending_preposition)
                        pending_preposition = None
                    output.append("более")
                    output.append(positive)
                    # Стандарт сравнения вводим союзом «чем»,
                    # если он есть и не дан явно.
                    next_tok = self._next_meaningful_token(
                        tokens, index
                    )
                    if next_tok != "чем" and (
                        next_tok in self.pronouns
                        or (
                            next_tok is not None
                            and self._is_genitive_noun(next_tok)
                        )
                    ):
                        pending_comparison = True
                    continue

            # ── Притяжательные прилагательные ──
            # «мамин» → посессивная конструкция «у мама» после
            # существительного: «мамино письмо» → «письмо у мама».
            owner = self._possessive_owner(token)
            if owner is not None:
                pending_possession = ["у", owner]
                continue

            # ── Определители ──
            determiner = self._determiner(token)
            if determiner is not None:
                if pending_preposition:
                    output.append(pending_preposition)
                    pending_preposition = None
                output.append(determiner)
                if determiner in {"эти", "те", "некоторые", "все"}:
                    suppress_plural_marker = True
                continue

            # ── Порядковые числительные → номер + числительное (§6.3) ──
            ordinal = self._ordinal_cardinal(token)
            if ordinal is not None:
                if pending_preposition:
                    output.append(pending_preposition)
                    pending_preposition = None
                output.append("номер")
                output.append(ordinal)
                continue

            # ── Числительные ──
            if self._is_numeral(token):
                # Количественное слово перед множественным существительным
                # совпадает с маркером множественного числа — не дублировать
                # («много городов» → «много город»,
                #  «множество действий» → «много действие»).
                if token in {"много", "множество"}:
                    if pending_preposition:
                        output.append(pending_preposition)
                        pending_preposition = None
                    output.append("много")
                    suppress_plural_marker = True
                    continue
                numeral = self._numeral_base(token)
                if pending_preposition:
                    output.append(pending_preposition)
                    pending_preposition = None
                output.append(numeral)
                # Числительное/количественное слово выражает количество NP,
                # дополнительный маркер «много» не нужен.
                suppress_plural_marker = True
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
                if pending_preposition:
                    output.append(pending_preposition)
                    pending_preposition = None
                output.append(self._special_particle(token))
                continue
            # Склонённые формы «самый» («самом», «самого», …)
            # — та же фокусная частица. Краткие номинативные
            # «сам/сама/само/сами» — местоимение, оставляем его.
            if token not in {"сам", "сама", "само", "сами"} and (
                self._is_form_of(token, "самый")
            ):
                if pending_preposition:
                    output.append(pending_preposition)
                    pending_preposition = None
                output.append("самый")
                continue

            # ── Дательные местоимения → к + база ──
            # Дательный адресат (§13.4): «я дал книгу ему» →
            # «я был кон дати книга к он». При предлоге («о мне»)
            # форма предложная — «к» не добавляется.
            if token in _DATIVE_PRONOUNS and not pending_preposition:
                if self._modal_predicate_ahead(tokens, index):
                    # «мне надо идти» → «надо я иди»: дательный
                    # субъект, а не адресат.
                    deferred_modal_subject = [
                        self.pronouns.get(token, token)
                    ]
                    continue
                output.extend(["к", self.pronouns[token]])
                continue

            # ── Многие / множество перед существительным ──
            # Количественное значение выражает маркер множественного
            # числа на существительном: «многие города» → «много город»,
            # «множество действий» → «много действие».
            if token in {"многие", "многих", "многим", "многими"}:
                next_tok = self._next_meaningful_token(tokens, index)
                if next_tok and self._is_nominal(next_tok):
                    output.append("много")
                else:
                    output.append(token)
                continue
            if token == "множество":
                # Существительное после «множества» во множественном
                # числе само даст маркер «много».
                next_tok = self._next_meaningful_token(tokens, index)
                if next_tok and self._is_plural_form(next_tok):
                    continue
                output.append(token)
                continue

            # ── Притяжательные местоимения ──
            # «мой/твой/наш/ваш/свой» — самостоятельные лексемы.
            # «его/ее/их» перед именем — притяжание, иначе личное
            # местоимение: «вижу его» → «види он» (§4.1–4.2).
            standalone_poss = self._standalone_possessive(
                token, tokens, index
            )
            if standalone_poss is not None:
                if pending_preposition:
                    output.append(pending_preposition)
                    pending_preposition = None
                    preposition_applied = True
                output.append(standalone_poss)
                continue
            if self._is_my_verb_form(token, tokens, index):
                pass  # императив/глагол «мыть» обработается ниже
            elif token in _POSSESSIVES:
                if (
                    token in _AMBIGUOUS_POSSESSIVES
                    and not self._is_possessive_position(tokens, index)
                ):
                    value = self._nominal_output(token)
                    if self._should_defer_direct_object(
                        token, tokens, index, last_predicate_index,
                        pending_preposition, preposition_applied,
                    ):
                        deferred_objects.append(value)
                    else:
                        output.extend(value)
                    continue
                if pending_preposition:
                    output.append(pending_preposition)
                    pending_preposition = None
                pending_possession = _POSSESSIVES[token].split()
                continue

            # ── Неизменяемые наречные лексемы (словарь) ──
            # Отдельные наречия из лексикона: без суффиксов,
            # согласований и изменений; выводятся канонической
            # формой как есть, значение — семантическая метка
            # (частота, степень, скорость, ...).
            if token in self.adverbs:
                output.append(token)
                continue

            # ── Наречия закрытого списка → сохраняются как есть ──
            if token in self.adverbs_blacklist:
                output.append(token)
                continue

            # ── ИМПЕРАТИВ ──
            imperative = self._process_imperative(
                token, tokens, index
            )
            if imperative is not None:
                if (
                    imperative[0] == self._particle(
                        "imperative_you", "вы"
                    )
                    and output
                    and output[-1] == self._particle("negation", "не")
                ):
                    # «не читайте» → «вы не чита» (§8.2).
                    output.insert(len(output) - 1, imperative[0])
                    output.extend(imperative[1:])
                else:
                    output.extend(imperative)
                last_predicate_index = index
                if deferred_objects:
                    for obj in deferred_objects:
                        output.extend(obj)
                    deferred_objects.clear()
                continue

            # ── Деепричастие: застывшая форма (§15.4) ──
            if self._is_gerund(token):
                output.append(token)
                last_predicate_index = index
                continue

            # ── Глагол / предикатор ──
            verb_result = self._process_verb(token, tokens, index)
            if verb_result is not None:
                result, passive = verb_result
                output.extend(self._dedupe_tam(result, emitted_tam))
                last_predicate_index = index

                if pending_preposition:
                    output.append(pending_preposition)
                    pending_preposition = None

                if passive:
                    agent_index = self._find_passive_agent(
                        tokens, index
                    )
                    if agent_index is not None:
                        output.append(
                            self._particle("passive_agent", "би")
                        )
                        output.extend(
                            self._nominal_output(
                                tokens[agent_index]
                            )
                        )
                        consumed.add(agent_index)
                elif deferred_objects:
                    for obj in deferred_objects:
                        output.extend(obj)
                    deferred_objects.clear()
                continue

            # ── Родительный падеж → у ──
            # Не применяется к множественному числу и после
            # количественного слова: «много городов» → «много город»,
            # «многие города» → «много город», а не «у город».
            # Омонимия «стороны» (род.ед. / им.мн.) снимается
            # согласованием: «заинтересованные стороны» — множественное.
            plural_ctx = self._plural_modifier_before(
                tokens, index
            ) or self._verb_accusative_plural(tokens, index, token)
            prev_tok = next(
                (
                    t
                    for t in reversed(tokens[:index])
                    if not self._is_punctuation(t)
                ),
                None,
            )
            if (
                self._is_genitive_noun(token)
                and not self._is_plural_form(token)
                and not plural_ctx
                and not self._quantifier_before(tokens, index)
                and not self._accusative_context(tokens, index)
            ):
                if prev_tok == "нет":
                    # «у меня нет книги» → «у я нет книга»:
                    # отрицание уже выражено словом «нет».
                    output.append(self._nominal_fallback(token))
                    continue
                if pending_comparison:
                    # Стандарт сравнения: «чем» + именительная база,
                    # без маркера «у» («выше брата» → «чем брат»).
                    output.append("чем")
                    output.append(self._get_singular_base(token))
                    pending_comparison = False
                    preposition_applied = False
                    continue
                if pending_preposition:
                    # Предлог заменяет падеж полностью (§13):
                    # «от группы» → «от группа», без маркера «у».
                    output.append(pending_preposition)
                    pending_preposition = None
                elif preposition_applied:
                    preposition_applied = False
                else:
                    output.append("у")
                output.append(self._nominal_fallback(token))
                continue

            # ── Творительный падеж → с (§4.2, §919) ──
            # «я пишу ручкой» → «я писа с ручка». Предлог заменяет
            # падеж полностью (§13): «с ручкой» → «с ручка»,
            # без дублирования маркера «с».
            if (
                (
                    self._is_instrumental(token)
                    or self._is_instrumental_modifier(
                        token, tokens, index
                    )
                )
                and not pending_preposition
                and not preposition_applied
            ):
                if not self._instrumental_np_started(tokens, index):
                    output.append("с")
                use_suppress = suppress_plural_marker
                value = self._nominal_output(
                    token,
                    suppress_plural_marker=use_suppress,
                )
                output.extend(value)
                if use_suppress and (plural_ctx or self._is_plural_form(token)) and any(
                    p.tag.POS == "NOUN" and p.score > 0.3
                    for p in self.morph.parse(token)
                ):
                    suppress_plural_marker = False
                if pending_possession:
                    output.extend(pending_possession)
                    pending_possession = None
                continue

            # ── Имя / местоимение ──
            use_suppress = suppress_plural_marker
            value = self._nominal_output(
                token,
                suppress_plural_marker=use_suppress,
            )
            if pending_comparison:
                output.append("чем")
                pending_comparison = False

            defer_object = self._should_defer_direct_object(
                token, tokens, index, last_predicate_index,
                pending_preposition, preposition_applied,
            )
            if defer_object:
                obj_tokens = list(value)
                if pending_possession:
                    obj_tokens.extend(pending_possession)
                    pending_possession = None
                deferred_objects.append(obj_tokens)
                if preposition_applied:
                    preposition_applied = False
            else:
                # Обстоятельство между отложенным дополнением и его
                # сказуемым встаёт после дополнения (§16.1: V — O — X):
                # «и её на дерево загнала» → «и загна она на дерево».
                pp_deferred = bool(
                    pending_preposition and deferred_objects
                )
                if pp_deferred:
                    deferred_objects.append(
                        [pending_preposition, *value]
                    )
                    pending_preposition = None
                    if pending_possession:
                        deferred_objects[-1].extend(
                            pending_possession
                        )
                        pending_possession = None
                elif pending_preposition:
                    output.append(pending_preposition)
                    pending_preposition = None
                elif preposition_applied:
                    preposition_applied = False
                if not pp_deferred:
                    output.extend(value)
                    if pending_possession:
                        output.extend(pending_possession)
                        pending_possession = None
                if use_suppress and (plural_ctx or self._is_plural_form(token)) and any(
                    p.tag.POS == "NOUN" and p.score > 0.3
                    for p in self.morph.parse(token)
                ):
                    suppress_plural_marker = False

            if defer_object and use_suppress and (
                plural_ctx or self._is_plural_form(token)
            ) and any(
                p.tag.POS == "NOUN" and p.score > 0.3
                for p in self.morph.parse(token)
            ):
                suppress_plural_marker = False

        if pending_possession:
            # Посессив без существительного — выводим как есть.
            output.extend(pending_possession)
        if deferred_objects:
            for obj in deferred_objects:
                output.extend(obj)

        output = self._reorder_np_plural_marker(output)

        result = " ".join(output).strip()
        if result and not preserve_punctuation:
            if question:
                result += "?"
            elif exclamation:
                result += "!"
        return result

    # ═══════════════════════════════════════════
    # NP-LEVEL PLURAL MARKER
    # ═══════════════════════════════════════════


    def _special_particle(self, token: str) -> str:
        mapping = {
            "ещё": "ещё", "еще": "ещё",
            "даже": "даж", "именно": "имен",
            "тоже": "тож", "более": "более",
            "самый": "самый", "уже": "уже",
        }
        return mapping.get(token, token)


    @staticmethod
    def _append_punctuation(output: list[str], token: str) -> None:
        """Сохранить знак препинания, не добавляя лишний пробел."""
        if not output:
            return
        if token in {"—", "–"}:
            output.append(token)
        else:
            output[-1] += token

    @staticmethod
    def _is_punctuation(token: str) -> bool:
        return bool(re.fullmatch(r"[!?.,;:—-]", token))

