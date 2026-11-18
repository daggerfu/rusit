"""
РУСИТ 5.3.1 — тесты: test_rusit_misc.
Запуск: pytest tests/test_rusit_misc.py -v
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

    def test_intensifier_hyphen_no_crash(self, tr):
        result = tr.translate("Там живет много-много негров.")
        assert "негр" in result

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
# 26. ПРОИЗВОДИТЕЛЬНОСТЬ
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