"""
РУСИТ 5.3.1 — тесты: test_rusit_syntax.
Запуск: pytest tests/test_rusit_syntax.py -v
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

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("день", "день"),
            ("Добрый день", "добрый день"),
            ("Добрый день!", "добрый день!"),
        ],
    )
    def test_noun_not_misread_as_imperative(self, tr, text, expected):
        assert tr.translate(text) == expected



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
# 25. ПОРЯДОК SVO, ДЕТЕРМИНАТОРЫ И ЧИСЛО NP
# ═══════════════════════════════════════════════

class TestSVOReordering:
    """Прямое дополнение перед глаголом выносится после сказуемого."""

    def test_pronoun_object_after_verb(self, tr):
        assert tr.translate("Я тебя люблю.") == "я люби ты"

    def test_fronted_object_after_verb(self, tr):
        assert tr.translate("Меня ты любишь.") == "ты люби я"

    def test_object_stays_after_verb(self, tr):
        assert tr.translate("Я люблю тебя.") == "я люби ты"

    def test_noun_object_singular_after_subject_before_verb(self, tr):
        assert tr.translate("Я книгу читаю.") == "я чита книга"

    def test_noun_object_plural_after_subject_before_verb(self, tr):
        assert tr.translate("Мы заявления принимаем.") == (
            "мы принима заявление"
        )



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


