"""Mixin для синтаксического анализа через spaCy."""

from __future__ import annotations

from typing import Optional


class SpacyMixin:
    def _prepare_spacy(
        self, tokens: list[str], text: str | None = None
    ) -> None:
        """Построить spaCy-разбор, соответствующий текущим токенам."""
        self._spacy_doc = None
        self._spacy_token_map = {}
        self._spacy_reverse_map = {}
        if self.nlp is None:
            return
        source = text if text is not None else " ".join(tokens)
        self._spacy_doc = self.nlp(source)
        self._spacy_token_map = self._build_spacy_token_map(
            tokens, self._spacy_doc
        )
        self._spacy_reverse_map = {
            spacy_index: local_index
            for local_index, spacy_index in self._spacy_token_map.items()
        }

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

    def _spacy_lemma(self, index: int) -> Optional[str]:
        token = self._spacy_token(index)
        if token is None:
            return None
        return token.lemma_.lower().replace("ё", "е")

    def _spacy_pos(self, index: int) -> Optional[str]:
        token = self._spacy_token(index)
        return token.pos_ if token is not None else None

    def _spacy_dep(self, index: int) -> Optional[str]:
        token = self._spacy_token(index)
        return token.dep_ if token is not None else None

    def _spacy_morph(self, index: int, feature: str) -> Optional[str]:
        token = self._spacy_token(index)
        if token is None:
            return None
        values = token.morph.get(feature)
        return values[0].lower() if values else None

    def _spacy_head_index(self, index: int) -> Optional[int]:
        """Локальный индекс головного слова в dependency-дереве."""
        token = self._spacy_token(index)
        if token is None:
            return None
        return self._spacy_reverse_map.get(token.head.i)

    def _spacy_agent_index(self, index: int) -> Optional[int]:
        """Индекс одушевлённого агента при пассивном сказуемом."""
        for child in self._spacy_children(index):
            if child.dep_ not in {"obl", "obl:agent", "nsubj:pass"}:
                continue
            if child.pos_ not in {"NOUN", "PROPN", "PRON"}:
                continue
            if "Ins" not in child.morph.get("Case"):
                continue
            agent_index = self._spacy_reverse_map.get(child.i)
            if agent_index is not None:
                return agent_index
        return None
