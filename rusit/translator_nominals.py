"""Nominal/NP mixin for RUSIT translator."""

from __future__ import annotations

import re
from typing import Optional

from .translator_constants import _PRONOUN_FALLBACKS

class NominalsMixin:
    def _reorder_np_plural_marker(self, output: list[str]) -> list[str]:
        """Маркер множественности NP ставится перед всей группой."""
        result = list(output)
        i = 0
        while i < len(result):
            if result[i] != "много":
                i += 1
                continue
            # «много» перед существительным — маркер множественности NP.
            if i + 1 >= len(result):
                i += 1
                continue
            if not self._is_noun_like_output(result[i + 1]):
                i += 1
                continue
            j = i - 1
            while j >= 0 and self._is_np_modifier_output(result[j]):
                j -= 1
            insert_pos = j + 1
            if insert_pos < i:
                marker = result.pop(i)
                result.insert(insert_pos, marker)
                i = insert_pos + 1
            else:
                i += 1
        return result


    def _is_noun_like_output(self, token: str) -> bool:
        if token in self.nouns.values():
            return True
        if token in self.pronouns.values():
            return False
        # Составные/дефисные формы: проверяем голову.
        if "-" in token:
            head = token.rsplit("-", 1)[1]
            return self._is_noun_like_output(head)
        for p in self.morph.parse(token):
            if p.tag.POS == "NOUN":
                return True
        return False


    def _is_np_modifier_output(self, token: str) -> bool:
        # Определения в составе NP (прилагательные/квалификаторы).
        if token in {"этот", "эти", "тот", "те", "каждый", "любой",
                     "один", "мой", "твой", "наш", "ваш", "свой"}:
            return False
        if token in self.qualifiers.values():
            return True
        if token in self.relative_adjectives:
            return True
        for p in self.morph.parse(token):
            if p.tag.POS == "ADJF":
                return True
        return False

    # ═══════════════════════════════════════════
    # ПРИЧАСТНЫЕ ОБОРОТЫ → «который» + КЛАУЗА (§15.3)
    # ═══════════════════════════════════════════


    def _nominal_output(
        self,
        token: str,
        force_plural: bool = False,
        suppress_plural_marker: bool = False,
    ) -> list[str]:
        # РУСИТ использует грамматически нейтральное число: сама форма
        # существительного не сообщает, один предмет или несколько.
        # Количество выражается только явным словом (числительное, много,
        # эти, все, несколько, ...), которое уже выведено в поток.
        # Поэтому force_plural здесь не используется.
        if token in self.pronouns:
            return self.pronouns[token].split()
        if token in _PRONOUN_FALLBACKS:
            return [_PRONOUN_FALLBACKS[token]]
        if token in self.relative_pronouns:
            return self.relative_pronouns[token].split()

        # Дефисный композит: «бизнес-процессы» → «много бизнес-процесс».
        if "-" in token:
            head, tail = token.rsplit("-", 1)
            if re.fullmatch(r"[а-я]+", head) and re.fullmatch(
                r"[а-я]+", tail
            ):
                parts = self._nominal_output(
                    tail,
                    force_plural=force_plural,
                    suppress_plural_marker=suppress_plural_marker,
                )
                if len(parts) > 1 and parts[0] == "много":
                    return ["много", head + "-" + parts[1]]
                return [head + "-" + parts[0]]

        # Нейтральное число: каноническая лексема без маркера «много».
        # Маркер появляется в потоке только от явного квантификатора.
        if force_plural:
            if self._is_nominal(token):
                # Маркер «много» относится к существительному-вершине NP,
                # а не к согласованным определениям.
                is_noun_head = any(
                    p.tag.POS == "NOUN" and p.score > 0.3
                    for p in self.morph.parse(token)
                )
                if is_noun_head:
                    base = self._get_singular_base(token)
                    if suppress_plural_marker:
                        return [base]
                    return ["много", base]
                # Прилагательное/определение в составе множественной NP:
                # каноническая форма без отдельного маркера числа.
                parses = self.morph.parse(token)
                for p in parses:
                    if p.tag.POS == "ADJF" and p.score > 0.1:
                        lemma = p.normal_form.replace("ё", "е")
                        if lemma in self.qualifiers or lemma in self.relative_adjectives:
                            return [lemma]
                for p in parses:
                    if p.tag.POS == "ADJF" and p.score > 0.1:
                        return [p.normal_form.replace("ё", "е")]
                for p in parses:
                    if p.tag.POS == "ADJS" and p.score > 0.5:
                        return [p.normal_form.replace("ё", "е")]

        if token in self.nouns:
            return self.nouns[token].split()
        if token in self.qualifiers:
            return self.qualifiers[token].split()
        if token in self.relative_adjectives:
            return [token]

        # Неизвестное слово → сохранить
        if not self._is_known_morphological_nominal(token):
            # Прилагательное неизвестного происхождения всё же
            # сохраняет полную каноническую форму (§5.2):
            # «заинтересованные стороны» → «заинтересованный …».
            # Только ADJF: каноническая форма PRTF у pymorphy —
            # инфинитив, а не полная форма причастия.
            for p in self.morph.parse(token):
                if p.tag.POS == "ADJF" and p.score > 0.1:
                    return [p.normal_form.replace("ё", "е")]
            # Краткое прилагательное → полная каноническая форма:
            # «необязательны» → «необязательный».
            # Порог выше, чем у ADJF: неизвестные слова («зоркало»)
            # имеют низкий score краткого разбора.
            for p in self.morph.parse(token):
                if p.tag.POS == "ADJS" and p.score > 0.7:
                    return [p.normal_form.replace("ё", "е")]
            # Неизвестное существительное → лемма
            # («последовательности» → «последовательность»).
            for p in self.morph.parse(token):
                if p.tag.POS == "NOUN" and p.score > 0.1:
                    return [p.normal_form.replace("ё", "е")]
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
            if p.tag.POS not in {
                "NOUN", "ADJF", "PRON", "NPRO",
            }:
                continue
            # Лемма из лексикона узнаётся независимо от score:
            # иначе формы типа «темным» (score ≈ 0.4) уходят
            # в неизвестные слова вместо нормализации к полной форме.
            lemma = p.normal_form.replace("ё", "е")
            if (
                lemma in self.nouns
                or lemma in self.qualifiers
                or lemma in self.relative_adjectives
            ):
                return True
            if p.score > 0.7:
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
            lemma = parse.normal_form.replace("ё", "е")
            if lemma in self.nouns:
                return self.nouns[lemma]
            return lemma

        if parse.tag.POS in {"ADJF", "ADJS"}:
            # Прилагательное сохраняет полную каноническую форму (§5.2).
            # При омонимии («большим» = «большой» / «больший»)
            # предпочитаем разбор с леммой из лексикона.
            for p in parses:
                lemma = p.normal_form.replace("ё", "е")
                if p.tag.POS in {"ADJF", "ADJS"} and (
                    lemma in self.qualifiers
                    or lemma in self.relative_adjectives
                ):
                    return lemma
            return parse.normal_form.replace("ё", "е")

        if parse.tag.POS == "ADVB":
            return token

        if parse.tag.POS in {"NPRO", "PRON"}:
            lemma = parse.normal_form.replace("ё", "е")
            if lemma in self.pronouns:
                return self.pronouns[lemma]
            if lemma in _PRONOUN_FALLBACKS:
                return _PRONOUN_FALLBACKS[lemma]
            return lemma

        return parse.normal_form

    # ═══════════════════════════════════════════
    # есть₂
    # ═══════════════════════════════════════════


    def _is_genitive_noun(self, token: str) -> bool:
        for parse in self.morph.parse(token):
            if parse.tag.POS == "NOUN" and parse.score > 0.5:
                if "gent" in str(parse.tag):
                    return True
        return False


    def _verb_accusative_plural(
        self, tokens: list, index: int, token: str
    ) -> bool:
        """Формы типа «заявления» (род. ед. = вин. мн.): после глагола
        читаются как винительный множественный
        («принимаем заявления» → «принима много заявление»),
        а не как родительный («у заявление»)."""
        if not any(
            p.tag.POS == "NOUN"
            and "accs" in str(p.tag)
            and p.tag.number == "plur"
            for p in self.morph.parse(token)
        ):
            return False
        if self._fronted_accusative_object(tokens, index):
            return True
        prev = None
        for tok in tokens[:index]:
            if not self._is_punctuation(tok):
                prev = tok
        if prev is None:
            return False
        return any(
            p.tag.POS in {"VERB", "INFN"}
            for p in self.morph.parse(prev)
        )

    # ═══════════════════════════════════════════
    # PASSIVE
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


    _ORDINAL_CARDINALS = {
        "первый": "один",
        "второй": "два",
        "третий": "три",
        "четвертый": "четыре",
        "пятый": "пять",
        "шестой": "шесть",
        "седьмой": "семь",
        "восьмой": "восемь",
        "девятый": "девять",
        "десятый": "десять",
    }


    def _ordinal_cardinal(self, token: str) -> Optional[str]:
        """Порядковое прилагательное → числительное для «номер» (§6.3)."""
        for parse in self.morph.parse(token):
            if parse.tag.POS not in {"ADJF", "ADJS"}:
                continue
            lemma = parse.normal_form.replace("ё", "е")
            return self._ORDINAL_CARDINALS.get(lemma)
        return None


    def _numeral_base(self, token: str) -> str:
        if re.fullmatch(r"\d+", token):
            return token
        parses = self.morph.parse(token)
        return parses[0].normal_form if parses else token


    def _determiner(self, token: str) -> Optional[str]:
        if token in {"один", "одна", "одно", "одни"}:
            return "один"
        if token in {"этот", "эта", "это"}:
            return "этот"
        if token == "эти":
            return "эти"
        if token in {"тот", "та", "то"}:
            return "тот"
        if token == "те":
            return "те"
        if token in {"все", "весь", "вся", "всё"}:
            return "все"
        if token in {"каждый", "каждая", "каждое"}:
            return "каждый"
        if token == "любой":
            return "любой"
        # Склонённые формы: «этом», «того», «одним» и т.п.
        for p in self.morph.parse(token):
            lemma = p.normal_form.replace("ё", "е")
            if lemma == "этот":
                return "эти" if p.tag.number == "plur" else "этот"
            if lemma == "тот":
                return "те" if p.tag.number == "plur" else "тот"
            if lemma == "один":
                return "один"
            # «некоторые» — выделение части множества.
            if lemma == "некоторый":
                return "некоторые"
        return None

