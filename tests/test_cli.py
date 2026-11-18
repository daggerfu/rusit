"""Тесты CLI: перевод из файла и в файл."""

from pathlib import Path

import pytest

from rusit.cli import main


@pytest.fixture(autouse=True)
def repo_root(monkeypatch):
    """Лексикон по умолчанию загружается относительно корня репозитория."""
    monkeypatch.chdir(Path(__file__).resolve().parents[1])


def test_translate_file_to_file(tmp_path):
    source = tmp_path / "input.txt"
    target = tmp_path / "output.txt"
    source.write_text(
        "Я читаю книгу.\nТы меня любишь?\nЯ читаю книгу, а он спит.\n",
        encoding="utf-8",
    )

    assert main(["translate", "-i", str(source), "-o", str(target)]) == 0
    assert target.read_text(encoding="utf-8") == (
        "я чита книга.\nли ты люби я?\nя чита книга, а он спи.\n"
    )


def test_translate_file_to_stdout(tmp_path, capsys):
    source = tmp_path / "input.txt"
    source.write_text("Я читаю книгу.", encoding="utf-8")

    assert main(["translate", "--input-file", str(source)]) == 0
    assert capsys.readouterr().out == "я чита книга.\n"


def test_translate_text_to_file(tmp_path):
    target = tmp_path / "output.txt"

    assert main(["translate", "Я читаю книгу.", "-o", str(target)]) == 0
    assert target.read_text(encoding="utf-8") == "я чита книга.\n"


def test_translate_rejects_text_and_file(tmp_path, capsys):
    source = tmp_path / "input.txt"
    source.write_text("Я читаю книгу.", encoding="utf-8")

    assert main(["translate", "Я сплю.", "-i", str(source)]) == 2
    assert "--input" in capsys.readouterr().err


def test_translate_missing_file(capsys):
    assert main(["translate", "-i", "/nonexistent/input.txt"]) == 2
    assert "не удалось прочитать" in capsys.readouterr().err


def test_translate_markdown_file_to_file(tmp_path):
    source = tmp_path / "input.md"
    target = tmp_path / "output.md"
    source.write_text(
        "# Заголовок\n\n- первый пункт\n- второй пункт\n\n"
        "Это **важный** текст и [ссылка](https://example.com).\n",
        encoding="utf-8",
    )

    assert main(["translate", "-i", str(source), "-o", str(target)]) == 0
    assert target.read_text(encoding="utf-8") == (
        "# заголовок\n\n- первый пункт\n- второй пункт\n\n"
        "этот **важный** текст и [ссылка](https://example.com).\n"
    )


def test_translate_markdown_flag_overrides_extension(tmp_path, capsys):
    source = tmp_path / "input.txt"
    source.write_text("Текст **жирный**.\n", encoding="utf-8")

    assert main(
        ["translate", "-i", str(source), "--format", "markdown"]
    ) == 0
    assert capsys.readouterr().out == "текст **жирный**.\n"
