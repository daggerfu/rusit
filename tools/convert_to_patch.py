#!/usr/bin/env python3
"""apply_patch (OpenAI Codex) -> unified diff, с rstrip-терпимостью."""
import sys
import difflib
from pathlib import Path
from collections import defaultdict


def parse(patch_path: str):
    text = Path(patch_path).read_text(encoding="utf-8").lstrip("\ufeff")
    lines = text.splitlines()
    while lines and lines[0].strip() == "":
        lines.pop(0)
    if not lines or lines[0].strip() != "*** Begin Patch":
        sys.exit("Патч должен начинаться с '*** Begin Patch'")

    edits = defaultdict(list)
    current_file = None
    op_lines = []
    in_hunk = False
    i = 1

    def flush():
        nonlocal op_lines, in_hunk
        if current_file is not None and op_lines:
            edits[current_file].append(list(op_lines))
        op_lines, in_hunk = [], False

    while i < len(lines):
        line = lines[i]
        if line.strip() == "*** End Patch":
            flush(); return edits
        if line.startswith("*** Update File: "):
            flush()
            current_file = line[len("*** Update File: "):].strip()
            i += 1; continue
        if line.startswith("@@"):
            flush(); in_hunk = True; i += 1; continue
        if not in_hunk:
            i += 1; continue

        if line == "":
            j = i + 1
            while j < len(lines) and lines[j] == "":
                j += 1
            if j >= len(lines) or lines[j].startswith("@@") \
               or lines[j].startswith("***"):
                i += 1; continue          # разделитель между hunks
            op_lines.append((" ", ""))    # контекст: пустая строка в файле
            i += 1; continue

        if line.startswith(" "):
            op_lines.append((" ", line[1:]))
        elif line.startswith("-"):
            op_lines.append(("-", line[1:]))
        elif line.startswith("+"):
            op_lines.append(("+", line[1:]))
        else:
            sys.exit(f"Ошибка: неожиданная строка в hunk: {line!r}")
        i += 1

    sys.exit("Ошибка: патч не завершён '*** End Patch'")


def find_block(haystack, needle):
    n = len(needle)
    needle_r = [x.rstrip() for x in needle]
    for j in range(len(haystack) - n + 1):
        if [x.rstrip() for x in haystack[j:j + n]] == needle_r:
            return j
    return -1


def apply_hunk(file_lines, op_lines):
    old_lines = [t for op, t in op_lines if op in (" ", "-")]
    pos = find_block(file_lines, old_lines)
    if pos < 0:
        return False
    replacement = []
    old_idx = pos
    for op, t in op_lines:
        if op == " ":
            replacement.append(file_lines[old_idx])  # сохранить whitespace файла
            old_idx += 1
        elif op == "-":
            old_idx += 1
        elif op == "+":
            replacement.append(t)
    file_lines[pos:pos + len(old_lines)] = replacement
    return True


def main(patch_path: str) -> None:
    edits = parse(patch_path)
    for fname, hunks in edits.items():
        path = Path(fname)
        if not path.exists():
            print(f"# файл не найден: {fname}", file=sys.stderr)
            continue
        original = path.read_text(encoding="utf-8").splitlines()
        modified = list(original)
        for op_lines in hunks:
            if not apply_hunk(modified, op_lines):
                old_lines = [t for op, t in op_lines if op in (" ", "-")]
                print(
                    f"# HUNK НЕ НАЙДЕН в {fname}:\n# "
                    + "\n# ".join(repr(x) for x in old_lines),
                    file=sys.stderr,
                )
        out = list(difflib.unified_diff(
            original, modified,
            fromfile=f"a/{path.name}", tofile=f"b/{path.name}",
            lineterm="", n=3,
        ))
        if out:
            print("\n".join(out))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Использование: python3 convert_to_patch.py <apply_patch_file>")
    main(sys.argv[1])
