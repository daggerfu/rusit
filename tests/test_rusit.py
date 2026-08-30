from rusit import RusitTranslator, RusitValidator


def test_translate_core_examples():
    tr = RusitTranslator()
    assert tr.translate("Я читаю книгу.") == "я чита книга"
    assert tr.translate("Мы будем строить дом.") == "мы буд строи дом"
    assert tr.translate("Я прочитал новую книгу моего друга.") == "я был кон чита новый книга у я друг"


def test_question_and_validation():
    tr = RusitTranslator()
    assert tr.translate("Ты читаешь книгу?").startswith("ли ")
    validator = RusitValidator()
    assert validator.validate("я был кон чита книга у брат").ok
    bad = validator.validate("я кон нач чита")
    assert not bad.ok
