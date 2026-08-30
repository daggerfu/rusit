"""Corpus helpers for aligned Russian/RUSIT examples."""
from __future__ import annotations

import csv
from pathlib import Path
from .translator import RusitTranslator
from .validator import RusitValidator


EXAMPLES = [
    ("Я читаю книгу.", "я чита книга"),
    ("Я прочитал новую книгу моего друга.", "я был кон чита новый книга у мой друг"),
    ("Мы будем строить дом.", "мы буд строи дом"),
    ("Книга лежит на столе.", "книга лежит на стол"),
    ("Дом был построен рабочими.", "дом был кон строи би рабочий"),
]


def build_demo_corpus(path: str | Path) -> None:
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ru", "rusit"])
        writer.writerows(EXAMPLES)


def score_file(path: str | Path) -> dict[str, int]:
    translator = RusitTranslator()
    validator = RusitValidator()
    total = exact = valid = 0
    with Path(path).open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            total += 1
            got = translator.translate(row["ru"])
            exact += int(got == row["rusit"])
            valid += int(validator.validate(got).ok)
    return {"total": total, "exact": exact, "valid": valid}
