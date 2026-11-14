"""
Хранение лексикона РУСИТ в SQLite.

Схема базы:
    meta(key, value)                — метаданные лексикона (version, revision, ...)
    sections(name, kind)            — список секций; kind: 'dict' | 'set'
    entries(section, key, value)    — словарные статьи; для секций-множеств value = key

Все словарные секции лексикона (verbs, nouns, particles, ...) и особые слова
(пользовательские дополнения) хранятся в одной таблице entries.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_META_SECTION = "meta"


class LexiconDB:
    """SQLite-база лексикона РУСИТ."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    # ═══════════════════════════════════════════
    # СХЕМА
    # ═══════════════════════════════════════════

    def _create_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sections (
                name TEXT PRIMARY KEY,
                kind TEXT NOT NULL CHECK (kind IN ('dict', 'set'))
            );
            CREATE TABLE IF NOT EXISTS entries (
                section TEXT NOT NULL REFERENCES sections(name),
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY (section, key)
            );
            """
        )
        self.conn.commit()

    # ═══════════════════════════════════════════
    # КОНТЕКСТНЫЙ МЕНЕДЖЕР
    # ═══════════════════════════════════════════

    def __enter__(self) -> "LexiconDB":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def close(self) -> None:
        self.conn.close()

    # ═══════════════════════════════════════════
    # ЗАГРУЗКА / ВЫГРУЗКА JSON
    # ═══════════════════════════════════════════

    def import_json(self, json_path: str | Path) -> None:
        """Загрузить лексикон из JSON-файла, заменив текущее содержимое базы."""
        with open(json_path, encoding="utf-8") as f:
            lexicon: dict = json.load(f)
        self.import_dict(lexicon)

    def import_dict(self, lexicon: dict) -> None:
        """Загрузить лексикон из словаря, заменив текущее содержимое базы."""
        self.conn.executescript(
            """
            DELETE FROM entries;
            DELETE FROM sections;
            DELETE FROM meta;
            """
        )
        for key, value in lexicon.get(_META_SECTION, {}).items():
            self.conn.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?)",
                (str(key), json.dumps(value, ensure_ascii=False)),
            )
        for section, content in lexicon.items():
            if section == _META_SECTION:
                continue
            if isinstance(content, dict):
                self._register_section(section, "dict")
                for k, v in content.items():
                    self._upsert_entry(section, str(k), str(v))
            elif isinstance(content, list):
                self._register_section(section, "set")
                for item in content:
                    self._upsert_entry(section, str(item), str(item))
            else:
                raise ValueError(
                    f"Неподдерживаемый тип секции '{section}': "
                    f"{type(content).__name__}"
                )
        self.conn.commit()

    def export_json(self, json_path: str | Path) -> None:
        """Сохранить лексикон из базы в JSON-файл."""
        lexicon = self.load()
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(lexicon, f, ensure_ascii=False, indent=2)

    def load(self) -> dict:
        """Собрать словарь лексикона из базы (структура как у JSON-файла)."""
        lexicon: dict = {}
        meta = {
            key: json.loads(value)
            for key, value in self.conn.execute(
                "SELECT key, value FROM meta"
            ).fetchall()
        }
        if meta:
            lexicon[_META_SECTION] = meta
        for section, kind in self.conn.execute(
            "SELECT name, kind FROM sections ORDER BY rowid"
        ).fetchall():
            rows = self.conn.execute(
                "SELECT key, value FROM entries WHERE section = ? "
                "ORDER BY rowid",
                (section,),
            ).fetchall()
            if kind == "set":
                lexicon[section] = [key for key, _ in rows]
            else:
                lexicon[section] = {key: value for key, value in rows}
        return lexicon

    # ═══════════════════════════════════════════
    # ОСОБЫЕ СЛОВА (РЕДАКТИРОВАНИЕ)
    # ═══════════════════════════════════════════

    def add(self, section: str, key: str, value: Optional[str] = None) -> None:
        """
        Добавить или обновить статью.
        Если value не задано, секция считается множеством (value = key).
        """
        key = key.lower().replace("ё", "е")
        if value is None:
            self._register_section(section, "set")
            value = key
        else:
            value = value.lower().replace("ё", "е")
            self._register_section(section, "dict")
        self._upsert_entry(section, key, value)
        self.conn.commit()

    def remove(self, section: str, key: str) -> bool:
        """Удалить статью. Возвращает True, если статья была удалена."""
        key = key.lower().replace("ё", "е")
        cursor = self.conn.execute(
            "DELETE FROM entries WHERE section = ? AND key = ?",
            (section, key),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def get(self, section: str, key: str) -> Optional[str]:
        """Значение статьи или None."""
        key = key.lower().replace("ё", "е")
        row = self.conn.execute(
            "SELECT value FROM entries WHERE section = ? AND key = ?",
            (section, key),
        ).fetchone()
        return row[0] if row else None

    def sections(self) -> Dict[str, str]:
        """Секции базы: имя → kind ('dict' | 'set')."""
        return dict(self.conn.execute(
            "SELECT name, kind FROM sections ORDER BY rowid"
        ).fetchall())

    def entries(self, section: str) -> List[Tuple[str, str]]:
        """Статьи секции в виде списка (key, value)."""
        return self.conn.execute(
            "SELECT key, value FROM entries WHERE section = ? ORDER BY key",
            (section,),
        ).fetchall()

    # ═══════════════════════════════════════════
    # ВНУТРЕННИЕ
    # ═══════════════════════════════════════════

    def _register_section(self, name: str, kind: str) -> None:
        self.conn.execute(
            "INSERT INTO sections (name, kind) VALUES (?, ?) "
            "ON CONFLICT(name) DO NOTHING",
            (name, kind),
        )

    def _upsert_entry(self, section: str, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO entries (section, key, value) VALUES (?, ?, ?) "
            "ON CONFLICT(section, key) DO UPDATE SET value = excluded.value",
            (section, key, value),
        )


def load_lexicon(db_path: str | Path) -> dict:
    """Словарь лексикона из SQLite-базы (структура как у JSON-файла)."""
    with LexiconDB(db_path) as db:
        return db.load()


def import_json(db_path: str | Path, json_path: str | Path) -> LexiconDB:
    """Создать базу из JSON-файла и вернуть открытую базу."""
    db = LexiconDB(db_path)
    db.import_json(json_path)
    return db
