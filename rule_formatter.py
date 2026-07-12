"""Deterministic (non-AI) fallback formatters.

Hymn verses are word-wrapped to a fixed max characters per line (screen
readability limit) and grouped two lines at a time. CCM structure labeling
is a best-effort heuristic based on exact repeated line-blocks, so it can
miss choruses whose wording varies slightly between repeats, and it cannot
reliably detect a Bridge.
"""


MAX_LINE_CHARS = 18  # screen-calibrated: longer lines overflow the subtitle slide


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


def format_hymn_rule(verses: list, refrain) -> str:
    blocks = []
    for i, v in enumerate(verses, 1):
        wrapped = wrap_line(v, prefix=f"{i}. ")
        blocks.extend(pair_lines(wrapped))
        if refrain:
            blocks.extend(pair_lines(wrap_line(refrain)))
    return "\n\n".join(blocks)


def _find_chorus_block(lines: list):
    n = len(lines)
    max_size = min(12, n // 2)
    for size in range(max_size, 1, -1):
        seen = {}
        for start in range(n - size + 1):
            block = tuple(lines[start:start + size])
            if block in seen:
                return list(block), size
            seen[block] = start
    return None, 0


def _find_occurrences(lines: list, block: list):
    size = len(block)
    n = len(lines)
    starts = []
    i = 0
    while i <= n - size:
        if lines[i:i + size] == block:
            starts.append(i)
            i += size
        else:
            i += 1
    return starts


def group_lines(lines: list) -> str:
    """Join a section's raw lyric lines into 2-line groups separated by a blank line.

    Raw lines are never split, only merged: if a section has an odd number of
    lines, exactly one adjacent pair is joined onto a single display line —
    whichever adjacent pair keeps the two resulting lines closest in length —
    so a leftover line never ends up alone in its own tiny group.
    """
    lines = [ln for ln in lines if ln.strip()]
    n = len(lines)
    if n == 0:
        return ""

    if n % 2 == 1 and n > 1:
        best_seq, best_score = lines, None
        for i in range(n - 1):
            merged = f"{lines[i]} {lines[i + 1]}"
            seq = lines[:i] + [merged] + lines[i + 2:]
            pairs = [(seq[j], seq[j + 1]) for j in range(0, len(seq), 2)]
            score = sum(abs(len(a) - len(b)) for a, b in pairs)
            if best_score is None or score < best_score:
                best_score, best_seq = score, seq
        lines = best_seq

    if len(lines) % 2 == 0:
        groups = ["\n".join(lines[i:i + 2]) for i in range(0, len(lines), 2)]
    else:
        groups = ["\n".join(lines[i:i + 2]) if i + 1 < len(lines) else lines[i]
                   for i in range(0, len(lines), 2)]
    return "\n\n".join(groups)


def format_ccm_rule(lyrics: str) -> str:
    """Each unique section (Verse/Chorus/Bridge) is emitted only once, even if
    it repeats several times in the song, since this is a subtitle source and
    a repeated section reuses the same slide."""
    lines = [ln.strip() for ln in lyrics.split("\n") if ln.strip()]
    chorus_block, size = _find_chorus_block(lines)

    segments = []
    seen_blocks = set()
    verse_count = 0

    def flush_verse(buf):
        nonlocal verse_count
        key = tuple(buf)
        if not buf or key in seen_blocks:
            return
        seen_blocks.add(key)
        verse_count += 1
        segments.append((f"Verse {verse_count}", buf))

    if chorus_block:
        starts = set(_find_occurrences(lines, chorus_block))
        chorus_included = False
        verse_buffer = []
        i, n = 0, len(lines)
        while i < n:
            if i in starts:
                flush_verse(verse_buffer)
                verse_buffer = []
                if not chorus_included:
                    segments.append(("Chorus", lines[i:i + size]))
                    seen_blocks.add(tuple(lines[i:i + size]))
                    chorus_included = True
                i += size
            else:
                verse_buffer.append(lines[i])
                i += 1

        key = tuple(verse_buffer)
        if verse_buffer and key not in seen_blocks:
            has_chorus = any(label == "Chorus" for label, _ in segments)
            if len(verse_buffer) <= 4 and has_chorus:
                seen_blocks.add(key)
                segments.append(("Bridge", verse_buffer))
            else:
                flush_verse(verse_buffer)
    else:
        chunk = 4
        for idx in range(0, len(lines), chunk):
            flush_verse(lines[idx:idx + chunk])

    out_blocks = [f"{label}\n{group_lines(seg_lines)}" for label, seg_lines in segments]
    return "\n\n".join(out_blocks)
