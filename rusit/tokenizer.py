"""Токенизация текста для транслятора РУСИТ."""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(
    r"[А-Яа-яЁё]+|[A-Za-z]+|\d+|[!?.,;:—-]"
)


def tokenize(text: str) -> list[str]:
    raw = _TOKEN_RE.findall(
        text.lower().replace("ё", "е")
    )
    # Слияние дефисных композитов: «бизнес-процессы» — один токен.
    merged: list[str] = []
    i = 0
    while i < len(raw):
        if (
            i + 2 < len(raw)
            and raw[i + 1] == "-"
            and re.fullmatch(r"[а-яa-z]+", raw[i])
            and re.fullmatch(r"[а-яa-z]+", raw[i + 2])
        ):
            merged.append(raw[i] + "-" + raw[i + 2])
            i += 3
        else:
            merged.append(raw[i])
            i += 1
    return merged
