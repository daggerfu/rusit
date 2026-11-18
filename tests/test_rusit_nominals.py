"""
РУСИТ 5.3.1 — тесты: test_rusit_nominals.
Запуск: pytest tests/test_rusit_nominals.py -v
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
        assert result == "мой книга"

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

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("Красно стекло.", "красно стекло"),
            ("делать красиво", "дела красиво"),
        ],
    )
    def test_krasivyy_not_misread_as_verb(self, tr, text, expected):
        assert tr.translate(text) == expected

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

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("Он выше меня.", "он более высокий чем я"),
            ("Она лучше тебя.", "она более хороший чем ты"),
            ("Он выше брата.", "он более высокий чем брат"),
        ],
    )
    def test_comparative_suffix(self, tr, text, expected):
        # Сравнительный суффикс → «более», стандарт — «чем» (§5.4).
        assert tr.translate(text) == expected

    def test_comparative_predicative_no_standard(self, tr):
        # Предикативное сравнение без стандарта (§5.4).
        assert tr.translate("Это хуже.") == "этот более плохой"

    def test_comparative_explicit_chem(self, tr):
        # Явный союз «чем» не дублируется.
        assert tr.translate("Я выше, чем ты.") == "я более высокий чем ты"

    def test_comparative_not_quantifier(self, tr):
        # «больше» при количественном значении — не сравнение.
        result = tr.translate("Больше людей пришло.")
        assert "более" not in result

    def test_comparative_adverb_untouched(self, tr):
        # Наречная сравнительная степень без стандарта — как есть.
        assert tr.translate("Беги быстрее.") == "бежа быстрее"



# ═══════════════════════════════════════════════
# 12. МНОЖЕСТВЕННОЕ ЧИСЛО
# ═══════════════════════════════════════════════

class TestPlurality:
    """Нейтральное число: много только от явного квантификатора."""

    def test_bare_plural_has_no_mnogo(self, tr):
        result = tr.translate("Люди закрыли окна.")
        assert "много" not in result
        assert "человек" in result
        assert "окно" in result

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



class TestPluralDeterminers:
    """Множественные указательные/неопределённые детерминаторы."""

    def test_eti(self, tr):
        assert tr.translate("Эти дома.") == "эти дом"

    def test_te(self, tr):
        assert tr.translate("Те книги.") == "те книга"

    def test_neskolko(self, tr):
        assert tr.translate("Несколько книг.") == "несколько книга"

    def test_nekotorye(self, tr):
        assert tr.translate("Некоторые люди.") == "некоторые человек"

    def test_u_neskolkih(self, tr):
        assert tr.translate("У нескольких друзей.") == "у несколько друг"



class TestNounPhraseNumber:
    """Грамматически нейтральное число: количество только по явному слову."""

    @pytest.mark.parametrize("russian, expected", [
        ("Большие дома стоят.", "большой дом стоя"),
        ("Маленькие дети играют.", "маленький ребёнок игра"),
        ("Два больших дома.", "два большой дом"),
        ("Все красивые дома.", "все красивый дом"),
        ("Несколько старых книг.", "несколько старый книга"),
        ("Много интересных книг.", "много интересный книга"),
        ("Дети любят книги.", "ребёнок люби книга"),
        ("Они любят книги.", "они люби книга"),
    ])
    def test_np_plural_marker(self, tr, russian, expected):
        assert tr.translate(russian) == expected


class TestGeneralNumber:
    """Обобщённое число: форма не различает один и несколько предметов."""

    @pytest.mark.parametrize("russian, expected", [
        ("Я люблю книгу.", "я люби книга"),
        ("Я люблю книги.", "я люби книга"),
        ("Я купил три книги.", "я кон купи три книга"),
        ("Я купил много книг.", "я кон купи много книга"),
        ("Я вижу этих людей.", "я виде эти человек"),
    ])
    def test_general_number(self, tr, russian, expected):
        assert tr.translate(russian) == expected


