"""Валидатор грамматики РУСИТ 5.3.1."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


ZONE_ORDER = {
    "не": 0, "был": 1, "буд": 1,
    "про": 2, "сей": 3,
    "кон": 4, "нач": 4, "пере": 4, "прод": 4,
    "получ": 4, "перест": 4,
    "ста": 5,
    "ся": 7,
}

BOUNDARY = {"кон", "нач", "пере", "прод", "получ", "перест"}

INCOMPATIBLE = {
    frozenset({"кон", "нач"}), frozenset({"кон", "пере"}),
    frozenset({"кон", "прод"}), frozenset({"нач", "пере"}),
    frozenset({"нач", "прод"}), frozenset({"пере", "прод"}),
    frozenset({"про", "кон"}), frozenset({"про", "нач"}),
    frozenset({"про", "пере"}), frozenset({"про", "прод"}),
    frozenset({"про", "получ"}), frozenset({"про", "перест"}),
    frozenset({"про", "сей"}), frozenset({"про", "ста"}),
    frozenset({"сей", "прод"}), frozenset({"сей", "кон"}),
}

RELATIONAL = {"у", "от", "к", "с", "в", "на", "из", "о"}

PARTICLES = {
    "не", "был", "буд", "про", "сей",
    "кон", "нач", "пере", "прод", "получ", "перест",
    "ста", "ся", "ли", "бы", "да", "же",
    "уже", "ещё", "еще", "есть", "би", "вы",
}

DEPENDENT_REQUIRED = RELATIONAL | {"би"}

_TOKEN_RE = re.compile(r"[А-Яа-яЁёA-Za-z]+|\d+|[!?.,;:—\-]")


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def error(self) -> str | None:
        """Совместимость со старым API."""
        return self.errors[0] if self.errors else None


class RusitValidator:

    def validate(self, sentence: str) -> ValidationResult:
        tokens = sentence.lower().split()
        errors: list[str] = []
        warnings: list[str] = []

        particles = [t for t in tokens if t in ZONE_ORDER]

        # 1. Запрещённые пары
        for i in range(len(particles)):
            for j in range(i + 1, len(particles)):
                pair = frozenset({particles[i], particles[j]})
                if pair in INCOMPATIBLE:
                    errors.append(
                        f"Несовместимые частицы: '{particles[i]}' + '{particles[j]}'"
                    )

        # 2. Не более одной граничной
        boundary_found = [p for p in particles if p in BOUNDARY]
        if len(boundary_found) > 1:
            errors.append(f"Более одной граничной частицы: {boundary_found}")

        # 3. был и буд взаимоисключающие
        if "был" in particles and "буд" in particles:
            errors.append("был и буд взаимоисключающие")

        # 4. Порядок зон
        prev_zone = -1
        for p in particles:
            zone = ZONE_ORDER.get(p)
            if zone is None:
                continue
            if zone < prev_zone:
                errors.append(
                    f"Нарушен порядок зон: '{p}' (зона {zone}) после зоны {prev_zone}"
                )
                break
            prev_zone = zone

        # 5. Незавершённые предлоги / маркеры без зависимого слова
        for i, tok in enumerate(tokens):
            if tok in DEPENDENT_REQUIRED:
                if i + 1 >= len(tokens):
                    errors.append(f"'{tok}' без зависимого слова")

        return ValidationResult(ok=len(errors) == 0, errors=errors, warnings=warnings)

    def is_valid(self, sentence: str) -> bool:
        return self.validate(sentence).ok

    def explain(self, text: str) -> list[dict]:
        """Классификация токенов РУСИТ-текста."""
        result = []
        for token in _TOKEN_RE.findall(text):
            lower = token.lower()
            if re.fullmatch(r"[!?.,;:—\-]", token):
                result.append({"token": token, "type": "punctuation"})
            elif lower in PARTICLES:
                item = {"token": token, "type": "particle"}
                if lower in ZONE_ORDER:
                    item["zone"] = ZONE_ORDER[lower]
                if lower in BOUNDARY:
                    item["boundary"] = True
                result.append(item)
            elif lower in RELATIONAL:
                result.append({"token": token, "type": "relational"})
            else:
                result.append({"token": token, "type": "lexeme"})
        return result
