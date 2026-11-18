"""Эвристическая оценка качества перевода книг (РУСИТ 5.3.1)."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/work")
from rusit.validator import RusitValidator

SRC = Path("/work/books")
DST = Path("/work/books_rusit")


def main() -> None:
    v = RusitValidator()
    stats = Counter()
    examples: dict[str, list[tuple[str, str, str]]] = {
        "invalid": [],
        "error_marker": [],
        "unicode_or_latin": [],
        "u_overuse": [],
        "mnogo_heavy": [],
    }

    for dst in sorted(DST.rglob("*.txt")):
        src = SRC / dst.relative_to(DST)
        src_lines = src.read_text(encoding="utf-8", errors="replace").splitlines()
        dst_lines = dst.read_text(encoding="utf-8").splitlines()
        for i, (s, t) in enumerate(zip(src_lines, dst_lines), 1):
            stats["pairs"] += 1
            if not s.strip():
                stats["blank"] += 1
                continue
            if "[ERROR:" in t:
                stats["error_marker"] += 1
                if len(examples["error_marker"]) < 5:
                    examples["error_marker"].append((str(src), i, t[:160]))
                continue
            val = v.validate(t.rstrip(".!?;:,"))
            if not val.ok:
                stats["invalid"] += 1
                if len(examples["invalid"]) < 8:
                    examples["invalid"].append((str(src), i, f"{t[:140]} :: {val.errors[:2]}"))
            words = t.split()
            if any(any(ord(c) < 128 and c.isalpha() for c in w) for w in words):
                stats["latin_in_output"] += 1
            if t.count(" у ") >= 3:
                stats["u_overuse"] += 1
                if len(examples["u_overuse"]) < 5:
                    examples["u_overuse"].append((str(src), i, t[:160]))
            if t.count("много") >= 4:
                stats["mnogo_heavy"] += 1
                if len(examples["mnogo_heavy"]) < 5:
                    examples["mnogo_heavy"].append((str(src), i, t[:160]))

    print("=== Статистика ===")
    for k in ["pairs", "blank", "invalid", "error_marker", "latin_in_output", "u_overuse", "mnogo_heavy"]:
        print(f"{k}: {stats[k]}")
    nonblank = stats["pairs"] - stats["blank"] - stats["error_marker"]
    if nonblank:
        print(f"доля валидных (непустых, без ошибок): {(nonblank - stats['invalid']) / nonblank:.1%}")
    for kind, items in examples.items():
        if items:
            print(f"\n=== Примеры: {kind} ===")
            for path, lineno, text in items:
                print(f"{Path(path).name}:{lineno}: {text}")


if __name__ == "__main__":
    main()
