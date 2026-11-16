"""
РУСИТ 5.0 (со спецификацией 5.3.1) — полный набор тестов.
Запуск: pytest tests/test_rusit.py -v
"""

import pytest
from rusit import RusitTranslator, RusitValidator


# ═══════════════════════════════════════════════
# ФИКСТУРЫ
# ═══════════════════════════════════════════════

@pytest.fixture
def tr():
    """Транслятор без spaCy (детерминированный режим)."""
    return RusitTranslator(use_spacy=False)


@pytest.fixture
def tr_spacy():
    """Транслятор со spaCy (SVO-перестройка)."""
    return RusitTranslator(use_spacy=True)


@pytest.fixture
def validator():
    """Валидатор грамматики РУСИТ."""
    return RusitValidator()


# ═══════════════════════════════════════════════
# 1. БАЗОВЫЙ SVO
# ═══════════════════════════════════════════════

class TestBasicSVO:
    """Простые предложения: подлежащее + сказуемое + дополнение."""

    def test_simple_present(self, tr):
        assert tr.translate("Я читаю книгу.") == "я чита книга"

    def test_simple_present_verb_only(self, tr):
        assert tr.translate("Он спит.") == "он спи"

    def test_simple_with_adverb(self, tr):
        result = tr.translate("Я быстро читаю книгу.")
        assert "быстро" in result
        assert "чита" in result
        assert "книга" in result

    def test_subject_verb(self, tr):
        assert tr.translate("Она работает.") == "она работа"

    def test_verb_with_prepositional_object(self, tr):
        result = tr.translate("Я живу в городе.")
        assert "жив" in result
        assert "в" in result
        assert "город" in result


# ═══════════════════════════════════════════════
# 2. ВРЕМЁНА
# ═══════════════════════════════════════════════

class TestTense:
    """Прошедшее (был), будущее (буд), настоящее (∅)."""

    def test_present_no_marker(self, tr):
        result = tr.translate("Я читаю.")
        assert "был" not in result
        assert "буд" not in result
        assert "чит" in result

    def test_past(self, tr):
        result = tr.translate("Я читал книгу.")
        assert result == "я был чита книга"

    def test_past_feminine(self, tr):
        result = tr.translate("Она читала книгу.")
        assert "был" in result
        assert "чит" in result

    def test_past_plural(self, tr):
        result = tr.translate("Они читали книгу.")
        assert "был" in result

    def test_future(self, tr):
        result = tr.translate("Я буду читать книгу.")
        assert result == "я буд чита книга"

    def test_future_simple(self, tr):
        result = tr.translate("Мы будем строить дом.")
        assert "буд" in result
        assert "стро" in result
        assert "дом" in result

    @pytest.mark.parametrize("sentence,expected_tense", [
        ("Я читаю.", "pres"),
        ("Я читал.", "past"),
        ("Я буду читать.", "futr"),
    ])
    def test_tense_markers(self, tr, sentence, expected_tense):
        result = tr.translate(sentence)
        if expected_tense == "pres":
            assert "был" not in result and "буд" not in result
        elif expected_tense == "past":
            assert "был" in result
        elif expected_tense == "futr":
            assert "буд" in result


# ═══════════════════════════════════════════════
# 3. ВИД (СОВЕРШЁННЫЙ / НЕСОВЕРШЁННЫЙ)
# ═══════════════════════════════════════════════

class TestAspect:
    """кон для телических, получ/перест для ателических."""

    def test_perfective_telic(self, tr):
        result = tr.translate("Я прочитал книгу.")
        assert "кон" in result
        assert "чит" in result

    def test_imperfective_no_marker(self, tr):
        result = tr.translate("Я читал книгу.")
        assert "кон" not in result

    def test_past_perfective(self, tr):
        result = tr.translate("Я прочитал книгу.")
        assert result == "я был кон чита книга"

    def test_future_perfective(self, tr):
        result = tr.translate("Я прочитаю книгу.")
        assert result == "я буд кон чита книга"

    def test_perfective_close(self, tr):
        result = tr.translate("Они закрыли окна.")
        assert "кон" in result
        assert "закры" in result

    def test_perfective_build(self, tr):
        result = tr.translate("Мы построили дом.")
        assert "кон" in result
        assert "стро" in result

    def test_perfective_write(self, tr):
        result = tr.translate("Он написал письмо.")
        assert "кон" in result
        assert "пис" in result


# ═══════════════════════════════════════════════
# 4. АТЕЛИЧЕСКИЕ ГЛАГОЛЫ (получ / перест)
# ═══════════════════════════════════════════════

class TestAtelicVerbs:
    """получ для получения результата, перест для утраты."""

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
        assert "люб" in result

    def test_razljubit(self, tr):
        result = tr.translate("Он разлюбил её.")
        assert "перест" in result
        assert "люб" in result

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


# ═══════════════════════════════════════════════
# 5. ФАЗА (нач / пере / прод)
# ═══════════════════════════════════════════════

class TestPhase:
    """Маркеры начала, прекращения, продолжения."""

    def test_nachat(self, tr):
        result = tr.translate("Я начал читать.")
        assert "нач" in result
        assert "чит" in result

    def test_perestat(self, tr):
        result = tr.translate("Я перестал читать.")
        assert "пере" in result or "перест" in result

    def test_prodolzhit(self, tr):
        result = tr.translate("Я продолжил читать.")
        assert "прод" in result

    def test_phase_with_tense(self, tr):
        result = tr.translate("Он начал работать.")
        assert "нач" in result
        assert "работ" in result


# ═══════════════════════════════════════════════
# 6. МУТАТИВ (ста)
# ═══════════════════════════════════════════════

class TestMutative:
    """Единственная частица мутатива — ста (§7.6)."""

    def test_sta_adjective(self, tr):
        result = tr.translate("Город стал тихим.")
        assert "ста" in result
        assert "тихий" in result

    def test_sta_state(self, tr):
        result = tr.translate("Вода стала холодной.")
        assert "ста" in result
        assert "холодный" in result

    def test_sta_sky(self, tr):
        result = tr.translate("Небо стало тёмным.")
        assert "ста" in result
        assert "темный" in result  # ё нормализуется в е

    def test_sta_profession(self, tr):
        result = tr.translate("Она стала врачом.")
        assert "ста" in result
        assert "станов" not in result
        assert "врач" in result

    def test_sta_role(self, tr):
        result = tr.translate("Он стал лидером.")
        assert "ста" in result
        assert "станов" not in result

    def test_sta_past(self, tr):
        result = tr.translate("Он стал грустным.")
        assert "ста" in result
        assert "грустный" in result

    def test_sta_perfective(self, tr):
        result = tr.translate("Город стал тихим.")
        assert "кон ста" in result
        assert "тихий" in result

    def test_sta_future_perfective(self, tr):
        result = tr.translate("Она станет врачом.")
        assert "буд кон ста" in result
        assert "врач" in result

    def test_sta_imperfective(self, tr):
        result = tr.translate("Город становится тихим.")
        assert "ста" in result
        assert "тихий" in result
        assert "станови" not in result
        assert "ся" not in result

    def test_sta_past_imperfective(self, tr):
        result = tr.translate("Город становился тихим.")
        assert "был ста" in result
        assert "тихий" in result


# ═══════════════════════════════════════════════
# 7. ОТРИЦАНИЕ
# ═══════════════════════════════════════════════

class TestNegation:
    """Частица не перед глагольной группой."""

    def test_simple_negation(self, tr):
        result = tr.translate("Я не читаю.")
        assert result == "я не чита"

    def test_negation_past(self, tr):
        result = tr.translate("Я не читал.")
        assert "не" in result
        assert "был" in result

    def test_negation_future(self, tr):
        result = tr.translate("Я не буду читать.")
        assert "не" in result
        assert "буд" in result

    def test_negation_perfective(self, tr):
        result = tr.translate("Я не прочитал книгу.")
        assert "не" in result
        assert "кон" in result

    def test_negation_with_object(self, tr):
        result = tr.translate("Он не видел дом.")
        assert "не" in result
        assert "вид" in result
        assert "дом" in result


# ═══════════════════════════════════════════════
# 8. ВОПРОСЫ
# ═══════════════════════════════════════════════

class TestQuestions:
    """Полярные (ли) и WH-вопросы."""

    def test_polar_question(self, tr):
        result = tr.translate("Ты читаешь книгу?")
        assert result.startswith("ли")
        assert "чит" in result
        assert "книга" in result

    def test_polar_question_past(self, tr):
        result = tr.translate("Он приходил?")
        assert result.startswith("ли")
        assert "был" in result

    def test_polar_question_punctuation(self, tr):
        assert tr.translate("Ты меня любишь?") == "ли ты я люби?"

    def test_wh_question_punctuation(self, tr):
        result = tr.translate("Кто читает книгу?")
        assert result.endswith("?")

    def test_wh_question_kto(self, tr):
        result = tr.translate("Кто читает книгу?")
        assert "кто" in result
        assert "ли" not in result

    def test_wh_question_gde(self, tr):
        result = tr.translate("Где ты живёшь?")
        assert "где" in result
        assert "ли" not in result

    def test_wh_question_kogda(self, tr):
        result = tr.translate("Когда он придёт?")
        assert "когда" in result
        assert "ли" not in result

    def test_wh_question_pochemu(self, tr):
        result = tr.translate("Почему ты не идёшь?")
        assert "почему" in result
        assert "не" in result

    def test_embedded_polar_question(self, tr):
        result = tr.translate("Я не знаю, придёт ли он.")
        assert "ли" in result

    def test_embedded_wh_question(self, tr):
        result = tr.translate("Я не знаю, где он живёт.")
        assert "где" in result
        # ли не должно быть для WH-вопроса
        assert result.count("ли") == 0 or "ли" not in result.split("где")[0]


# ═══════════════════════════════════════════════
# 9. ПОСЕССИВ И ПРЕДЛОГИ
# ═══════════════════════════════════════════════

class TestPrepositions:
    """Предлоги: у, от, к, с, в, на, из, о, би."""

    def test_possessive_u(self, tr):
        result = tr.translate("Книга брата.")
        assert "книга" in result
        assert "у" in result
        assert "брат" in result

    def test_possessive_moy(self, tr):
        result = tr.translate("Моя книга.")
        assert "у" in result
        assert "я" in result

    def test_direction_k(self, tr):
        result = tr.translate("Я иду к дому.")
        assert "к" in result
        assert "дом" in result

    def test_instrument_s(self, tr):
        result = tr.translate("Я пишу ручкой.")
        assert "с" in result
        assert "ручка" in result

    def test_location_v(self, tr):
        result = tr.translate("Я живу в городе.")
        assert "в" in result
        assert "город" in result

    def test_location_na(self, tr):
        result = tr.translate("Книга на столе.")
        assert "на" in result
        assert "стол" in result

    def test_source_iz(self, tr):
        result = tr.translate("Он вышел из дома.")
        assert "из" in result
        assert "дом" in result

    def test_topic_o(self, tr):
        result = tr.translate("Я говорю о войне.")
        assert "о" in result
        assert "война" in result

    def test_nested_possession(self, tr):
        result = tr.translate("Дом брата друга.")
        assert result.split().count("у") == 2


# ═══════════════════════════════════════════════
# 10. ПАССИВ
# ═══════════════════════════════════════════════

class TestPassive:
    """Пассивная конструкция с би."""

    def test_passive_with_agent(self, tr):
        result = tr.translate("Дом построен рабочими.")
        assert "стро" in result
        assert "би" in result
        assert "рабочий" in result or "рабоч" in result

    def test_passive_without_agent(self, tr):
        result = tr.translate("Дом построен.")
        assert "стро" in result

    def test_passive_past(self, tr):
        result = tr.translate("Дом был построен.")
        assert "был" in result
        assert "стро" in result


# ═══════════════════════════════════════════════
# 11. ПРИЛАГАТЕЛЬНЫЕ
# ═══════════════════════════════════════════════

class TestAdjectives:
    """Один тип: качественные и относительные — полная форма (§5.2)."""

    def test_qualitative_full_form(self, tr):
        result = tr.translate("Большой дом.")
        assert "большой" in result
        assert "дом" in result

    def test_qualitative_krasivyy(self, tr):
        result = tr.translate("Красивый дом.")
        assert "красивый" in result

    def test_qualitative_novyy(self, tr):
        result = tr.translate("Новая книга.")
        assert "новый" in result
        assert "новая" not in result

    def test_qualitative_tikhiy(self, tr):
        result = tr.translate("Тихий город.")
        assert "тихий" in result

    def test_inflected_form_normalized(self, tr):
        result = tr.translate("Большого дома нет.")
        assert "большой" in result
        assert "большого" not in result

    def test_relative_preserved(self, tr):
        result = tr.translate("Деревянный стол.")
        assert "деревянный" in result

    def test_relative_lesnoy(self, tr):
        result = tr.translate("Лесной дом.")
        assert "лесной" in result

    def test_relative_nauchnyy(self, tr):
        result = tr.translate("Научный журнал.")
        assert "научный" in result

    def test_comparative(self, tr):
        result = tr.translate("Более большой дом.")
        assert "более" in result
        assert "большой" in result

    def test_superlative(self, tr):
        result = tr.translate("Самый большой дом.")
        assert "самый" in result
        assert "большой" in result


# ═══════════════════════════════════════════════
# 12. МНОЖЕСТВЕННОЕ ЧИСЛО
# ═══════════════════════════════════════════════

class TestPlurality:
    """много для множественного, числительные без много."""

    def test_plural_adds_mnogo(self, tr):
        result = tr.translate("Люди закрыли окна.")
        assert "много" in result
        assert "человек" in result

    def test_numeral_no_mnogo(self, tr):
        result = tr.translate("Три человека пришли.")
        assert "три" in result
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
    """Местоимения неизменяемы."""

    def test_ya(self, tr):
        assert tr.translate("Я читаю.") == "я чита"

    def test_ty(self, tr):
        assert tr.translate("Ты читаешь.") == "ты чита"

    def test_on(self, tr):
        assert tr.translate("Он читает.") == "он чита"

    def test_ona(self, tr):
        assert tr.translate("Она читает.") == "она чита"

    def test_my(self, tr):
        assert tr.translate("Мы читаем.") == "мы чита"

    def test_vy(self, tr):
        assert tr.translate("Вы читаете.") == "вы чита"

    def test_oni(self, tr):
        assert tr.translate("Они читают.") == "они чита"

    def test_dative_k(self, tr):
        result = tr.translate("Я дал книгу ему.")
        assert "к" in result
        assert "он" in result

    def test_instrumental_s(self, tr):
        result = tr.translate("Я говорю с ней.")
        assert "с" in result
        assert "она" in result


# ═══════════════════════════════════════════════
# 14. ПРИДАТОЧНЫЕ ПРЕДЛОЖЕНИЯ
# ═══════════════════════════════════════════════

class TestSubordinateClauses:
    """Союзы что, который, когда, если."""

    def test_chto_clause(self, tr):
        result = tr.translate("Я знаю, что он пришёл.")
        assert "что" in result
        assert "зна" in result
        assert "кон" in result
        assert "приход" in result

    def test_kotoryy_clause(self, tr):
        result = tr.translate("Человек, который читает книгу.")
        assert "который" in result
        assert "чит" in result

    def test_kogda_clause(self, tr):
        result = tr.translate("Когда пришла зима, город стал тихим.")
        assert "когда" in result
        assert "зима" in result
        assert "ста" in result
        assert "тихий" in result

    def test_esli_clause(self, tr):
        result = tr.translate("Если ты придёшь, я буду рад.")
        assert "если" in result


# ═══════════════════════════════════════════════
# 15. ИМПЕРАТИВ
# ═══════════════════════════════════════════════

class TestImperative:
    """Императив — неизменяемая лексема без суффиксов (§8)."""

    def test_imperative_i_final(self, tr):
        result = tr.translate("Иди!")
        assert "иди" in result

    def test_imperative_exclamation(self, tr):
        assert tr.translate("Иди!") == "иди!"

    def test_imperative_lexeme(self, tr):
        assert tr.translate("Читай!") == "чита!"
        assert tr.imperative_of("читать") == "чита"

    def test_imperative_negative(self, tr):
        assert tr.translate("Не читай!") == "не чита!"

    def test_imperative_plural(self, tr):
        assert tr.translate("Читайте!") == "вы чита!"

    def test_imperative_third_person(self, tr):
        result = tr.translate("Пусть он идёт!")
        assert "да" in result
        assert "иди" in result


# ═══════════════════════════════════════════════
# 16. МОДАЛЬНОСТЬ
# ═══════════════════════════════════════════════

class TestModality:
    """надо, можно, нельзя."""

    def test_nado(self, tr):
        result = tr.translate("Мне надо идти.")
        assert "надо" in result

    def test_mozhno(self, tr):
        result = tr.translate("Можно войти?")
        assert "можно" in result

    def test_nelzya(self, tr):
        result = tr.translate("Нельзя курить.")
        assert "нельзя" in result


# ═══════════════════════════════════════════════
# 17. ВАЛИДАТОР: ДОПУСТИМЫЕ ПОСЛЕДОВАТЕЛЬНОСТИ
# ═══════════════════════════════════════════════

class TestValidatorValid:
    """Валидатор принимает корректные конструкции."""

    def test_simple_verb(self, validator):
        assert validator.validate("я чита книга").ok

    def test_past_tense(self, validator):
        assert validator.validate("я был чита книга").ok

    def test_future_tense(self, validator):
        assert validator.validate("я буд чита книга").ok

    def test_perfective(self, validator):
        assert validator.validate("я кон чита книга").ok

    def test_past_perfective(self, validator):
        assert validator.validate("я был кон чита книга").ok

    def test_future_perfective(self, validator):
        assert validator.validate("я буд кон чита книга").ok

    def test_negation(self, validator):
        assert validator.validate("я не чита").ok

    def test_negation_past(self, validator):
        assert validator.validate("я не был чита").ok

    def test_inchoative(self, validator):
        assert validator.validate("я нач чита").ok

    def test_cessative(self, validator):
        assert validator.validate("я пере чита").ok

    def test_continuative(self, validator):
        assert validator.validate("я прод чита").ok

    def test_past_inchoative(self, validator):
        assert validator.validate("я был нач чита").ok

    def test_mutative(self, validator):
        assert validator.validate("город ста тихий").ok

    def test_mutative_noun(self, validator):
        assert validator.validate("он ста врач").ok

    def test_perfective_mutative(self, validator):
        assert validator.validate("он кон ста тихий").ok

    def test_inchoative_mutative(self, validator):
        assert validator.validate("он нач ста тихий").ok

    def test_acquisition_mutative(self, validator):
        assert validator.validate("он получ ста врач").ok

    def test_loss_mutative(self, validator):
        assert validator.validate("он перест ста врач").ok

    def test_experiential(self, validator):
        assert validator.validate("я про чита книга").ok

    def test_progressive(self, validator):
        assert validator.validate("я сей чита").ok

    def test_past_progressive(self, validator):
        assert validator.validate("я был сей чита").ok

    def test_reflexive(self, validator):
        assert validator.validate("он умыва ся").ok

    def test_full_valid_chain(self, validator):
        assert validator.validate("я не был нач чита").ok


# ═══════════════════════════════════════════════
# 18. ВАЛИДАТОР: ЗАПРЕЩЁННЫЕ ПОСЛЕДОВАТЕЛЬНОСТИ
# ═══════════════════════════════════════════════

class TestValidatorInvalid:
    """Валидатор отвергает некорректные конструкции."""

    def test_double_boundary_kon_nach(self, validator):
        result = validator.validate("я кон нач чита")
        assert not result.ok

    def test_double_boundary_kon_pere(self, validator):
        result = validator.validate("я кон пере чита")
        assert not result.ok

    def test_double_boundary_kon_prod(self, validator):
        result = validator.validate("я кон прод чита")
        assert not result.ok

    def test_double_boundary_nach_pere(self, validator):
        result = validator.validate("я нач пере чита")
        assert not result.ok

    def test_double_boundary_nach_prod(self, validator):
        result = validator.validate("я нач прод чита")
        assert not result.ok

    def test_double_boundary_pere_prod(self, validator):
        result = validator.validate("я пере прод чита")
        assert not result.ok

    def test_double_boundary_kon_poluch(self, validator):
        result = validator.validate("я кон получ зна")
        assert not result.ok

    def test_double_boundary_poluch_perest(self, validator):
        result = validator.validate("я получ перест зна")
        assert not result.ok

    def test_pro_with_kon(self, validator):
        result = validator.validate("я про кон чита")
        assert not result.ok

    def test_pro_with_poluch(self, validator):
        result = validator.validate("я про получ зна")
        assert not result.ok

    def test_pro_with_perest(self, validator):
        result = validator.validate("я про перест люби")
        assert not result.ok

    def test_pro_with_sey(self, validator):
        result = validator.validate("я про сей чита")
        assert not result.ok

    def test_pro_with_sta(self, validator):
        result = validator.validate("я про ста тихий")
        assert not result.ok

    def test_sey_with_prod(self, validator):
        result = validator.validate("я сей прод чита")
        assert not result.ok

    def test_sey_with_kon(self, validator):
        result = validator.validate("я сей кон чита")
        assert not result.ok

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
    """Валидатор возвращает понятные сообщения."""

    def test_error_message_for_incompatible(self, validator):
        result = validator.validate("я кон нач чита")
        assert not result.ok
        assert result.error is not None
        assert "кон" in result.error or "нач" in result.error

    def test_error_message_for_order(self, validator):
        result = validator.validate("я сей был чита")
        assert not result.ok
        assert result.error is not None


# ═══════════════════════════════════════════════
# 20. КРАЕВЫЕ СЛУЧАИ
# ═══════════════════════════════════════════════

class TestEdgeCases:
    """Пустой ввод, пунктуация, неизвестные слова."""

    def test_empty_string(self, tr):
        assert tr.translate("") == ""

    def test_only_punctuation(self, tr):
        assert tr.translate("!") == ""

    def test_unknown_word_passthrough(self, tr):
        result = tr.translate("Я читаю зоркало.")
        assert "зоркало" in result  # неизвестное слово проходит как есть

    def test_multiple_sentences(self, tr):
        result = tr.translate("Я читаю. Он спит.")
        assert "чит" in result
        assert "сп" in result

    def test_preserves_numbers(self, tr):
        result = tr.translate("У меня 3 книги.")
        assert "3" in result

    def test_preserve_punctuation(self, tr):
        assert tr.translate(
            "Я читаю книгу, а он спит.", preserve_punctuation=True
        ) == "я чита книга, а он спи."

    def test_drop_punctuation_by_default(self, tr):
        assert tr.translate("Я читаю книгу.") == "я чита книга"

    def test_dash_in_text(self, tr):
        result = tr.translate("Я — человек.")
        assert "человек" in result


# ═══════════════════════════════════════════════
# 21. ПОЛНЫЕ ТЕКСТЫ (ИНТЕГРАЦИОННЫЕ)
# ═══════════════════════════════════════════════

class TestIntegration:
    """Полные абзацы и сложные конструкции."""

    def test_winter_text(self, tr):
        text = "Когда пришла зима, город стал тихим."
        result = tr.translate(text)
        assert "когда" in result
        assert "зима" in result
        assert "кон" in result or "приход" in result
        assert "город" in result
        assert "ста" in result
        assert "тихий" in result

    def test_people_closed_windows(self, tr):
        text = "Люди закрыли окна."
        result = tr.translate(text)
        assert "много" in result or "человек" in result
        assert "кон" in result
        assert "закры" in result
        assert "окно" in result

    def test_old_man(self, tr):
        text = "Только старик каждый вечер сидел у двери."
        result = tr.translate(text)
        assert "старик" in result
        assert "был" in result
        assert "сид" in result
        assert "у" in result
        assert "дверь" in result

    def test_complex_sentence(self, tr):
        text = "Я знаю, что он никогда больше не увидит этот город."
        result = tr.translate(text)
        assert "зна" in result
        assert "что" in result
        assert "никогда" in result
        assert "получ" in result
        assert "вид" in result
        assert "город" in result

    def test_fantasy_text(self, tr):
        text = "Три космонавта прилетели на новую планету."
        result = tr.translate(text)
        assert "три" in result
        assert "кон" in result
        assert "приход" in result or "прилет" in result
        assert "новый" in result
        assert "планета" in result


# ═══════════════════════════════════════════════
# 22. ДИСКУРСИВНЫЕ МАРКЕРЫ
# ═══════════════════════════════════════════════

class TestDiscourseMarkers:
    """Разговорные маркеры: прям, типа, кароч, ну."""

    def test_nu_passthrough(self, tr):
        result = tr.translate("Ну, я не знаю.")
        assert "ну" in result
        assert "не" in result

    def test_tipa_passthrough(self, tr):
        result = tr.translate("Он типа не пришёл.")
        assert "типа" in result

    def test_karoch_passthrough(self, tr):
        result = tr.translate("Короче, мы идём.")
        assert "кароч" in result

    def test_prjam_passthrough(self, tr):
        result = tr.translate("Он прям устал.")
        assert "прям" in result


# ═══════════════════════════════════════════════
# 23. РЕГИСТРЫ
# ═══════════════════════════════════════════════

class TestRegisters:
    """Формальный и разговорный режимы."""

    def test_formal_strips_markers(self, tr):
        tr.set_register("formal")
        result = tr.translate("Ну, я не знаю.")
        assert "ну" not in result
        tr.set_register("neutral")

    def test_colloquial_keeps_markers(self, tr):
        tr.set_register("colloquial")
        result = tr.translate("Ну, я не знаю.")
        assert "ну" in result
        tr.set_register("neutral")


# ═══════════════════════════════════════════════
# 24. ПАРАМЕТРИЗОВАННЫЕ ТЕСТЫ
# ═══════════════════════════════════════════════

class TestParametrized:
    """Массовые проверки через parametrize."""

    @pytest.mark.parametrize("russian,expected_contains", [
        ("Я читаю.", ["чит"]),
        ("Он спит.", ["сп"]),
        ("Она работает.", ["работ"]),
        ("Мы живём.", ["жив"]),
        ("Они идут.", ["ид"]),
        ("Я люблю.", ["люб"]),
        ("Ты видишь.", ["вид"]),
        ("Он говорит.", ["говор"]),
    ])
    def test_present_tense_verbs(self, tr, russian, expected_contains):
        result = tr.translate(russian)
        for word in expected_contains:
            assert word in result, f"Ожидалось '{word}' в '{result}'"

    @pytest.mark.parametrize("russian,expected_marker", [
        ("Я читал.", "был"),
        ("Я буду читать.", "буд"),
        ("Я прочитал.", "кон"),
        ("Я не читаю.", "не"),
    ])
    def test_markers(self, tr, russian, expected_marker):
        result = tr.translate(russian)
        assert expected_marker in result

    @pytest.mark.parametrize("russian,forbidden", [
        ("Я читаю.", ["был", "буд", "кон"]),
        ("Он спит.", ["был", "буд", "кон"]),
    ])
    def test_no_false_markers(self, tr, russian, forbidden):
        result = tr.translate(russian)
        for marker in forbidden:
            assert marker not in result, f"Не должно быть '{marker}' в '{result}'"

    @pytest.mark.parametrize("adjective,noun", [
        ("большой", "дом"),
        ("красивый", "дом"),
        ("новый", "дом"),
        ("старый", "дом"),
        ("тихий", "город"),
        ("холодный", "ветер"),
    ])
    def test_qualitative_adjectives_full_form(self, tr, adjective, noun):
        result = tr.translate(f"{adjective.capitalize()} {noun}.")
        assert adjective in result, f"'{adjective}' должно быть в '{result}'"

    @pytest.mark.parametrize("sentence", [
        "я был чита книга",
        "я буд чита книга",
        "я кон чита книга",
        "я не чита",
        "я нач чита",
        "я пере чита",
        "я прод чита",
        "город ста тихий",
        "он ста врач",
        "он кон ста тихий",
        "он нач ста тихий",
        "он получ ста врач",
        "он перест ста врач",
        "я про чита книга",
        "я сей чита",
        "я был кон чита книга",
        "я буд кон чита книга",
        "я не был чита",
        "я не буд чита",
    ])
    def test_valid_sequences(self, validator, sentence):
        result = validator.validate(sentence)
        assert result.ok, f"Должно быть валидно: '{sentence}'. Ошибка: {result.error}"

    @pytest.mark.parametrize("sentence", [
        "я кон нач чита",
        "я кон пере чита",
        "я кон прод чита",
        "я нач пере чита",
        "я нач прод чита",
        "я пере прод чита",
        "я про кон чита",
        "я про получ зна",
        "я про перест люби",
        "я про сей чита",
        "я сей прод чита",
        "я сей кон чита",
        "я про ста тихий",
    ])
    def test_invalid_sequences(self, validator, sentence):
        result = validator.validate(sentence)
        assert not result.ok, f"Должно быть невалидно: '{sentence}'"


# ═══════════════════════════════════════════════
# 25. ПРОИЗВОДИТЕЛЬНОСТЬ
# ═══════════════════════════════════════════════

class TestPerformance:
    """Базовые проверки скорости."""

    def test_single_sentence_under_100ms(self, tr):
        import time
        start = time.time()
        tr.translate("Я читаю книгу.")
        elapsed = time.time() - start
        assert elapsed < 0.1, f"Слишком медленно: {elapsed:.3f}s"

    def test_hundred_sentences_under_10s(self, tr):
        import time
        sentences = ["Я читаю книгу."] * 100
        start = time.time()
        for s in sentences:
            tr.translate(s)
        elapsed = time.time() - start
        assert elapsed < 10.0, f"Слишком медленно: {elapsed:.3f}s"