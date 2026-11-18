"""Тесты перевода Markdown с сохранением разметки."""

import pytest

from rusit import RusitTranslator
from rusit.markdown import looks_like_markdown


@pytest.fixture(scope="module")
def tr():
    return RusitTranslator()


def test_headings_and_lists_preserved(tr):
    source = (
        "# Заголовок\n"
        "\n"
        "- первый пункт\n"
        "- второй пункт\n"
        "\n"
        "1. первый пункт\n"
        "\n"
        "> Цитата\n"
    )
    assert tr.translate_markdown(source) == (
        "# заголовок\n"
        "\n"
        "- первый пункт\n"
        "- второй пункт\n"
        "\n"
        "1. первый пункт\n"
        "\n"
        "> цитата\n"
    )


def test_inline_markup_preserved(tr):
    source = (
        "Это **важный** текст и *курсив*, "
        "а также [ссылка](https://example.com)."
    )
    assert tr.translate_markdown(source) == (
        "этот **важный** текст и *курсив*, "
        "а также [ссылка](https://example.com)."
    )


def test_code_blocks_not_translated(tr):
    source = (
        "```python\n"
        'print("Я читаю книгу.")\n'
        "```\n"
        "\n"
        "    Я читаю книгу.\n"
    )
    assert tr.translate_markdown(source) == source


def test_front_matter_and_table_preserved(tr):
    source = (
        "---\n"
        "title: Тест\n"
        "---\n"
        "\n"
        "| Русский | RUSIT |\n"
        "| --- | --- |\n"
        "| книга | книга |\n"
    )
    assert tr.translate_markdown(source) == (
        "---\n"
        "title: Тест\n"
        "---\n"
        "\n"
        "| русский | rusit |\n"
        "| --- | --- |\n"
        "| книга | книга |\n"
    )


def test_inline_code_link_destination_and_html_untouched(tr):
    source = (
        "Ссылка `код с * звёздочкой` на "
        "[сайт](https://example.com/a(b)?x=1) и <span>текст</span>."
    )
    result = tr.translate_markdown(source)
    assert "`код с * звёздочкой`" in result
    assert "[сайт](https://example.com/a(b)?x=1)" in result
    assert "<span>" in result and "</span>" in result


def test_no_punctuation_or_blank_lines_lost(tr):
    source = "Ты меня любишь?\n\nЯ читаю книгу, а он спит.\n"
    assert tr.translate_markdown(source) == (
        "ли ты люби я?\n\nя чита книга, а он спи.\n"
    )


def test_looks_like_markdown():
    assert looks_like_markdown("# Заголовок")
    assert looks_like_markdown("текст **жирный**")
    assert not looks_like_markdown("обычный текст без разметки")
