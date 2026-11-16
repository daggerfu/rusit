"""Перевод Markdown с сохранением разметки и структуры документа.

Разметка не переводится: блоки кода, ссылки, HTML, сущности и inline-код
заменяются временными метками, переводится только обычный текст, после чего
метки возвращаются на место.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .translator import RusitTranslator


_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_ATX_RE = re.compile(r"^( {0,3}#{1,6}\s+)(.*)$")
_BLOCKQUOTE_RE = re.compile(r"^((?: {0,3}>\s?)+)(.*)$")
_BULLET_RE = re.compile(r"^( {0,3}[-+*]\s+)(.*)$")
_ORDERED_RE = re.compile(r"^( {0,3}\d+[.)]\s+)(.*)$")
_TASK_RE = re.compile(r"^(\[[ xX]\]\s+)(.*)$")
_HR_RE = re.compile(
    r"^ {0,3}(?:(?:\*\s*){3,}|(?:-\s*){3,}|(?:_\s*){3,})$"
)
_SETEXT_RE = re.compile(r"^ {0,3}(?:=+|-+)\s*$")
_REF_DEF_RE = re.compile(r"^ {0,3}\[[^\]]+\]:\s+\S")
_FOOTNOTE_RE = re.compile(r"^(\s*\[\^[^\]]+\]:\s*)(.*)$")
_TABLE_SEP_RE = re.compile(
    r"^\s*\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)*\|?\s*$"
)
_HTML_BLOCK_RE = re.compile(
    r"^\s*<(address|article|aside|base|basefont|blockquote|body|caption|"
    r"center|col|colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|"
    r"figcaption|figure|footer|form|frame|frameset|h[1-6]|head|header|hr|"
    r"html|iframe|legend|li|link|main|menu|menuitem|nav|noframes|ol|"
    r"optgroup|option|p|param|search|section|summary|table|tbody|td|tfoot|"
    r"th|thead|title|tr|track|ul|script|style|pre|textarea)\b",
    re.IGNORECASE,
)
_VOID_HTML_TAGS = {
    "base", "basefont", "col", "frame", "hr", "img", "input", "link",
    "menuitem", "param", "track",
}
_INDENTED_RE = re.compile(r"^(?: {4}|\t)")
_LIST_START_RE = re.compile(r"^ {0,3}(?:[-+*]|\d+[.)])\s+")

_INLINE_CODE_RE = re.compile(r"(`+)(.+?)\1")
_LINK_RE = re.compile(
    r"(!?)\[([^\]\n]*)\]\(((?:[^()\n]|\([^()\n]*\))*)\)"
)
_REF_LINK_RE = re.compile(r"(!?)\[([^\]\n]*)\]\[([^\]\n]*)\]")
_FOOTNOTE_REF_RE = re.compile(r"\[\^[^\]\n]+\]")
_INLINE_MATH_RE = re.compile(r"\$[^$\n]+\$")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->")
_AUTOLINK_RE = re.compile(r"<[^<>\s]+>")
_HTML_TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")
_ENTITY_RE = re.compile(r"&(?:#\d+|#x[0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]+);")
_URL_RE = re.compile(r"(?:https?|ftp)://[^\s<>()\[\]]+")
_NUMBER_RE = re.compile(r"\d+(?:[.,:]\d+)+")
_ESCAPE_RE = re.compile(r"\\[\\`*{}\[\]()#+\-.!_>~|]")
_EMPHASIS_RE = re.compile(r"\*{1,3}|_{1,3}|~~")
_WORD_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9]")

_MARKDOWN_HINT_RE = re.compile(
    r"(?m)^ {0,3}(?:#{1,6}\s|`{3,}|~{3,}|>\s|[-+*]\s+|\d+[.)]\s+)"
    r"|\*\*[^*\n]+\*\*"
    r"|\[[^\]\n]+\]\([^)\n]+\)"
    r"|^\s*\|.*\|\s*$"
)


def looks_like_markdown(text: str) -> bool:
    """Быстрая эвристика: похож ли текст на Markdown."""
    return bool(_MARKDOWN_HINT_RE.search(text))


def translate_markdown(text: str, translator: RusitTranslator) -> str:
    """Перевести Markdown-документ, сохранив разметку и переводы строк."""
    lines = text.split("\n")
    output: list[str] = []
    fence: tuple[str, int] | None = None
    html_end: str | None = None
    indented_code = False
    previous_blank = True
    previous_nonblank = ""
    start = _front_matter_end(lines)

    for line in lines[:start]:
        output.append(line)
    if start:
        previous_nonblank = lines[start - 1]
        previous_blank = True

    for line in lines[start:]:
        if fence is not None:
            output.append(line)
            match = _FENCE_RE.match(line)
            if (
                match
                and match.group(1)[0] == fence[0]
                and len(match.group(1)) >= fence[1]
                and not match.group(2).strip()
            ):
                fence = None
            previous_blank = not line.strip()
            if line.strip():
                previous_nonblank = line
            continue

        if html_end is not None:
            output.append(line)
            if html_end in line.lower():
                html_end = None
            previous_blank = not line.strip()
            if line.strip():
                previous_nonblank = line
            continue

        if indented_code:
            if not line.strip() or _INDENTED_RE.match(line):
                output.append(line)
                previous_blank = not line.strip()
                if line.strip():
                    previous_nonblank = line
                continue
            indented_code = False

        match = _FENCE_RE.match(line)
        if match:
            fence = (match.group(1)[0], len(match.group(1)))
            output.append(line)
            previous_blank = False
            previous_nonblank = line
            continue

        html_match = _HTML_BLOCK_RE.match(line)
        if html_match:
            tag = html_match.group(1).lower()
            output.append(line)
            closed = (
                line.rstrip().endswith("/>")
                or f"</{tag}>" in line.lower()
            )
            if tag not in _VOID_HTML_TAGS and not closed:
                html_end = f"</{tag}>"
            previous_blank = False
            previous_nonblank = line
            continue
        if line.lstrip().startswith("<!--"):
            output.append(line)
            if "-->" not in line:
                html_end = "-->"
            previous_blank = False
            previous_nonblank = line
            continue

        if (
            previous_blank
            and _INDENTED_RE.match(line)
            and not _LIST_START_RE.match(previous_nonblank)
        ):
            indented_code = True
            output.append(line)
            previous_blank = False
            previous_nonblank = line
            continue

        output.append(_translate_block_line(line, translator))
        previous_blank = not line.strip()
        if line.strip():
            previous_nonblank = line

    return "\n".join(output)


def _front_matter_end(lines: list[str]) -> int:
    """Вернуть индекс после YAML front matter, иначе 0."""
    if len(lines) < 2 or lines[0].strip() != "---":
        return 0
    if not re.match(r"^[A-Za-z_][\w-]*:\s*", lines[1]):
        return 0
    for index in range(1, len(lines)):
        if lines[index].strip() in {"---", "..."}:
            return index + 1
    return 0


def _translate_block_line(line: str, translator: RusitTranslator) -> str:
    if not line.strip():
        return line
    if _HR_RE.match(line) or _SETEXT_RE.match(line):
        return line

    footnote = _FOOTNOTE_RE.match(line)
    if footnote:
        return footnote.group(1) + _translate_inline(
            footnote.group(2), translator
        )
    if _REF_DEF_RE.match(line):
        return line

    if "|" in line and (
        line.lstrip().startswith("|")
        or line.rstrip().endswith("|")
        or line.count("|") >= 2
    ):
        if _TABLE_SEP_RE.match(line):
            return line
        return "|".join(
            _translate_inline(cell, translator)
            for cell in _split_table_cells(line)
        )

    blockquote = _BLOCKQUOTE_RE.match(line)
    if blockquote:
        return blockquote.group(1) + _translate_block_line(
            blockquote.group(2), translator
        )

    heading = _ATX_RE.match(line)
    if heading:
        return heading.group(1) + _translate_inline(
            heading.group(2), translator
        )

    item = _BULLET_RE.match(line) or _ORDERED_RE.match(line)
    if item:
        prefix, rest = item.groups()
        task = _TASK_RE.match(rest)
        if task:
            return prefix + task.group(1) + _translate_inline(
                task.group(2), translator
            )
        return prefix + _translate_inline(rest, translator)

    return _translate_inline(line, translator)


def _split_table_cells(line: str) -> list[str]:
    """Разделить строку таблицы по неэкранированным `|` вне code-span."""
    cells: list[str] = []
    buf: list[str] = []
    index = 0
    while index < len(line):
        if line[index] == "\\" and index + 1 < len(line):
            buf.append(line[index:index + 2])
            index += 2
            continue
        if line[index] == "`":
            match = _INLINE_CODE_RE.match(line, index)
            if match:
                buf.append(match.group(0))
                index = match.end()
                continue
        if line[index] == "|":
            cells.append("".join(buf))
            buf = []
        else:
            buf.append(line[index])
        index += 1
    cells.append("".join(buf))
    return cells


def _translate_inline(text: str, translator: RusitTranslator) -> str:
    """Перевести одну строку, сохранив inline-разметку."""
    stripped = text.lstrip(" \t")
    leading = text[:len(text) - len(stripped)]
    core = stripped.rstrip(" \t")
    trailing = stripped[len(core):]
    if not core:
        return text

    placeholders: list[tuple[str, bool, bool]] = []
    masked: list[str] = []
    _mask_inline(core, placeholders, masked)
    translated = translator.translate(
        "".join(masked), preserve_punctuation=True
    )
    restored = _restore_inline(translated, placeholders)
    return leading + restored + trailing


def _mask_inline(
    text: str,
    placeholders: list[tuple[str, bool, bool]],
    out: list[str],
) -> None:
    """Заменить разметку метками, оставив обычный текст для перевода."""
    index = 0
    while index < len(text):
        match = _ESCAPE_RE.match(text, index)
        if match:
            _add_placeholder(text, index, match.end(), match.group(0),
                             placeholders, out)
            index = match.end()
            continue

        match = _INLINE_CODE_RE.match(text, index)
        if match:
            _add_placeholder(text, index, match.end(), match.group(0),
                             placeholders, out)
            index = match.end()
            continue

        match = _LINK_RE.match(text, index)
        if match:
            prefix = match.group(1) + "["
            _add_placeholder(text, index, index + len(prefix), prefix,
                             placeholders, out)
            _mask_inline(match.group(2), placeholders, out)
            inner_start = match.start(3) - 2
            _add_placeholder(text, inner_start, match.start(3), "](",
                             placeholders, out)
            _add_placeholder(text, match.start(3), match.end(3),
                             match.group(3), placeholders, out)
            _add_placeholder(text, match.end(3), match.end(3) + 1, ")",
                             placeholders, out)
            index = match.end()
            continue

        match = _REF_LINK_RE.match(text, index)
        if match:
            prefix = match.group(1) + "["
            _add_placeholder(text, index, index + len(prefix), prefix,
                             placeholders, out)
            _mask_inline(match.group(2), placeholders, out)
            inner_start = match.start(3) - 2
            _add_placeholder(text, inner_start, match.start(3), "][",
                             placeholders, out)
            _add_placeholder(text, match.start(3), match.end(3),
                             match.group(3), placeholders, out)
            _add_placeholder(text, match.end(3), match.end(3) + 1, "]",
                             placeholders, out)
            index = match.end()
            continue

        match = _FOOTNOTE_REF_RE.match(text, index)
        if match:
            _add_placeholder(text, index, match.end(), match.group(0),
                             placeholders, out)
            index = match.end()
            continue

        match = _INLINE_MATH_RE.match(text, index)
        if match:
            _add_placeholder(text, index, match.end(), match.group(0),
                             placeholders, out)
            index = match.end()
            continue

        match = _HTML_COMMENT_RE.match(text, index)
        if match:
            _add_placeholder(text, index, match.end(), match.group(0),
                             placeholders, out)
            index = match.end()
            continue

        match = _AUTOLINK_RE.match(text, index)
        if match:
            _add_placeholder(text, index, match.end(), match.group(0),
                             placeholders, out)
            index = match.end()
            continue

        match = _HTML_TAG_RE.match(text, index)
        if match:
            _add_placeholder(text, index, match.end(), match.group(0),
                             placeholders, out)
            index = match.end()
            continue

        match = _ENTITY_RE.match(text, index)
        if match:
            _add_placeholder(text, index, match.end(), match.group(0),
                             placeholders, out)
            index = match.end()
            continue

        match = _URL_RE.match(text, index)
        if match:
            _add_placeholder(text, index, match.end(), match.group(0),
                             placeholders, out)
            index = match.end()
            continue

        match = _NUMBER_RE.match(text, index)
        if match:
            _add_placeholder(text, index, match.end(), match.group(0),
                             placeholders, out)
            index = match.end()
            continue

        match = _EMPHASIS_RE.match(text, index)
        if match:
            _add_placeholder(text, index, match.end(), match.group(0),
                             placeholders, out)
            index = match.end()
            continue

        out.append(text[index])
        index += 1


def _add_placeholder(
    text: str,
    start: int,
    end: int,
    value: str,
    placeholders: list[tuple[str, bool, bool]],
    out: list[str],
) -> None:
    left_tight = start > 0 and not text[start - 1].isspace()
    right_tight = end < len(text) and not text[end].isspace()
    placeholders.append((value, left_tight, right_tight))
    if out and not out[-1][-1:].isspace():
        out.append(" ")
    out.append(_placeholder(len(placeholders) - 1))
    out.append(" ")


def _placeholder(index: int) -> str:
    """Метка из одних латинских букв: транслятор не меняет её."""
    letters = ""
    value = index
    while True:
        letters = chr(ord("a") + value % 26) + letters
        value = value // 26 - 1
        if value < 0:
            break
    return f"zzmdq{letters}qzz"


def _restore_inline(
    text: str, placeholders: list[tuple[str, bool, bool]]
) -> str:
    """Вернуть разметку на место и восстановить прилипание знаков."""
    result = re.sub(r"[ \t]{2,}", " ", text)
    sentinels = [f"\ue000{index}\ue001"
                 for index in range(len(placeholders))]

    for index, sentinel in enumerate(sentinels):
        result = result.replace(_placeholder(index), sentinel)

    for index, (_, left_tight, right_tight) in enumerate(placeholders):
        sentinel = sentinels[index]
        if left_tight:
            result = re.sub(r"[ \t]*" + re.escape(sentinel),
                            sentinel, result)
        if right_tight:
            result = re.sub(re.escape(sentinel) + r"[ \t]*",
                            sentinel, result)

    for sentinel, (value, _, _) in zip(sentinels, placeholders):
        result = result.replace(sentinel, value)

    return result
