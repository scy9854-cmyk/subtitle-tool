"""Deterministic (non-AI) fallback formatters.

Hymn verses are word-wrapped to a fixed max characters per line (screen
readability limit) and grouped two lines at a time. CCM structure labeling
is a best-effort heuristic based on exact repeated line-blocks, so it can
miss choruses whose wording varies slightly between repeats, and it cannot
reliably detect a Bridge.
"""

import re

import formatters
import scrapers
from reference_parser import parse_reference

_AD_HEADER_RE = re.compile(r"^(\d+)\s*[|.)]\s*(.+)$")


MAX_LINE_CHARS = 20  # screen-calibrated hard ceiling: longer lines overflow the subtitle slide


def split_two_lines(text: str, prefix: str = "", max_chars: int = MAX_LINE_CHARS):
    """Balance-split text into exactly two lines at the best word boundary.
    Returns None if even the best balance point leaves a line over max_chars
    -- the caller should fall back to wrap_line (possibly multiple groups)
    for text that doesn't comfortably fit in two lines."""
    words = text.split()
    if not words:
        return None
    if len(words) == 1:
        line = f"{prefix}{words[0]}"
        return [line] if len(line) <= max_chars else None

    lengths = [len(w) for w in words]
    plen = len(prefix)
    total = sum(lengths) + (len(words) - 1) + plen  # prefix counts toward line1's share
    best_i, best_diff = 1, float("inf")
    for i in range(1, len(words)):
        left = plen + sum(lengths[:i]) + (i - 1)
        diff = abs(left - (total - left))
        if diff < best_diff:
            best_diff, best_i = diff, i

    line1 = f"{prefix}{' '.join(words[:best_i])}"
    line2 = " ".join(words[best_i:])
    if len(line1) <= max_chars and len(line2) <= max_chars:
        return [line1, line2]
    return None


def wrap_line(text: str, max_chars: int = MAX_LINE_CHARS, prefix: str = "") -> list:
    """Greedily pack words onto lines of at most max_chars (never splits a word).

    If prefix is given, it's prepended to the first output line and its length
    is deducted from that first line's budget so the prefix itself never pushes
    the line over max_chars.
    """
    words = text.split()
    lines = []
    current, current_len = [], 0
    budget = max_chars - len(prefix)
    for w in words:
        add_len = len(w) + (1 if current else 0)
        if current and current_len + add_len > budget:
            lines.append(" ".join(current))
            current, current_len = [w], len(w)
            budget = max_chars
        else:
            current.append(w)
            current_len += add_len
    if current:
        lines.append(" ".join(current))
    if lines and prefix:
        lines[0] = f"{prefix}{lines[0]}"
    return lines


def pair_lines(lines: list) -> list:
    """Group already-wrapped lines two at a time (no re-merging -- they're already
    at the max width, so combining two would blow the per-line budget again)."""
    return ["\n".join(lines[i:i + 2]) for i in range(0, len(lines), 2)]


def segment_to_lines(seg: str, prefix: str = "") -> list:
    """A natural segment (one of the hymn site's own <br/>-separated pieces)
    is kept to exactly two lines whenever that fits within SEGMENT_SOFT_MAX;
    only a segment too long for a clean 2-line split falls back to the
    stricter multi-line hard wrap."""
    return split_two_lines(seg, prefix=prefix) or wrap_line(seg, prefix=prefix)


def format_hymn_rule(verses: list, refrain) -> str:
    """verses is a list of verses, each itself a list of that verse's original
    segments; refrain is one such segment list or None."""
    refrain_blocks = []
    if refrain:
        for seg in refrain:
            refrain_blocks.extend(pair_lines(segment_to_lines(seg)))

    blocks = []
    for i, segments in enumerate(verses, 1):
        for j, seg in enumerate(segments):
            prefix = f"{i}. " if j == 0 else ""
            blocks.extend(pair_lines(segment_to_lines(seg, prefix)))
        blocks.extend(refrain_blocks)
    return "\n\n".join(blocks)


def _label_paragraphs(paragraphs: list) -> list:
    """paragraphs -> [(label, lines)]. A paragraph that reappears verbatim
    later is the Chorus (included once, at its first occurrence); everything
    else is a Verse in order, except a short unique trailing paragraph after
    a Chorus, which is called a Bridge."""
    chorus = next((p for i, p in enumerate(paragraphs) if p in paragraphs[i + 1:]), None)

    segments = []
    seen = set()
    verse_count = 0
    chorus_included = False
    for idx, para in enumerate(paragraphs):
        if chorus is not None and para == chorus:
            if not chorus_included:
                segments.append(("Chorus", para))
                chorus_included = True
            continue
        key = tuple(para)
        if key in seen:
            continue
        seen.add(key)
        is_last = idx == len(paragraphs) - 1
        if is_last and len(para) <= 4 and chorus_included and verse_count >= 1:
            segments.append(("Bridge", para))
        else:
            verse_count += 1
            segments.append((f"Verse {verse_count}", para))
    return segments


def _minimal_period(block: list) -> list:
    """If block is itself just a smaller pattern repeated back-to-back
    (e.g. the chorus sung 3x in a row got matched as one 12-line block),
    reduce it to that smallest repeating unit."""
    n = len(block)
    for d in range(1, n):
        if n % d == 0 and all(block[i] == block[i % d] for i in range(n)):
            return block[:d]
    return block


def _find_repeated_block(lines: list):
    """Sliding-window search for the largest exact-repeated run of lines --
    used when the source has no blank-line stanza breaks at all, so there's
    no paragraph structure to split on in the first place."""
    n = len(lines)
    for size in range(min(12, n // 2), 1, -1):
        seen = {}
        for start in range(n - size + 1):
            block = tuple(lines[start:start + size])
            if block in seen:
                block = _minimal_period(list(block))
                return block, len(block)
            seen[block] = start
    return None, 0


def _paragraphs_from_flat_lines(lines: list) -> list:
    block, size = _find_repeated_block(lines)
    if not block:
        return [lines] if lines else []

    starts = set()
    i, n = 0, len(lines)
    while i <= n - size:
        if lines[i:i + size] == block:
            starts.add(i)
            i += size
        else:
            i += 1

    paragraphs, buf, i = [], [], 0
    while i < n:
        if i in starts:
            if buf:
                paragraphs.append(buf)
                buf = []
            paragraphs.append(lines[i:i + size])
            i += size
        else:
            buf.append(lines[i])
            i += 1
    if buf:
        paragraphs.append(buf)
    return paragraphs


def format_ccm_rule(lyrics: str) -> str:
    """Each unique section (Verse/Chorus/Bridge) is emitted only once, even if
    it repeats several times in the song, since this is a subtitle source and
    a repeated section reuses the same slide.

    Section boundaries come straight from the source's own blank-line
    stanza breaks where they exist (Bugs Music lyrics are usually laid out
    this way). Some songs' lyrics have none at all, though -- in that case
    fall back to finding the largest exact-repeated run of lines (the
    Chorus) and treat the stretches between its occurrences as paragraphs."""
    paragraphs = []
    for para in re.split(r"\n\s*\n", lyrics.strip()):
        para_lines = [ln.strip() for ln in para.split("\n") if ln.strip()]
        if para_lines:
            paragraphs.append(para_lines)

    if len(paragraphs) <= 1:
        flat_lines = [ln.strip() for ln in lyrics.split("\n") if ln.strip()]
        paragraphs = _paragraphs_from_flat_lines(flat_lines)
    if not paragraphs:
        return ""

    segments = _label_paragraphs(paragraphs)
    out_blocks = [f"{label}\n" + "\n".join(seg_lines) for label, seg_lines in segments]
    return "\n\n".join(out_blocks)


def format_sermon_rule(raw_text: str) -> str:
    """No AI: a line is either a bare Bible reference (regex-matched via
    reference_parser, then expanded with the real scraped text -- same as
    the AI path), a '#' image cue, or plain text, kept as-is either way."""
    blocks = []
    for line in raw_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        ref = parse_reference(line)
        if ref:
            try:
                data = scrapers.fetch_bible(ref["book"], ref["chapter"], ref["start"], ref["end"])
                blocks.append(formatters.format_bible(data))
                continue
            except scrapers.ScrapeError:
                pass  # fall through to plain text below
        blocks.append(line)
    return "\n\n".join(blocks)


def format_ad_rule(raw_text: str) -> str:
    """No AI: pasted bulletin text where each item starts with a numbered
    header like "1 | 환영인사" / "1. 환영인사" / "1) 환영인사". Everything
    until the next header is that item's content, blank lines collapsed to
    at most one (paragraph break) and trimmed at both ends."""
    items = []
    current = None
    for raw_line in raw_text.split("\n"):
        line = raw_line.strip()
        m = _AD_HEADER_RE.match(line)
        if m:
            current = {"number": m.group(1), "title": m.group(2).strip(), "lines": []}
            items.append(current)
        elif current is not None:
            current["lines"].append(line)

    blocks = []
    for item in items:
        content_lines, prev_blank = [], True
        for ln in item["lines"]:
            if ln:
                content_lines.append(ln)
                prev_blank = False
            elif not prev_blank:
                content_lines.append("")
                prev_blank = True
        while content_lines and content_lines[-1] == "":
            content_lines.pop()
        content = "\n".join(content_lines)
        blocks.append(f"{item['number']}. {item['title']}\n{content}".rstrip())
    return "\n\n".join(blocks)
