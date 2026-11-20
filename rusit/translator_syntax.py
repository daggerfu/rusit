"""Syntax/structure mixin for RUSIT translator."""

from __future__ import annotations

from typing import Optional

from .translator_constants import (
    _AMBIGUOUS_POSSESSIVES,
    _DATIVE_PRONOUNS,
    _POSSESSIVES,
    _STANDALONE_POSSESSIVE_LEMMAS,
)

class SyntaxMixin:
    def _restructure_participles(self, tokens: list[str]) -> list[str]:
        """Причастий в РУСИТ нет: определительное причастие
        перестраивается в относительную клаузу.

        Постпозитив (требует запятой): «дом, построенный …»
        → «дом, который кон строи …».
        Препозитив (согласование по роду и числу):
        «созданные ранее артефакты»
        → «артефакт который кон созда ранее».
        Предикативный пассив без запятой не трогаем (§14).
        """
        result = list(tokens)
        # spaCy-разбор построен по исходным токенам, а result меняется
        # при перестройке; храним исходный индекс рядом с каждым токеном,
        # иначе после первой вставки/удаления разбор «съезжает».
        # None — синтетический токен («который», запятая).
        origin: list[int | None] = list(range(len(tokens)))
        i = 0
        while i < len(result):
            token = result[i]
            if not self._is_attributive_participle(token, origin[i]):
                i += 1
                continue

            # Постпозитив: NOUN "," PART
            if (
                i >= 2
                and result[i - 1] == ","
                and self._is_noun_token(result[i - 2])
            ):
                head = result[i - 2]
                result[i - 2 : i + 1] = [head, ",", "который", token]
                origin[i - 2 : i + 1] = [
                    origin[i - 2], None, None, origin[i]
                ]
                i += 3
                continue

            # Препозитив: PART (ADVB)* NOUN с согласованием
            j = i + 1
            while j < len(result) and self._is_adverb_token(result[j]):
                j += 1
            if (
                j < len(result)
                and self._is_noun_token(result[j])
                and not self._is_animate_instrumental(result[j])
                and self._agrees_in_gn(token, result[j])
            ):
                noun = result[j]
                noun_origin = origin[j]
                del result[j]
                del origin[j]
                result[i:i] = [noun, "который"]
                origin[i:i] = [noun_origin, None]
                i += 3
                continue

            i += 1
        return result


    def _is_attributive_participle(
        self, token: str, index: int | None = None
    ) -> bool:
        """spaCy уточняет морфологию: dep=acl/amod — определительное
        причастие, ROOT/ccomp — сказуемое. dep=conj сам по себе не
        показателен: так же помечается однородное определение
        («созданные и написанные книги»), поэтому проверяем голову."""
        if index is not None:
            dep = self._spacy_dep(index)
            if dep in {"ROOT", "ccomp"}:
                return False
            if dep == "conj" and self._conj_head_is_predicate(index):
                return False
            if (
                dep in {"acl", "amod"}
                and self._spacy_morph(index, "VerbForm") == "part"
            ):
                # Перестройка возможна, только если причастие сводится
                # к известной глагольной лексеме. Иначе оставляем
                # застывшую форму как есть (§15.3), без «который».
                return any(
                    p.tag.POS in {"PRTF", "PRTS"}
                    and self._participle_to_verb(p.normal_form)
                    in self.verbs
                    for p in self.morph.parse(token)
                )
        for p in self.morph.parse(token):
            if p.tag.POS not in {"PRTF", "PRTS"}:
                continue
            if self._participle_to_verb(p.normal_form) in self.verbs:
                return True
        return False


    def _conj_head_is_predicate(self, index: int) -> bool:
        """Является ли голова однородного члена сказуемым.

        У однородных определений голова — причастие-определение
        (amod/acl), у однородных сказуемых — финитный глагол или
        корневое/зависимое сказуемое."""
        seen: set[int] = set()
        current = index
        while current not in seen:
            seen.add(current)
            head_index = self._spacy_head_index(current)
            if head_index is None:
                return False
            head = self._spacy_token(head_index)
            if head is None:
                return False
            if head.pos_ not in {"VERB", "AUX"}:
                return False
            if "Fin" in head.morph.get("VerbForm"):
                return True
            if head.dep_ in {"ROOT", "ccomp"}:
                return True
            if head.dep_ != "conj":
                return False
            current = head_index
        return False


    def _is_noun_token(self, token: str) -> bool:
        return any(
            p.tag.POS == "NOUN"
            for p in self.morph.parse(token)
        )


    def _is_adverb_token(self, token: str) -> bool:
        return any(
            p.tag.POS == "ADVB"
            for p in self.morph.parse(token)
        )


    def _agrees_in_gn(self, participle: str, noun: str) -> bool:
        """Согласование причастия с существительным: число обязательно,
        род — когда у причастия он выражен (во мн.ч. pymorphy
        род причастия пустой, а существительное сохраняет)."""
        p_gn = [
            (p.tag.gender, p.tag.number)
            for p in self.morph.parse(participle)
            if p.tag.POS in {"PRTF", "PRTS"}
        ]
        for p in self.morph.parse(noun):
            if p.tag.POS != "NOUN":
                continue
            for gender, number in p_gn:
                if p.tag.number != number:
                    continue
                if gender is None or gender == p.tag.gender:
                    return True
        return False

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


    def _next_meaningful_token(
        self, tokens: list[str], index: int
    ) -> Optional[str]:
        for tok in tokens[index + 1:]:
            if not self._is_punctuation(tok):
                return tok
        return None


    def _modal_predicate_ahead(
        self, tokens: list[str], index: int
    ) -> bool:
        """Дальше по клаузе стоит модальный предикатор (§12)."""
        for tok in tokens[index + 1:]:
            if self._is_punctuation(tok):
                return False
            if tok in {"не", "уже", "ещё", "еще", "же", "ли", "бы"}:
                continue
            return tok in self.modal_predicates
        return False


    def _starts_new_clause(self, tokens: list[str], index: int) -> bool:
        """После границы начинается клауза со своим подлежащим.

        У такой клаузы собственный предикат, поэтому TAM-маркеры
        предыдущей клаузы на неё не распространяются (§7.8, §21.1)."""
        for j in range(index + 1, len(tokens)):
            tok = tokens[j]
            if self._is_punctuation(tok):
                return False
            if tok in self.relative_pronouns:
                return True
            if tok in self.conjunctions:
                continue
            return any(
                p.tag.POS in {"NPRO", "NOUN"}
                and "nomn" in str(p.tag)
                for p in self.morph.parse(tok)
            )
        return False


    def _is_possessive_position(
        self, tokens: list[str], index: int
    ) -> bool:
        """«его/ее/их» перед именем — притяжание (§4.2).

        В остальных позициях это личные местоимения:
        «вижу его» → «види он», а не «види у он».
        """
        pos = self._spacy_pos(index)
        dep = self._spacy_dep(index)
        if pos == "DET" and dep in {"det", "nmod", "amod"}:
            return True
        if pos == "PRON" and dep in {"obj", "iobj", "obl"}:
            return False
        next_tok = self._next_meaningful_token(tokens, index)
        if next_tok is None or next_tok in self.conjunctions:
            return False
        if (
            next_tok in self.nouns
            or next_tok in self.qualifiers
            or next_tok in self.relative_adjectives
        ):
            return True
        return any(
            p.tag.POS in {"NOUN", "ADJF", "PRTF"}
            for p in self.morph.parse(next_tok)
        )


    def _possessive_owner(self, token: str) -> Optional[str]:
        """Притяжательное прилагательное («мамин») → владелец.

        Леммы на «-ин» дают владельца через основу + «-а»:
        мамин → мама, папин → папа, бабушкин → бабушка.
        """
        for p in self.morph.parse(token):
            if p.tag.POS != "ADJF" or "Poss" not in str(p.tag):
                continue
            lemma = p.normal_form.replace("ё", "е")
            if lemma.endswith("ин"):
                return lemma[:-2] + "а"
        return None


    def _standalone_possessive(
        self, token: str, tokens: list[str], index: int
    ) -> Optional[str]:
        """Каноническая форма притяжательного-лексемы.

        «мой/твой/наш/ваш/свой» и их склонённые формы сохраняются
        как отдельные неизменяемые лексемы.
        """
        for p in self.morph.parse(token):
            if p.tag.POS != "ADJF" or "Apro" not in str(p.tag):
                continue
            lemma = p.normal_form.replace("ё", "е")
            if lemma not in _STANDALONE_POSSESSIVE_LEMMAS:
                continue
            # «мой/моя/мою/моё» омонимичны формам глагола «мыть».
            if self._has_competing_verb_parse(token, p):
                if not self._possessive_agrees_with_next(
                    token, p, tokens, index
                ):
                    return None
                # При согласовании всё ещё возможен глагол; для
                # явного императива «мой» отдаём приоритет глаголу,
                # если перед существительным нет типичного
                # притяжательного контекста с согласованием.
                if token == "мой" and self._has_imperative_parse(token):
                    # «мой дом» (согласование) — притяжание;
                    # «мой руки» (нет) — уже отсеяно выше.
                    return lemma
            return lemma
        return None


    def _has_competing_verb_parse(self, token: str, poss_parse) -> bool:
        """Есть неглагольно-притяжательный разбор того же токена как глагола."""
        for p in self.morph.parse(token):
            if p.tag.POS in {"VERB", "INFN", "GRND"}:
                if p.normal_form.replace("ё", "е") == "мыть":
                    return True
        return False


    def _possessive_agrees_with_next(
        self, token: str, poss_parse, tokens: list[str], index: int
    ) -> bool:
        """Грубая проверка согласования притяжательного со следующим именем."""
        next_tok = self._next_meaningful_token(tokens, index)
        if next_tok is None:
            return False
        next_parses = self.morph.parse(next_tok)
        for np in next_parses:
            if np.tag.POS not in {"NOUN", "ADJF", "PRTF"}:
                continue
            # Сравниваем число/род/падеж где применимо.
            if poss_parse.tag.number and np.tag.number:
                if poss_parse.tag.number != np.tag.number:
                    continue
            if poss_parse.tag.gender and np.tag.gender:
                if (
                    poss_parse.tag.number == "sing"
                    and np.tag.number == "sing"
                    and poss_parse.tag.gender != np.tag.gender
                ):
                    continue
            if poss_parse.tag.case and np.tag.case:
                if poss_parse.tag.case == np.tag.case:
                    return True
                # Одушевлённый винительный ~ родительный — пропускаем
                # строгую проверку падежа.
            return True
        return False


    def _has_imperative_parse(self, token: str) -> bool:
        """Есть разбор императива глагола."""
        for p in self.morph.parse(token):
            if p.tag.POS == "VERB" and "impr" in str(p.tag):
                return True
        return False


    def _is_my_verb_form(
        self, token: str, tokens: list[str], index: int
    ) -> bool:
        """Токен — форма глагола «мыть», а не притяжательное «мой»."""
        # Только неоднозначные с притяжательным «мой» формы.
        if token not in {"мой", "моя", "мою", "мое", "моём", "моем"}:
            return False
        poss_parse = None
        has_wash = False
        for p in self.morph.parse(token):
            lemma = p.normal_form.replace("ё", "е")
            if p.tag.POS in {"VERB", "INFN", "GRND"} and lemma == "мыть":
                has_wash = True
            if p.tag.POS == "ADJF" and "Apro" in str(p.tag) and lemma == "мой":
                poss_parse = p
        if not has_wash or poss_parse is None:
            return False
        # Если есть согласованное именное зависимое — притяжание.
        if self._possessive_agrees_with_next(
            token, poss_parse, tokens, index
        ):
            return False
        # «мой руки» — императив с несогласованным объектом.
        # Одиночное/предикативное «мой» оставляем притяжанием.
        next_tok = self._next_meaningful_token(tokens, index)
        if next_tok is None:
            return False
        for np in self.morph.parse(next_tok):
            if np.tag.POS in {"NOUN", "ADJF", "PRON", "NPRO"}:
                return True
        return False


    def _fronted_accusative_object(
        self, tokens: list[str], index: int
    ) -> bool:
        """Имя перед сказуемым при явном подлежащем: «мы заявления
        принимаем». Собственная forme nomn у имени здесь не мешает —
        подлежащее уже выражено отдельным словом слева."""
        if not any(
            p.tag.POS in {"NOUN", "NPRO"}
            and p.tag.case == "accs"
            for p in self.morph.parse(tokens[index])
        ):
            return False
        subject_before = False
        for tok in tokens[:index]:
            if self._is_punctuation(tok):
                continue
            if any(
                p.tag.POS in {"NPRO", "NOUN"} and p.tag.case == "nomn"
                for p in self.morph.parse(tok)
            ):
                subject_before = True
                break
        if not subject_before:
            return False
        for tok in tokens[index + 1:]:
            if self._is_punctuation(tok):
                continue
            if any(p.tag.POS in {"VERB", "INFN"} for p in self.morph.parse(tok)):
                return True
        return False

    def _should_defer_direct_object(
        self,
        token: str,
        tokens: list[str],
        index: int,
        predicate_index: Optional[int],
        pending_preposition: Optional[str],
        preposition_applied: bool,
    ) -> bool:
        """Прямое дополнение перед сказуемым → отложить для SVO.

        ``predicate_index`` — индекс последнего выданного сказуемого.
        Сказуемое более ранней клаузы не мешает отложить дополнение
        своей («…укусила и ее загнала» → «…укуси и загна она»), но
        эвристики pymorphy после него уже не применяются: они путают
        подлежащее/топик следующей клаузы с дополнением."""
        if pending_preposition or preposition_applied:
            return False
        if token in _DATIVE_PRONOUNS:
            return False
        dep = self._spacy_dep(index)
        if dep == "nsubj":
            return False
        head_index = self._spacy_head_index(index)
        if dep in {"obj", "iobj"} and head_index is not None:
            return head_index > index and (
                predicate_index is None
                or head_index > predicate_index
            )
        # Личные/возвратные местоимения в винительном (объектном) значении.
        # spaCy на разговорном порядке ошибается («…и её на дерево
        # загнала» → dep=case), поэтому здесь доверяем морфологии —
        # но только если в клаузе после сказуемого есть свой глагол.
        acc_forms = {
            "меня", "тебя", "его", "ее", "её", "нас", "вас", "их",
            "себя", "него", "нее", "неё", "них",
        }
        if token in acc_forms:
            # Исключаем именительный: «он/она/оно/они» сюда не попадают.
            # «его/её/их» могут быть притяжательными — те обрабатываются раньше.
            # Нужен разбор с объектным падежом.
            for p in self.morph.parse(token):
                if p.tag.POS in {"NPRO", "PRON"} and p.tag.case in {"accs", "gent"}:
                    lemma = p.normal_form.replace("ё", "е")
                    if lemma in {"я", "ты", "он", "она", "оно", "мы", "вы", "они", "себя"}:
                        return self._has_predicate_after(
                            tokens, index, predicate_index
                        )
            if token in {"меня", "тебя", "нас", "вас", "себя"}:
                return self._has_predicate_after(
                    tokens, index, predicate_index
                )
            return False
        if predicate_index is not None:
            return False
        if self._fronted_accusative_object(tokens, index):
            return True
        # Имена/существительные в аккузативе перед глаголом — осторожно,
        # чтобы не сломать SVO, где объект уже после глагола (нормальный случай
        # сюда не попадает, т.к. глагол ещё не встречен в SOV/OVS).
        # Ограничимся явным SOV/OSV с неодушевлённым/одушевлённым acc
        # только если это не подлежащее (nomn).
        has_nomn_subject = any(
            p.tag.case == "nomn" and p.tag.POS in {"NPRO", "PRON", "NOUN"}
            for p in self.morph.parse(token)
        )
        if has_nomn_subject:
            return False
        has_acc = any(
            p.tag.case == "accs" and p.tag.POS in {"NOUN", "NPRO", "PRON"}
            for p in self.morph.parse(token)
        )
        if not has_acc:
            return False
        # Проверяем, что дальше в предложении есть глагол-сказуемое,
        # иначе это может быть не SOV.
        for j in range(index + 1, len(tokens)):
            t = tokens[j]
            if self._is_punctuation(t):
                continue
            for p in self.morph.parse(t):
                if p.tag.POS in {"VERB", "INFN"}:
                    return True
            # причастие-предикат тоже возможно, но лучше быть консервативным
        return False


    def _has_predicate_after(
        self,
        tokens: list[str],
        index: int,
        predicate_index: Optional[int] = None,
    ) -> bool:
        """Есть ли в клаузе глагол после указанного токена.

        Учитываются только позиции после уже выданного сказуемого:
        глагол предыдущей клаузы объект не подтверждает."""
        for j in range(index + 1, len(tokens)):
            if predicate_index is not None and j <= predicate_index:
                continue
            if self._is_punctuation(tokens[j]):
                continue
            if any(
                p.tag.POS in {"VERB", "INFN"}
                for p in self.morph.parse(tokens[j])
            ):
                return True
        return False


    def _is_form_of(self, token: str, lemma: str) -> bool:
        return any(
            p.normal_form.replace("ё", "е") == lemma
            for p in self.morph.parse(token)
        )


    def _accusative_context(
        self, tokens: list[str], index: int
    ) -> bool:
        """Паттерн «V + прилагательное + существительное»:
        винительный падеж одушевлённого совпадает с родительным,
        родительный маркер не нужен («вижу большого человека»)."""
        meaningful = [
            t for t in tokens[:index] if not self._is_punctuation(t)
        ]
        if len(meaningful) < 2:
            return False
        adj, verb = meaningful[-1], meaningful[-2]
        if not any(
            p.tag.POS in {"VERB", "INFN"}
            for p in self.morph.parse(verb)
        ):
            return False
        return any(
            p.tag.POS in {"ADJF", "PRTF"}
            for p in self.morph.parse(adj)
        )


    def _plural_modifier_before(
        self, tokens: list[str], index: int
    ) -> bool:
        """Предыдущее значимое слово — множественное прилагательное,
        причастие или определитель («заинтересованные стороны»)."""
        prev = None
        for tok in tokens[:index]:
            if not self._is_punctuation(tok):
                prev = tok
        if prev is None:
            return False
        # Само количественное слово тоже может иметь множественный
        # разбор («многие» = ADJF plur) — оно не создаёт plural_ctx.
        if prev in {
            "много", "многие", "многих", "многим",
            "несколько", "нескольких", "множество",
        }:
            return False
        # «его книга» / «его книги»: неопределённая форма 3-го лица
        # сама по себе не делает следующее имя множественным.
        # Но слабо различаемые формы («книги») всё же должны получить
        # маркер «много», поэтому смотрим разбор самого имени.
        if prev in _AMBIGUOUS_POSSESSIVES and index < len(tokens):
            return any(
                p.tag.POS == "NOUN" and p.tag.number == "plur"
                for p in self.morph.parse(tokens[index])
            )
        for p in self.morph.parse(prev):
            if (
                p.tag.POS in {"ADJF", "PRTF", "PRTS"}
                and p.tag.number == "plur"
            ):
                return True
        return False


    def _quantifier_before(
        self, tokens: list[str], index: int
    ) -> bool:
        """Перед существительным стоит количественное слово."""
        prev = None
        for tok in tokens[:index]:
            if not self._is_punctuation(tok):
                prev = tok
        if prev is None:
            return False
        if prev in {
            "много", "многие", "многих", "многим",
            "несколько", "нескольких", "множество",
        }:
            return True
        return self._is_numeral(prev)

    # ═══════════════════════════════════════════
    # TAM + ASPECT
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
    # СРАВНИТЕЛЬНАЯ СТЕПЕНЬ (§5.4)
    # ═══════════════════════════════════════════


    def _comparison_context(
        self, tokens: list[str], index: int
    ) -> bool:
        """Контекст сравнения: COMP-форма с именным подлежащим слева.
        «Больше людей пришло» — количественное слово: подлежащего
        слева нет. «Беги быстрее» — наречие: слева глагол,
        а не имя. Стандарт сравнения («меня», «брата») необязателен:
        «это хуже» → «этот более плохой»."""
        prev = None
        for tok in tokens[:index]:
            if not self._is_punctuation(tok):
                prev = tok
        if prev is None:
            return False
        if not self._is_nominal(prev) and prev not in self.pronouns:
            return False
        return True


    def _comparative_positive(self, token: str) -> Optional[str]:
        """COMP-форма → полная каноническая форма прилагательного.

        Лемма COMP у pymorphy обычно уже прилагательное
        («больше» → «большой»); у слов типа «выше» лемма —
        наречие «высоко», и полная форма выводится заменой
        конечного «-о» на «-ий»/«-ой». Если полной формы в
        лексиконе нет, слово не трогаем."""
        for p in self.morph.parse(token):
            if p.tag.POS != "COMP":
                continue
            lemma = p.normal_form.replace("ё", "е")
            # Супплетивные сравнительные: «старше» → «старый»
            # (лемма у pymorphy — «старший», а не «старый»).
            lemma = {
                "старший": "старый",
                "младший": "молодой",
                "лучший": "хороший",
                "худший": "плохой",
            }.get(lemma, lemma)
            if lemma in self.qualifiers:
                return self.qualifiers[lemma]
            for candidate in (lemma[:-1] + "ий", lemma[:-1] + "ой"):
                if candidate in self.qualifiers:
                    return self.qualifiers[candidate]
            return None
        return None

    # ═══════════════════════════════════════════
    # Родительный → у
    # ═══════════════════════════════════════════


    def _find_passive_agent(
        self, tokens: list[str], verb_index: int
    ) -> Optional[int]:
        agent_index = self._spacy_agent_index(verb_index)
        # Агент перед сказуемым («братом была написана книга») уже
        # выдан в обычном порядке — второй раз его не добавляем.
        if agent_index is not None and agent_index > verb_index:
            return agent_index
        for index in range(verb_index + 1, len(tokens)):
            token = tokens[index]
            if self._is_punctuation(token):
                continue
            if token in self.prepositions or token in self.conjunctions:
                continue
            if self._is_animate_instrumental(token):
                return index
            if self._is_nominal(token):
                return None
        return None

