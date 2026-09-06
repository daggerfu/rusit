"""
РУСИТ 5.0 — Полный набор тестов.
Ревизия 2 спецификации.

Запуск:
    pytest tests/test_rusit.py -v
"""

import time

import pytest

from rusit import RusitTranslator, RusitValidator


# ═══════════════════════════════════════════════
# ФИКСТУРЫ
# ═══════════════════════════════════════════════

@pytest.fixture
def tr():
    """Транслятор в детерминированном режиме."""
    return RusitTranslator()


@pytest.fixture
def validator():
    """Валидатор грамматики РУСИТ 5.0."""
    return RusitValidator()


# ═══════════════════════════════════════════════
# 1. БАЗОВЫЙ SVO
# ═══════════════════════════════════════════════

class TestBasicSVO:

    def test_simple_present(self, tr):
        assert tr.translate("Я читаю книгу.") == "я чита книга"

    def test_simple_present_verb_only(self, tr):
        assert tr.translate("Он спит.") == "он спи"

    def test_simple_with_adverb(self, tr):
        result = tr.translate("Я быстро читаю книгу.")
        assert "чита" in result
        assert "книга" in result

    def test_subject_verb(self, tr):
        assert tr.translate("Она работает.") == "она работа"

    def test_verb_with_prepositional_object(self, tr):
        result = tr.translate("Я живу в городе.")
        assert "живи" in result
        assert "в" in result
        assert "город" in result


# ═══════════════════════════════════════════════
# 2. ВРЕМЕНА
# ═══════════════════════════════════════════════

class TestTense:

    def test_present_no_marker(self, tr):
        result = tr.translate("Я читаю.")
        assert "был" not in result
        assert "буд" not in result
        assert result == "я чита"

    def test_past(self, tr):
        assert tr.translate("Я читал книгу.") == "я был чита книга"

    def test_past_feminine(self, tr):
        result = tr.translate("Она читала книгу.")
        assert result == "она был чита книга"

    def test_past_plural(self, tr):
        result = tr.translate("Они читали книгу.")
        assert result == "они был чита книга"

    def test_future(self, tr):
        assert tr.translate("Я буду читать книгу.") == "я буд чита книга"

    def test_future_simple(self, tr):
        result = tr.translate("Мы будем строить дом.")
        assert result == "мы буд строи дом"

    @pytest.mark.parametrize(
        "sentence,expected",
        [
            ("Я читаю.", "я чита"),
            ("Я читал.", "я был чита"),
            ("Я буду читать.", "я буд чита"),
        ],
    )
    def test_tense_exact(self, tr, sentence, expected):
        assert tr.translate(sentence) == expected


# ═══════════════════════════════════════════════
# 3. ВИД / ЗАВЕРШЁННОСТЬ
# ═══════════════════════════════════════════════

class TestAspect:

    def test_perfective_telic(self, tr):
        result = tr.translate("Я прочитал книгу.")
        assert result == "я был кон чита книга"

    def test_imperfective_no_marker(self, tr):
        result = tr.translate("Я читал книгу.")
        assert result == "я был чита книга"
        assert "кон" not in result

    def test_past_perfective(self, tr):
        assert tr.translate("Я прочитал книгу.") == "я был кон чита книга"

    def test_future_perfective(self, tr):
        assert tr.translate("Я прочитаю книгу.") == "я буд кон чита книга"

    def test_perfective_close(self, tr):
        result = tr.translate("Они закрыли окна.")
        assert "кон" in result
        assert "закры" in result
        assert "окно" in result

    def test_perfective_build(self, tr):
        result = tr.translate("Мы построили дом.")
        assert result == "мы был кон строи дом"

    def test_perfective_write(self, tr):
        result = tr.translate("Он написал письмо.")
        assert result == "он был кон писа письмо"


# ═══════════════════════════════════════════════
# 4. РЕЗУЛЬТАТИВНЫЕ ОПЕРАТОРЫ
# ═══════════════════════════════════════════════

class TestResultativeOperators:

    def test_uznat(self, tr):
        result = tr.translate("Я узнал ответ.")
        assert "получ" in result
        assert "зна" in result
        assert "кон" not in result

    def test_ponyat(self, tr):
        result = tr.translate("Я понял задачу.")
        assert "получ" in result
        assert "понима" in result

    def test_uvidet(self, tr):
        result = tr.translate("Я увидел дом.")
        assert "получ" in result
        assert "вид" in result

    def test_polubit(self, tr):
        result = tr.translate("Он полюбил её.")
        assert "получ" in result
        assert "люби" in result

    def test_razljubit(self, tr):
        result = tr.translate("Он разлюбил её.")
        assert "перест" in result
        assert "люби" in result

    def test_zabyt(self, tr):
        result = tr.translate("Я забыл ответ.")
        assert "перест" in result
        assert "зна" in result

    def test_vspomnit(self, tr):
        result = tr.translate("Я вспомнил ответ.")
        assert "получ" in result
        assert "зна" in result

    def test_ne_uznal(self, tr):
        result = tr.translate("Я не узнал ответ.")
        assert "не" in result
        assert "получ" in result
        assert "кон" not in result


# ═══════════════════════════════════════════════
# 5. ФАЗА
# ═══════════════════════════════════════════════

class TestPhase:

    def test_nachat(self, tr):
        result = tr.translate("Я начал читать.")
        assert result == "я нач чита"

    def test_perestat(self, tr):
        result = tr.translate("Я перестал читать.")
        assert "пере" in result
        assert "чита" in result

    def test_prodolzhit(self, tr):
        result = tr.translate("Я продолжил читать.")
        assert "прод" in result
        assert "чита" in result

    def test_phase_with_tense(self, tr):
        result = tr.translate("Он начал работать.")
        assert "нач" in result
        assert "работа" in result


# ═══════════════════════════════════════════════
# 6. МУТАТИВ
# ═══════════════════════════════════════════════

class TestMutative:

    def test_sta_adjective(self, tr):
        result = tr.translate("Город стал тихим.")
        assert result == "город ста тих"

    def test_sta_state(self, tr):
        result = tr.translate("Вода стала холодной.")
        assert result == "вода ста холодн"

    def test_sta_sky(self, tr):
        result = tr.translate("Небо стало тёмным.")
        assert result == "небо ста тёмн"

    def test_stanov_profession(self, tr):
        result = tr.translate("Она стала врачом.")
        assert result == "она станов врач"

    def test_stanov_role(self, tr):
        result = tr.translate("Он стал лидером.")
        assert "станов" in result
        assert "лидер" in result

    def test_sta_past(self, tr):
        result = tr.translate("Он стал грустным.")
        assert "ста" in result
        assert "грустн" in result


# ═══════════════════════════════════════════════
# 7. ОТРИЦАНИЕ
# ═══════════════════════════════════════════════

class TestNegation:

    def test_simple_negation(self, tr):
        assert tr.translate("Я не читаю.") == "я не чита"

    def test_negation_past(self, tr):
        assert tr.translate("Я не читал.") == "я не был чита"

    def test_negation_future(self, tr):
        assert tr.translate("Я не буду читать.") == "я не буд чита"

    def test_negation_perfective(self, tr):
        result = tr.translate("Я не прочитал книгу.")
        assert result == "я не был кон чита книга"

    def test_negation_with_object(self, tr):
        result = tr.translate("Он не видел дом.")
        assert "не" in result
        assert "види" in result
        assert "дом" in result


# ═══════════════════════════════════════════════
# 8. ВОПРОСЫ
# ═══════════════════════════════════════════════

class TestQuestions:

    def test_polar_question(self, tr):
        result = tr.translate("Ты читаешь книгу?")
        assert result == "ли ты чита книга"

    def test_polar_question_past(self, tr):
        result = tr.translate("Он приходил?")
        assert result.startswith("ли ")
        assert "был" in result
        assert "приходи" in result

    def test_wh_question_kto(self, tr):
        result = tr.translate("Кто читает книгу?")
        assert result.startswith("кто")
        assert "ли" not in result
        assert "чита" in result

    def test_wh_question_gde(self, tr):
        result = tr.translate("Где ты живёшь?")
        assert result.startswith("где")
        assert "ли" not in result
        assert "живи" in result

    def test_wh_question_kogda(self, tr):
        result = tr.translate("Когда он придёт?")
        assert result.startswith("когда")
        assert "ли" not in result
        assert "приходи" in result

    def test_wh_question_pochemu(self, tr):
        result = tr.translate("Почему ты не идёшь?")
        assert result.startswith("почему")
        assert "не" in result
        assert "иди" in result

    def test_embedded_polar_question(self, tr):
        result = tr.translate("Я не знаю, придёт ли он.")
        assert "ли" in result

    def test_embedded_wh_question(self, tr):
        result = tr.translate("Я не знаю, где он живёт.")
        assert "где" in result
        assert "ли" not in result


# ═══════════════════════════════════════════════
# 9. ПРЕДЛОГИ И ПОСЕССИВ
# ═══════════════════════════════════════════════

class TestPrepositions:

    def test_possessive_u(self, tr):
        result = tr.translate("Книга брата.")
        assert "книга" in result
        assert "у" in result
        assert "брат" in result

    def test_possessive_moy(self, tr):
        result = tr.translate("Моя книга.")
        assert "книга" in result
        assert "у" in result
        assert "я" in result

    def test_direction_k(self, tr):
        result = tr.translate("Я иду к дому.")
        assert "иди" in result
        assert "к" in result
        assert "дом" in result

    def test_instrument_s(self, tr):
        result = tr.translate("Я пишу ручкой.")
        assert "писа" in result
        assert "с" in result
        assert "ручка" in result

    def test_location_v(self, tr):
        result = tr.translate("Я живу в городе.")
        assert "живи" in result
        assert "в" in result
        assert "город" in result

    def test_location_na(self, tr):
        result = tr.translate("Книга на столе.")
        assert "на" in result
        assert "стол" in result

    def test_source_iz(self, tr):
        result = tr.translate("Он вышел из дома.")
        assert "выйди" in result
        assert "из" in result
        assert "дом" in result

    def test_topic_o(self, tr):
        result = tr.translate("Я говорю о войне.")
        assert "говори" in result
        assert "о" in result
        assert "война" in result

    def test_nested_possession(self, tr):
        result = tr.translate("Дом брата друга.")
        assert result.count("у") == 2


# ═══════════════════════════════════════════════
# 10. ПАССИВ
# ═══════════════════════════════════════════════

class TestPassive:

    def test_passive_with_agent(self, tr):
        result = tr.translate("Дом построен рабочими.")
        assert "дом" in result
        assert "кон" in result
        assert "строи" in result
        assert "би" in result
        assert "рабочий" in result

    def test_passive_without_agent(self, tr):
        result = tr.translate("Дом построен.")
        assert "дом" in result
        assert "кон" in result
        assert "строи" in result

    def test_passive_past(self, tr):
        result = tr.translate("Дом был построен.")
        assert result == "дом был кон строи"


# ═══════════════════════════════════════════════
# 11. ПРИЛАГАТЕЛЬНЫЕ
# ═══════════════════════════════════════════════

class TestAdjectives:

    def test_qualitative_truncation(self, tr):
        result = tr.translate("Большой дом.")
        assert result == "больш дом"

    def test_qualitative_krasivyy(self, tr):
        result = tr.translate("Красивый дом.")
        assert result == "красив дом"

    def test_qualitative_novyy(self, tr):
        result = tr.translate("Новая книга.")
        assert result == "нов книга"

    def test_qualitative_tikhiy(self, tr):
        result = tr.translate("Тихий город.")
        assert result == "тих город"

    def test_relative_preserved(self, tr):
        result = tr.translate("Деревянный стол.")
        assert result == "деревянный стол"

    def test_relative_lesnoy(self, tr):
        result = tr.translate("Лесной дом.")
        assert result == "лесной дом"

    def test_relative_nauchnyy(self, tr):
        result = tr.translate("Научный журнал.")
        assert result == "научный журнал"

    def test_comparative(self, tr):
        result = tr.translate("Более большой дом.")
        assert result == "более больш дом"

    def test_superlative(self, tr):
        result = tr.translate("Самый большой дом.")
        assert result == "самый больш дом"


# ═══════════════════════════════════════════════
# 12. ЧИСЛО
# ═══════════════════════════════════════════════

class TestPlurality:

    def test_plural_adds_mnogo(self, tr):
        result = tr.translate("Люди закрыли окна.")
        assert "много" in result
        assert "человек" in result
        assert "кон" in result

    def test_numeral_no_mnogo(self, tr):
        result = tr.translate("Три человека пришли.")
        assert "три" in result
        assert "человек" in result
        assert "много" not in result

    def test_mnogo_explicit(self, tr):
        result = tr.translate("Много людей пришли.")
        assert "много" in result
        assert "человек" in result

    def test_all(self, tr):
        result = tr.translate("Все люди пришли.")
        assert "все" in result
        assert "человек" in result

    def test_numeral_with_noun(self, tr):
        result = tr.translate("Два дома стоят.")
        assert "два" in result
        assert "дом" in result
        assert "много" not in result


# ═══════════════════════════════════════════════
# 13. МЕСТОИМЕНИЯ
# ═══════════════════════════════════════════════

class TestPronouns:

    @pytest.mark.parametrize(
        "russian,expected",
        [
            ("Я читаю.", "я чита"),
            ("Ты читаешь.", "ты чита"),
            ("Он читает.", "он чита"),
            ("Она читает.", "она чита"),
            ("Мы читаем.", "мы чита"),
            ("Вы читаете.", "вы чита"),
            ("Они читают.", "они чита"),
        ],
    )
    def test_personal_pronouns(self, tr, russian, expected):
        assert tr.translate(russian) == expected

    def test_dative_k(self, tr):
        result = tr.translate("Я дал книгу ему.")
        assert "к" in result
        assert "он" in result

    def test_instrumental_s(self, tr):
        result = tr.translate("Я говорю с ней.")
        assert "с" in result
        assert "она" in result


# ═══════════════════════════════════════════════
# 14. ПРИДАТОЧНЫЕ
# ═══════════════════════════════════════════════

class TestSubordinateClauses:

    def test_chto_clause(self, tr):
        result = tr.translate("Я знаю, что он пришёл.")
        assert "что" in result
        assert "зна" in result
        assert "кон" in result
        assert "приходи" in result

    def test_kotoryy_clause(self, tr):
        result = tr.translate("Человек, который читает книгу.")
        assert "который" in result
        assert "чита" in result

    def test_kogda_clause(self, tr):
        result = tr.translate("Когда пришла зима, город стал тихим.")
        assert "когда" in result
        assert "зима" in result
        assert "ста" in result
        assert "тих" in result

    def test_esli_clause(self, tr):
        result = tr.translate("Если ты придёшь, я буду рад.")
        assert "если" in result
        assert "буд" in result


# ═══════════════════════════════════════════════
# 15. ИМПЕРАТИВ
# ═══════════════════════════════════════════════

class TestImperative:

    def test_imperative_i_final(self, tr):
        assert tr.translate("Иди!") == "иди"

    def test_imperative_a_final(self, tr):
        assert tr.translate("Читай!") == "читай"

    def test_imperative_i_lexeme(self, tr):
        assert tr.translate("Говори!") == "говори"

    def test_imperative_consonant_final(self, tr):
        assert tr.translate("Береги!") == "береги"

    def test_imperative_consonant_final_kraid(self, tr):
        assert tr.translate("Кради!") == "кради"

    def test_imperative_mog(self, tr):
        assert tr.translate("Моги!") == "моги"

    def test_imperative_epenthetic_piti(self, tr):
        assert tr.translate("Пей!") == "пити"

    def test_imperative_a_lexeme(self, tr):
        assert tr.translate("Делай!") == "делай"

    def test_imperative_negative(self, tr):
        assert tr.translate("Не читай!") == "не читай"

    def test_imperative_plural(self, tr):
        assert tr.translate("Читайте!") == "читай вы"

    def test_imperative_plural_i(self, tr):
        assert tr.translate("Говорите!") == "говори вы"

    def test_imperative_third_person(self, tr):
        result = tr.translate("Пусть он идёт!")
        assert result == "да он иди"

    def test_imperative_first_person(self, tr):
        result = tr.translate("Давайте читать!")
        assert result == "да мы чита"


# ═══════════════════════════════════════════════
# 16. МОДАЛЬНОСТЬ
# ═══════════════════════════════════════════════

class TestModality:

    def test_nado(self, tr):
        result = tr.translate("Мне надо идти.")
        assert "надо" in result
        assert "иди" in result

    def test_mozhno(self, tr):
        result = tr.translate("Можно войти?")
        assert "можно" in result
        assert "войди" in result

    def test_nelzya(self, tr):
        result = tr.translate("Нельзя курить.")
        assert "нельзя" in result
        assert "кури" in result


# ═══════════════════════════════════════════════
# 17. ВАЛИДАТОР: ДОПУСТИМЫЕ ПОСЛЕДОВАТЕЛЬНОСТИ
# ═══════════════════════════════════════════════

class TestValidatorValid:

    @pytest.mark.parametrize(
        "sentence",
        [
            "я чита книга",
            "я был чита книга",
            "я буд чита книга",
            "я кон чита книга",
            "я был кон чита книга",
            "я буд кон чита книга",
            "я не чита",
            "я не был чита",
            "я не буд чита",
            "я нач чита",
            "я пере чита",
            "я прод чита",
            "я был нач чита",
            "город ста тих",
            "он станов врач",
            "я получ зна",
            "я получ види",
            "он перест люби",
            "я про чита",
            "я сей чита",
            "я был сей чита",
            "он умыва ся",
            "я не был нач чита",
        ],
    )
    def test_valid_sequences(self, validator, sentence):
        result = validator.validate(sentence)
        assert result.ok, (
            f"Должно быть валидно: '{sentence}'. "
            f"Ошибка: {result.error}"
        )


# ═══════════════════════════════════════════════
# 18. ВАЛИДАТОР: ЗАПРЕЩЁННЫЕ ПОСЛЕДОВАТЕЛЬНОСТИ
# ═══════════════════════════════════════════════

class TestValidatorInvalid:

    @pytest.mark.parametrize(
        "sentence",
        [
            "я кон нач чита",
            "я кон пере чита",
            "я кон прод чита",
            "я нач пере чита",
            "я нач прод чита",
            "я пере прод чита",
            "я про кон чита",
            "я про нач чита",
            "я про пере чита",
            "я про прод чита",
            "я про сей чита",
            "я про ста тих",
            "я сей прод чита",
            "я сей кон чита",
            "я ста кон тих",
            "он ста кон тих",
            "он нач ста тих",
            "я кон ста тих",
        ],
    )
    def test_invalid_sequences(self, validator, sentence):
        result = validator.validate(sentence)
        assert not result.ok, (
            f"Должно быть невалидно: '{sentence}'"
        )

    def test_wrong_order_sey_before_byl(self, validator):
        result = validator.validate("я сей был чита")
        assert not result.ok

    def test_wrong_order_kon_before_ne(self, validator):
        result = validator.validate("я кон не чита")
        assert not result.ok


# ═══════════════════════════════════════════════
# 19. ВАЛИДАТОР: СООБЩЕНИЯ ОБ ОШИБКАХ
# ═══════════════════════════════════════════════

class TestValidatorErrors:

    def test_error_message_for_incompatible(self, validator):
        result = validator.validate("я кон нач чита")
        assert not result.ok
        assert result.error is not None
        assert "кон" in result.error or "нач" in result.error

    def test_error_message_for_order(self, validator):
        result = validator.validate("я сей был чит")
        assert not result.ok
        assert result.error is not None


# ═══════════════════════════════════════════════
# 20. ИМПЕРАТИВНЫЙ АФФИКС
# ═══════════════════════════════════════════════

class TestImperativeAllomorphs:

    @pytest.mark.parametrize(
        "infinitive,imperative",
        [
            ("читать", "читай"),
            ("делать", "делай"),
            ("работать", "работай"),
            ("говорить", "говори"),
            ("идти", "иди"),
            ("любить", "люби"),
            ("беречь", "береги"),
            ("красть", "кради"),
            ("мочь", "моги"),
        ],
    )
    def test_imperative_allomorphs(self, tr, infinitive, imperative):
        assert tr.imperative_of(infinitive) == imperative


# ═══════════════════════════════════════════════
# 21. ЭПЕНТЕЗИС
# ═══════════════════════════════════════════════

class TestEpenthesis:

    @pytest.mark.parametrize(
        "russian,expected",
        [
            ("Пить.", "пити"),
            ("Бить.", "бити"),
            ("Шить.", "шити"),
            ("Мыть.", "мыти"),
            ("Выть.", "выти"),
            ("Дать.", "дати"),
            ("Есть.", "ести"),
        ],
    )
    def test_epenthetic_forms(self, tr, russian, expected):
        assert tr.translate(russian) == expected


# ═══════════════════════════════════════════════
# 22. ВОЗВРАТНОСТЬ
# ═══════════════════════════════════════════════

class TestReflexivity:

    @pytest.mark.parametrize(
        "russian,lexeme",
        [
            ("Он умывается.", "умыва"),
            ("Она смеётся.", "смея"),
            ("Я боюсь.", "боя"),
            ("Мы встречаемся.", "встреча"),
            ("Дверь открывается.", "открыва"),
        ],
    )
    def test_reflexive(self, tr, russian, lexeme):
        result = tr.translate(russian)
        assert lexeme in result
        assert "ся" in result


# ═══════════════════════════════════════════════
# 23. ЭКЗИСТЕНЦИАЛЬНЫЙ ПРЕДИКАТОР
# ═══════════════════════════════════════════════

class TestExistential:

    def test_possession(self, tr):
        result = tr.translate("У меня есть дом.")
        assert result == "у я есть дом"

    def test_existence(self, tr):
        result = tr.translate("В лесу есть волк.")
        assert "в лес" in result
        assert "есть" in result
        assert "волк" in result


# ═══════════════════════════════════════════════
# 24. СВЯЗКА
# ═══════════════════════════════════════════════

class TestCopula:

    def test_present_copula(self, tr):
        assert tr.translate("Я врач.") == "я врач"

    def test_past_copula(self, tr):
        assert tr.translate("Я был врачом.") == "я был врач"

    def test_future_copula(self, tr):
        assert tr.translate("Я буду врачом.") == "я буд врач"


# ═══════════════════════════════════════════════
# 25. УСЛОВИЕ
# ═══════════════════════════════════════════════

class TestConditional:

    def test_basic_conditional(self, tr):
        result = tr.translate("Я бы пошёл.")
        assert "я" in result
        assert "бы" in result
        assert "иди" in result

    def test_conditional_clause(self, tr):
        result = tr.translate("Если я знаю, я бы пришёл.")
        assert "если" in result
        assert "бы" in result


# ═══════════════════════════════════════════════
# 26. ОПРЕДЕЛИТЕЛИ
# ═══════════════════════════════════════════════

class TestDeterminers:

    def test_one(self, tr):
        result = tr.translate("Один человек пришёл.")
        assert result == "один человек кон приходи"

    def test_this(self, tr):
        result = tr.translate("Этот человек сидит.")
        assert "этот" in result
        assert "человек" in result

    def test_that(self, tr):
        result = tr.translate("Тот дом стоит в лесу.")
        assert "тот" in result
        assert "дом" in result
        assert "в" in result
        assert "лес" in result


# ═══════════════════════════════════════════════
# 27. КАНОНИЧЕСКИЕ ГЛАГОЛЬНЫЕ ЛЕКСЕМЫ
# ═══════════════════════════════════════════════

class TestCanonicalVerbs:

    @pytest.mark.parametrize(
        "russian,rusit",
        [
            ("читать", "чита"),
            ("говорить", "говори"),
            ("делать", "дела"),
            ("любить", "люби"),
            ("видеть", "види"),
            ("писать", "писа"),
            ("работать", "работа"),
            ("строить", "строи"),
            ("жить", "живи"),
            ("спать", "спи"),
            ("идти", "иди"),
            ("нести", "неси"),
            ("плести", "плети"),
            ("грести", "греби"),
            ("расти", "расти"),
            ("войти", "войди"),
            ("выйти", "выйди"),
            ("прийти", "приходи"),
            ("уйти", "уходи"),
            ("беречь", "берег"),
            ("мочь", "мог"),
            ("течь", "тег"),
            ("печь", "пег"),
            ("сечь", "сег"),
            ("стричь", "стриг"),
            ("жечь", "жег"),
            ("лечь", "лег"),
            ("красть", "крад"),
            ("пасть", "пад"),
            ("сесть", "сед"),
            ("пить", "пити"),
            ("бить", "бити"),
            ("шить", "шити"),
            ("мыть", "мыти"),
            ("выть", "выти"),
            ("дать", "дати"),
            ("есть", "ести"),
        ],
    )
    def test_canonical_verb_lexeme(self, tr, russian, rusit):
        result = tr.translate(russian + ".")
        assert result == rusit


# ═══════════════════════════════════════════════
# 28. ДИСКУРСИВНЫЕ МАРКЕРЫ
# ═══════════════════════════════════════════════

class TestDiscourseMarkers:

    def test_nu(self, tr):
        result = tr.translate("Ну, я не знаю.")
        assert "ну" in result
        assert "не" in result
        assert "зна" in result

    def test_tipa(self, tr):
        result = tr.translate("Он типа не пришёл.")
        assert "типа" in result
        assert "не" in result

    def test_karoch(self, tr):
        result = tr.translate("Короче, мы идём.")
        assert "кароч" in result
        assert "иди" in result

    def test_prjam(self, tr):
        result = tr.translate("Он прям устал.")
        assert "прям" in result


# ═══════════════════════════════════════════════
# 29. РЕГИСТРЫ
# ═══════════════════════════════════════════════

class TestRegisters:

    def test_formal_strips_markers(self, tr):
        tr.set_register("formal")
        try:
            result = tr.translate("Ну, я не знаю.")
            assert "ну" not in result
            assert "зна" in result
        finally:
            tr.set_register("neutral")

    def test_colloquial_keeps_markers(self, tr):
        tr.set_register("colloquial")
        try:
            result = tr.translate("Ну, я не знаю.")
            assert "ну" in result
        finally:
            tr.set_register("neutral")


# ═══════════════════════════════════════════════
# 30. КРАЕВЫЕ СЛУЧАИ
# ═══════════════════════════════════════════════

class TestEdgeCases:

    def test_empty_string(self, tr):
        assert tr.translate("") == ""

    def test_only_punctuation(self, tr):
        assert tr.translate("!") == ""

    def test_unknown_word_passthrough(self, tr):
        result = tr.translate("Я читаю зоркало.")
        assert "зоркало" in result
        assert "чита" in result

    def test_multiple_sentences(self, tr):
        result = tr.translate("Я читаю. Он спит.")
        assert "чита" in result
        assert "спи" in result

    def test_preserves_numbers(self, tr):
        result = tr.translate("У меня 3 книги.")
        assert "3" in result

    def test_dash_in_text(self, tr):
        result = tr.translate("Я — человек.")
        assert "человек" in result


# ═══════════════════════════════════════════════
# 31. ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# ═══════════════════════════════════════════════

class TestIntegration:

    def test_winter_text(self, tr):
        text = "Когда пришла зима, город стал тихим."
        result = tr.translate(text)
        assert "когда" in result
        assert "зима" in result
        assert "город" in result
        assert "ста" in result
        assert "тих" in result

    def test_people_closed_windows(self, tr):
        text = "Люди закрыли окна."
        result = tr.translate(text)
        assert "много" in result
        assert "человек" in result
        assert "кон" in result
        assert "закры" in result
        assert "окно" in result

    def test_old_man(self, tr):
        text = "Только старик каждый вечер сидел у двери."
        result = tr.translate(text)
        assert "старик" in result
        assert "был" in result
        assert "у" in result
        assert "дверь" in result
        assert "сиде" in result or "сиди" in result

    def test_complex_sentence(self, tr):
        text = "Я знаю, что он никогда больше не увидит этот город."
        result = tr.translate(text)
        assert "зна" in result
        assert "что" in result
        assert "никогда" in result
        assert "получ" in result
        assert "види" in result
        assert "город" in result
        assert "этот" in result

    def test_business_text(self, tr):
        text = "Мы должны обсудить новый проект."
        result = tr.translate(text)
        assert "новый" in result or "нов" in result
        assert "проект" in result

    def test_fantasy_text(self, tr):
        text = "Три космонавта построили новый корабль."
        result = tr.translate(text)
        assert "три" in result
        assert "космонавт" in result
        assert "кон" in result
        assert "строи" in result
        assert "нов" in result
        assert "корабль" in result


# ═══════════════════════════════════════════════
# 32. ПАРАМЕТРИЗОВАННЫЕ ТЕСТЫ
# ═══════════════════════════════════════════════

class TestParametrized:

    @pytest.mark.parametrize(
        "russian,expected",
        [
            ("Я читаю.", "я чита"),
            ("Он спит.", "он спи"),
            ("Она работает.", "она работа"),
            ("Мы живём.", "мы живи"),
            ("Они идут.", "они иди"),
            ("Я люблю.", "я люби"),
            ("Ты видишь.", "ты види"),
            ("Он говорит.", "он говори"),
        ],
    )
    def test_present_tense_verbs(self, tr, russian, expected):
        assert tr.translate(russian) == expected

    @pytest.mark.parametrize(
        "russian,expected_marker",
        [
            ("Я читал.", "был"),
            ("Я буду читать.", "буд"),
            ("Я прочитал.", "кон"),
            ("Я не читаю.", "не"),
        ],
    )
    def test_markers(self, tr, russian, expected_marker):
        result = tr.translate(russian)
        assert expected_marker in result

    @pytest.mark.parametrize(
        "russian,forbidden",
        [
            ("Я читаю.", ["был", "буд", "кон"]),
            ("Он спит.", ["был", "буд", "кон"]),
        ],
    )
    def test_no_false_markers(self, tr, russian, forbidden):
        result = tr.translate(russian)
        for marker in forbidden:
            assert marker not in result

    @pytest.mark.parametrize(
        "adjective,expected",
        [
            ("большой", "больш"),
            ("красивый", "красив"),
            ("новый", "нов"),
            ("старый", "стар"),
            ("тихий", "тих"),
            ("холодный", "холодн"),
            ("темный", "тёмн"),
            ("маленький", "мал"),
            ("быстрый", "быстр"),
        ],
    )
    def test_qualitative_adjectives(self, tr, adjective, expected):
        result = tr.translate(f"{adjective} дом.")
        assert expected in result
        assert adjective not in result

    @pytest.mark.parametrize(
        "sentence",
        [
            "я чита книга",
            "я был чита книга",
            "я буд чита книга",
            "я кон чита книга",
            "я был кон чита книга",
            "я буд кон чита книга",
            "я не чита",
            "я нач чита",
            "я пере чита",
            "я прод чита",
            "город ста тих",
            "он станов врач",
            "я про чита",
            "я сей чита",
            "я был сей чита",
            "я не был чита",
            "я не буд чита",
            "он умыва ся",
        ],
    )
    def test_valid_sequences(self, validator, sentence):
        result = validator.validate(sentence)
        assert result.ok, (
            f"Должно быть валидно: '{sentence}'. "
            f"Ошибка: {result.error}"
        )

    @pytest.mark.parametrize(
        "sentence",
        [
            "я кон нач чита",
            "я кон пере чита",
            "я кон прод чита",
            "я нач пере чита",
            "я нач прод чита",
            "я пере прод чита",
            "я про кон чита",
            "я про нач чита",
            "я про пере чита",
            "я про прод чита",
            "я про сей чита",
            "я сей прод чита",
            "я сей кон чита",
            "я кон ста тих",
            "я нач ста тих",
            "я ста кон тих",
            "я про ста тих",
        ],
    )
    def test_invalid_sequences(self, validator, sentence):
        result = validator.validate(sentence)
        assert not result.ok


# ═══════════════════════════════════════════════
# 33. СОВМЕСТИМОСТЬ ТАМ / АСПЕКТА / ФАЗЫ
# ═══════════════════════════════════════════════

class TestParticleCompatibility:

    @pytest.mark.parametrize(
        "sentence",
        [
            "я чита",
            "я был чита",
            "я буд чита",
            "я был сей чита",
            "я буд сей чита",
            "я был кон чита",
            "я буд кон чита",
            "я был нач чита",
            "я буд нач чита",
            "я не был чита",
            "я не буд чита",
        ],
    )
    def test_allowed_combinations(self, validator, sentence):
        assert validator.validate(sentence).ok

    @pytest.mark.parametrize(
        "sentence",
        [
            "я кон нач чита",
            "я кон пере чита",
            "я кон прод чита",
            "я нач пере чита",
            "я нач прод чита",
            "я пере прод чита",
            "я про кон чита",
            "я про нач чита",
            "я про пере чита",
            "я про прод чита",
            "я про сей чита",
            "я сей прод чита",
            "я сей кон чита",
            "я ста кон тих",
            "я ста нач тих",
        ],
    )
    def test_forbidden_combinations(self, validator, sentence):
        assert not validator.validate(sentence).ok


# ═══════════════════════════════════════════════
# 34. ПРОИЗВОДИТЕЛЬНОСТЬ
# ═══════════════════════════════════════════════

class TestPerformance:

    def test_single_sentence_under_100ms(self, tr):
        start = time.perf_counter()
        tr.translate("Я читаю книгу.")
        elapsed = time.perf_counter() - start
        assert elapsed < 0.1, f"Слишком медленно: {elapsed:.3f}s"

    def test_hundred_sentences_under_10s(self, tr):
        sentences = ["Я читаю книгу."] * 100
        start = time.perf_counter()
        for sentence in sentences:
            tr.translate(sentence)
        elapsed = time.perf_counter() - start
        assert elapsed < 10.0, f"Слишком медленно: {elapsed:.3f}s"
