"""Regex-based Korean Bible reference detection -- no AI needed.

Handles the way pastors actually write a reference: either alone on its own
line ("요한복음 3:16", "요 3:16-18", "삼상 15장", "시 23편"), or with their
own hand-typed/pasted verse text tacked on right after ("삼상17:31~32 어떤
사람이 ..."). Either way only the leading reference is parsed -- anything
after it is ignored, since the caller replaces the whole line with the
actual scraped verse text rather than trusting a manually retyped copy.
"""
from __future__ import annotations

import re

from bible_books import ALL_BOOK_NAMES, resolve_book_name

_BOOK_PATTERN = "|".join(re.escape(name) for name in ALL_BOOK_NAMES)

_REFERENCE_RE = re.compile(
    rf"^({_BOOK_PATTERN})\s*(\d+)\s*"
    r"(?:장|:|편)\s*"
    r"(?:(\d+)\s*(?:[-~]\s*(\d+))?\s*절?)?"
)


def parse_reference(line: str) -> dict | None:
    """Return {book, chapter, start, end} if the line *starts with* a Bible
    reference, else None. A chapter-only reference (no verse) covers the
    whole chapter (start=1, end=999 -- fetch_bible clips to what exists)."""
    line = line.strip()
    if not line:
        return None

    m = _REFERENCE_RE.match(line)
    if not m:
        return None

    raw_book, chapter, start, end = m.groups()
    book = resolve_book_name(raw_book)
    if not book:
        return None

    chapter = int(chapter)
    if start is None:
        start, end = 1, 999
    else:
        start = int(start)
        end = int(end) if end else start

    return {"book": book, "chapter": chapter, "start": start, "end": end}
