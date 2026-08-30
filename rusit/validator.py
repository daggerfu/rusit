"""Validation, parsing and diagnostics for RUSIT 3.0 text."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .core import GRAMMAR_PARTICLES, PHASE_PARTICLES, RELATION_PARTICLES
from .translator import tokenize


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class RusitValidator:
    """Checks the most important normative RUSIT constraints."""

    forbidden_endings = ("ами", "ями", "ого", "ему", "ыми", "ими", "ешь", "ете", "ут", "ют")

    def validate(self, text: str) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        tokens = [t for t in tokenize(text) if not re.fullmatch(r"[!?.,;:—-]", t)]
        for i, tok in enumerate(tokens):
            if tok in {"был", "буд"}:
                if i + 1 < len(tokens) and tokens[i + 1] in {"был", "буд"}:
                    errors.append(f"две временные частицы подряд: {tok} {tokens[i + 1]}")
            if tok == "кон" and i + 1 < len(tokens) and tokens[i + 1] in PHASE_PARTICLES - {"прод"}:
                errors.append("недопустимая последовательность: кон + граничная фаза")
            if tok in RELATION_PARTICLES and i + 1 == len(tokens):
                errors.append(f"реляционная частица без зависимого слова: {tok}")
            if tok not in GRAMMAR_PARTICLES | RELATION_PARTICLES and tok.endswith(self.forbidden_endings):
                warnings.append(f"возможная русская флексия вместо словарной формы: {tok}")
        return ValidationResult(not errors, errors, warnings)

    def explain(self, text: str) -> list[dict[str, str]]:
        """Return token-level labels useful for teaching/debugging."""
        labels = []
        for tok in tokenize(text):
            if tok in GRAMMAR_PARTICLES:
                kind = "grammar-particle"
            elif tok in RELATION_PARTICLES:
                kind = "relation-particle"
            elif re.fullmatch(r"[!?.,;:—-]", tok):
                kind = "punctuation"
            else:
                kind = "lexeme"
            labels.append({"token": tok, "kind": kind})
        return labels
