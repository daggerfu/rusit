"""Verb/morphology mixin for RUSIT translator."""

from __future__ import annotations

import re
from typing import Optional

class VerbsMixin:
    def _process_imperative(
        self, token: str
    ) -> Optional[List[str]]:
        parses = self.morph.parse(token)

        impr_parses = [
            p for p in parses if "impr" in str(p.tag)
        ]
        if not impr_parses:
            return None

        parse = max(impr_parses, key=lambda p: p.score)

        # Омонимия «попали» = прош.вр. «попасть» / имп. «попалить»:
        # если императивный разбор — неизвестный глагол, а рядом
        # разбор с известной леммой не хуже по score, императиву
        # не бывать — слово пойдёт по обычной глагольной ветке.
        if parse.normal_form not in self.verbs:
            rivals = [
                p
                for p in parses
                if p.tag.POS in {"VERB", "INFN"}
                and p.normal_form in self.verbs
                and p.score >= parse.score
            ]
            if rivals:
                return None

            # «день» — существительное, а не императив редкого «деть»:
            # именной разбор с заметно большей массой перевешивает
            # случайный императивный разбор неизвестного глагола.
            nominal_rivals = [
                p
                for p in parses
                if "impr" not in str(p.tag)
                and p.tag.POS in {"NOUN", "ADJF", "ADJS", "PRON", "NPRO"}
                and p.score > parse.score
            ]
            if nominal_rivals:
                return None

        lemma = parse.normal_form
        reflexive = lemma.endswith(("ся", "сь"))
        lexeme = self._imperative_from_lexeme(
            self._verb_lexeme(lemma)
        )
        tag_str = str(parse.tag)

        result = [lexeme]
        if reflexive:
            result.append(self._particle("reflexive", "ся"))
        if "plur" in tag_str:
            result.insert(0, self._particle("imperative_you", "вы"))
        return result


    def _imperative_from_lexeme(self, lexeme: str) -> str:
        """Каноническая лексема уже является формой императива (§8)."""
        return lexeme

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
        candidates = [
            p
            for p in parses
            if p.tag.POS in {
                "VERB", "INFN", "PRTF", "PRTS", "GRND", "ADJS",
            }
        ]
        if not candidates:
            return None

        # Предпочитаем глагольный разбор известного глагола:
        # у форм типа «читаем» pymorphy ставит на первое место
        # краткое причастие («читаемый»), что даёт ложный пассив.
        parse = next(
            (
                p
                for p in candidates
                if p.tag.POS in {"VERB", "INFN"}
                and p.normal_form in self.verbs
            ),
            candidates[0],
        )

        lemma = parse.normal_form

        if lemma == "быть":
            return None

        # ── Краткое причастие / прилагательное = пассив ──
        if parse.tag.POS in {"PRTF", "PRTS", "ADJS"}:
            # Защита: неизвестное слово с морфологическим разбором
            # «краткое прилагательное» (напр. «зоркало») — не пассив,
            # а неизвестное слово; оно пройдёт в вывод как есть.
            verb_lemma = self._participle_to_verb(parse.normal_form)
            if verb_lemma not in self.verbs:
                return None
            return self._process_participle(
                parse, token, tokens, index
            )

        # ── Мутатив ──
        # «становиться» тоже мутатив, а не возвратный глагол.
        if lemma in {"стать", "становиться"}:
            result = self._tense_and_aspect(parse, lemma)
            result.append(self._particle("mutative_state", "ста"))
            return result, False

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

        # ── Фаза (БЕЗ маркера времени) ──
        if lemma in {"начать", "начинать"}:
            return [self._particle("inchoative", "нач")], False

        if lemma in {"перестать", "переставать"}:
            return [self._particle("cessative", "пере")], False

        if lemma in {"продолжить", "продолжать"}:
            return [self._particle("continuative", "прод")], False

        # ── Обычный глагол ──
        # Неизвестная лемма допускается, только если словоформа
        # уверенно глагольная (суммарная масса глагольных разборов);
        # тогда лексема выводится от основы («закрыть» → «закры»).
        # Иначе («русит» как имя: масса существительных выше)
        # слово пройдёт дальше и сохранится как есть.
        if lemma not in self.verbs:
            verb_mass = sum(
                p.score
                for p in parses
                if p.tag.POS
                in {"VERB", "INFN", "PRTF", "PRTS", "GRND"}
            )
            if verb_mass < 0.5:
                return None

        lexeme = self._verb_lexeme(lemma)
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

        # Граничная частица: завершённость. Завершённый пассив —
        # кон; действительное причастие несовершенного вида
        # («человек, который сиди») — без частицы.
        aspect = parse.tag.aspect
        tag_str = str(parse.tag)
        passive = "pssv" in tag_str
        past = "past" in tag_str
        if aspect == "perf" or (passive and past):
            result.append(self._particle("telic", "кон"))

        verb_lemma = self._participle_to_verb(parse.normal_form)
        result.append(self._verb_lexeme(verb_lemma))

        return result, True


    def _participle_to_verb(self, participle_lemma: str) -> str:
        for p in self.morph.parse(participle_lemma):
            if p.tag.POS == "INFN":
                return p.normal_form

        # Раньше здесь было совпадение первых трёх букв с лексемой
        # глагола: «красивый» превращалось в «красть» → «крад».
        # Надёжные источники — инфинитив из разбора и суффикс
        # причастия; короткий префикс даёт слишком много ложных пар.
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
            if p.tag.POS in {"PRTF", "PRTS", "ADJS"}:
                return True
        return False

    # ═══════════════════════════════════════════
    # МУТАТИВ
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


    def _dedupe_tam(
        self, result: list[str], emitted: set[str]
    ) -> list[str]:
        """Не повторять показатели времени/границы в одном предложении.

        Валидатор допускает не более одной граничной частицы на фразу,
        поэтому второй и последующие глаголы сохраняют только лексему
        (и, если нужно, ещё не встречавшуюся граничную частицу).
        """
        repeatable = {
            "был", "буд",
            "кон", "нач", "пере", "прод", "получ", "перест",
        }
        out: list[str] = []
        for part in result:
            if part in repeatable:
                if part in emitted:
                    continue
                emitted.add(part)
            out.append(part)
        return out

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
        aspect = parse.tag.aspect

        # Прошедшее совершенное вида выражается одной граничной
        # частицей «кон»: отдельный показатель «был» не нужен
        # (ср. «я кон купи книга»). Несовершенное прошедшее
        # по-прежнему маркируется «был».
        if tense == "past":
            if aspect != "perf":
                result.append(self._particle("past", "был"))
        elif tense == "futr":
            result.append(self._particle("future", "буд"))

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


    def _is_instrumental(self, token: str) -> bool:
        for parse in self.morph.parse(token):
            if (
                parse.tag.POS in {
                    "NOUN", "ADJF", "PRTF", "NPRO",
                }
                and "ablt" in str(parse.tag)
                and parse.score > 0.5
            ):
                return True
        return False


    def _is_animate_instrumental(self, token: str) -> bool:
        """Одушевлённое существительное в творительном —
        кандидат в агенты пассива. Неодушевлённое («артефактами»)
        — главное слово причастия, а не агент."""
        for parse in self.morph.parse(token):
            if (
                parse.tag.POS == "NOUN"
                and "ablt" in str(parse.tag)
                and "anim" in str(parse.tag)
            ):
                return True
        return False

    # ═══════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════

