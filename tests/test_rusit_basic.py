"""
РУСИТ 5.3.1 — тесты: test_rusit_basic.
Запуск: pytest tests/test_rusit_basic.py -v
"""

import pytest
from rusit import RusitTranslator, RusitValidator


# ═══════════════════════════════════════════════
# ФИКСТУРЫ
# ═══════════════════════════════════════════════

@pytest.fixture
def tr():
    """Транслятор."""
    return RusitTranslator()


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
# 1Б. НЕИЗМЕНЯЕМЫЕ НАРЕЧНЫЕ ЛЕКСЕМЫ
# ═══════════════════════════════════════════════

class TestAdverbs:
    """Наречия из словаря: без суффиксов и согласований, как есть."""

    @pytest.mark.parametrize("adverb", [
        "часто", "редко", "иногда",
        "почти", "полностью",
        "вместе", "отдельно",
        "хорошо", "плохо",
        "быстро", "медленно",
    ])
    def test_adverb_preserved_after_verb(self, tr, adverb):
        # Позиция после глагола — основная для адвербиальных
        # модификаторов: лексема проходит без изменений.
        result = tr.translate(f"Он читает {adverb}.")
        assert adverb in result
        assert "чита" in result

    def test_adverb_no_suffixes_or_agreement(self, tr):
        # Никаких наречных суффиксов и согласований:
        # «медленно» остаётся «медленно» в любом контексте.
        assert tr.translate("Она медленно читала.") == \
            "она медленно был чита"

    def test_adverb_lexicon_has_semantics(self, tr):
        # Значение наречия — семантическая метка в лексиконе.
        assert tr.adverbs["часто"] == "частота"
        assert tr.adverbs["полностью"] == "степень"
        assert tr.adverbs["быстро"] == "скорость"



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

    def test_tam_not_repeated_in_coordinated_clauses(self, tr, validator):
        result = tr.translate(
            "Он прочитал книгу и написал статью."
        )
        assert result == "он кон чита книга и пиши статья"
        assert validator.validate(result).ok

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
        assert result == "я кон чита книга"

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
        assert tr.translate("Ты меня любишь?") == "ли ты люби я?"

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


