"""SpaCy support mixin for RUSIT translator."""

from __future__ import annotations

class SpacyMixin:
    def _build_spacy_token_map(
        self, tokens: list[str], doc
    ) -> dict[int, int]:
        """Сопоставить токены tokenize() с токенами spaCy."""
        mapping: dict[int, int] = {}
        spacy_tokens = list(doc)
        spacy_i = 0
        for i, token in enumerate(tokens):
            norm = token.lower().replace("ё", "е")
            found = None
            j = spacy_i
            while j < len(spacy_tokens):
                st_norm = spacy_tokens[j].text.lower().replace("ё", "е")
                if st_norm == norm:
                    found = j
                    spacy_i = j + 1
                    break
                j += 1
            if found is None:
                # Повторный поиск с начала оставшегося окна не нужен:
                # допускаем расхождения токенизации.
                continue
            mapping[i] = found
        return mapping


    def _spacy_token(self, index: int):
        """Вернуть spaCy-токен для индекса исходного токена, если есть."""
        if self._spacy_doc is None:
            return None
        spacy_index = self._spacy_token_map.get(index)
        if spacy_index is None:
            return None
        if spacy_index < 0 or spacy_index >= len(self._spacy_doc):
            return None
        return self._spacy_doc[spacy_index]


    def _spacy_children(self, index: int) -> list:
        token = self._spacy_token(index)
        if token is None:
            return []
        return list(token.children)
