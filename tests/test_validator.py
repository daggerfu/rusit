"""
РУСИТ 5.3.1 — тесты: test_validator.
Запуск: pytest tests/test_validator.py -v
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


