from __future__ import annotations

import json
import os
import anthropic

import rule_formatter
import scrapers
import formatters
from bible_books import BOOKS

MODEL = "claude-sonnet-5"

HYMN_SYSTEM_PROMPT = """당신은 한국 교회의 예배 자막(이지워십) 담당자를 돕는 도우미입니다.
찬송가 각 절을 자막 화면에 보기 좋게 여러 줄로 나눠주세요. split_hymn 도구를 호출해서 결과를 알려주세요.

규칙:
1. 자연스러운 어순/구절 단위로 줄을 나눕니다 — 조사나 어미, 의미 단위가 자연스럽게 끊기는 지점에서 나누고, 한 단어의 중간에서 끊지 않습니다.
2. 한 줄은 공백 포함 20자를 넘지 않게 하되, 15자 안팎을 목표로 삼으세요. 무조건 짧게 쪼개지 말고, 다음 의미 단위까지 넣었을 때 20자를 넘지 않는다면 최대한 붙이세요 — 너무 잦은 줄바꿈은 오히려 부자연스럽습니다.
3. 원문 내용을 빠짐없이 그대로 옮기고, 단어를 추가하거나 빼지 마세요."""

HYMN_TOOL = {
    "name": "split_hymn",
    "description": "각 절을 자연스러운 어순 단위의 여러 줄로 나눠 반환합니다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "verses": {
                "type": "array",
                "description": "입력받은 절 순서와 개수를 그대로 따릅니다.",
                "items": {
                    "type": "object",
                    "properties": {
                        "lines": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["lines"],
                },
            },
        },
        "required": ["verses"],
    },
}

CCM_SYSTEM_PROMPT = """당신은 한국 교회의 예배 자막(이지워십) 담당자를 돕는 도우미입니다.
CCM 가사는 절 구분이 되어 있지 않은 경우가 많습니다. 주어진 원문 가사를 의미 단위로 분석해서
Verse 1, Verse 2, Pre-Chorus, Chorus, Bridge, Outro 등 곡 구조를 판단하고,
structure_lyrics 도구를 호출해서 결과를 알려주세요.

규칙:
1. 각 섹션의 lines에는 그 섹션에 해당하는 원문 가사 줄들을 원래 순서 그대로 넣습니다. 줄을 2줄/4줄 단위로 미리 묶거나 나누지 마세요 — 원문의 한 줄 = 배열의 한 항목입니다.
2. 이 결과는 자막 소스이므로, 노래에서 같은 Chorus(또는 같은 Verse)가 여러 번 반복되더라도 딱 한 번만 섹션으로 포함합니다. 처음 등장하는 곳에서만 넣고, 이후 반복되는 곳은 통째로 생략합니다.
3. sections 배열의 순서는 곡에 실제로 처음 등장하는 순서를 따릅니다."""

CCM_TOOL = {
    "name": "structure_lyrics",
    "description": "분석한 곡 구조를 섹션별로 반환합니다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {
                            "type": "string",
                            "description": "예: Verse 1, Chorus, Bridge, Outro",
                        },
                        "lines": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "이 섹션에 속하는 원문 가사 줄들 (원래 순서대로, 나누지 않음)",
                        },
                    },
                    "required": ["label", "lines"],
                },
            }
        },
        "required": ["sections"],
    },
}


AD_SYSTEM_PROMPT = """당신은 한국 교회의 주보 광고/공지 이미지를 자막 소스로 옮기는 도우미입니다.
주어진 이미지(주보의 광고란을 캡처한 사진)에는 번호가 매겨진 광고/공지가 하나 이상 들어있습니다.
이미지를 위에서 아래로 읽고 extract_announcements 도구를 호출해서 각 항목을 순서대로 알려주세요.

규칙:
1. number에는 이미지에 표시된 번호(1, 2, 3...)를 그대로 숫자로 넣습니다.
2. title에는 그 항목의 제목만 넣습니다 (번호나 구분기호는 제외, 예: "환영인사").
3. content에는 그 항목의 본문 내용을 그대로 옮깁니다. 장식용 기호나 로고는 빼고 핵심 텍스트만 담되, 이미지에서 문단이 빈 줄로 나뉘어 있으면 content 안에서도 그 문단 사이를 빈 줄로 유지합니다.
4. 이미지에 있는 항목을 하나도 빠짐없이, 번호 순서 그대로 모두 포함합니다. 없는 내용을 추측해서 채우지 않습니다."""

AD_TOOL = {
    "name": "extract_announcements",
    "description": "이미지에서 읽어낸 번호별 광고/공지 목록을 순서대로 반환합니다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "number": {"type": "integer", "description": "이미지에 표시된 번호"},
                        "title": {"type": "string", "description": "항목 제목 (번호 제외)"},
                        "content": {"type": "string", "description": "항목 본문 내용"},
                    },
                    "required": ["number", "title", "content"],
                },
            }
        },
        "required": ["items"],
    },
}


SERMON_SYSTEM_PROMPT = """당신은 한국 교회의 설교 원고를 예배 자막 소스로 정리하는 도우미입니다.
목사님이 작성한 설교 스크립트 원문을 줄 단위로 분석해서 segment_sermon 도구를 호출해주세요.

원문은 이미 줄바꿈으로 구분되어 있습니다. 그 줄 구분을 그대로 존중하세요 — 원문의 한 줄(빈 줄 제외) = 결과의 한 항목입니다. 문장을 임의로 합치거나 다시 나누지 마세요.

각 줄을 다음 세 종류 중 하나로 분류하세요:
1. "text" — 일반 설교 본문 줄
2. "image" — '#'으로 시작하는 이미지 자료 표시 줄
3. "reference" — 그 줄이 다른 설명 없이 온전히 성경 구절 참조만 담고 있는 경우 (예: "요한복음 3:16", "롬 8:28-30", "삼상 15장"). 이 경우 book에는 아래 정식 책 이름 목록 중 정확히 일치하는 이름을, chapter에는 장 번호를, startVerse/endVerse에는 절 범위를 넣습니다. 특정 절 없이 장 전체를 가리키면 startVerse=1, endVerse=999로 설정하세요. 절이 하나면 startVerse와 endVerse를 같은 값으로 하세요.

모든 항목에 content 필드를 넣어서 원문 그 줄의 텍스트를 그대로 보존하세요 (reference로 분류한 경우에도 원문 참조 표기를 content에 넣어두면, 나중에 조회가 실패했을 때 대체용으로 씁니다).

정식 책 이름 목록: {book_list}

빈 줄은 결과에 포함하지 마세요."""

SERMON_TOOL = {
    "name": "segment_sermon",
    "description": "설교 원고를 줄 단위로 분류해서 순서대로 반환합니다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "segments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["text", "image", "reference"]},
                        "content": {"type": "string", "description": "원문 그 줄의 텍스트"},
                        "book": {"type": "string", "description": "reference일 때: 정식 책 이름"},
                        "chapter": {"type": "integer", "description": "reference일 때: 장 번호"},
                        "startVerse": {"type": "integer", "description": "reference일 때: 시작 절"},
                        "endVerse": {"type": "integer", "description": "reference일 때: 끝 절"},
                    },
                    "required": ["type", "content"],
                },
            }
        },
        "required": ["segments"],
    },
}


def _client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY가 설정되어 있지 않습니다. .env 파일에 키를 추가해주세요."
        )
    return anthropic.Anthropic(api_key=api_key)


def format_hymn(verses: list, refrain) -> str:
    """Each verse (and the refrain) is a list of the hymn site's own natural
    <br/>-separated segments. A pure character-balance split can land on a
    grammatically awkward break (e.g. splitting "팔에 / 안기세" apart) even
    when it's well within the length limit, so every segment -- verse and
    refrain alike -- is sent to the AI for a natural word-order split in one
    batched call. Each returned line is re-verified against MAX_LINE_CHARS;
    any segment that fails validation, or any failure of the AI call itself,
    falls back to the deterministic balance/wrap split for that segment only."""
    # (kind, verse_idx, seg_idx, text, prefix) -- one entry per natural segment,
    # verse and refrain segments flattened into a single ordered list for one AI call.
    segments = []
    for i, segs in enumerate(verses):
        for j, seg in enumerate(segs):
            prefix = f"{i + 1}. " if j == 0 else ""
            segments.append(("verse", i, j, seg, prefix))
    if refrain:
        for j, seg in enumerate(refrain):
            segments.append(("refrain", None, j, seg, ""))

    ai_results = {}
    try:
        client = _client()
        user_content = "\n".join(f"{idx}: {text}" for idx, (_, _, _, text, _) in enumerate(segments))
        resp = client.messages.create(
            model=MODEL,
            max_tokens=4000,
            thinking={"type": "disabled"},
            system=HYMN_SYSTEM_PROMPT,
            tools=[HYMN_TOOL],
            tool_choice={"type": "tool", "name": "split_hymn"},
            messages=[{"role": "user", "content": user_content}],
        )
        tool_use = next(b for b in resp.content if getattr(b, "type", None) == "tool_use")
        data = tool_use.input
        if isinstance(data, str):
            data = json.loads(data)
        ai_list = data.get("verses") or []
        for idx, item in enumerate(ai_list):
            if idx >= len(segments):
                break
            _, _, _, _, prefix = segments[idx]
            candidate = [ln.strip() for ln in (item.get("lines") or []) if ln and ln.strip()]
            if candidate:
                lines = [f"{prefix}{candidate[0]}"] + candidate[1:]
                if all(len(ln) <= rule_formatter.MAX_LINE_CHARS for ln in lines):
                    ai_results[idx] = lines
    except Exception:
        pass  # no key, or any AI/parsing failure -- mechanical fallback covers every segment

    verse_blocks = {}
    refrain_blocks = []
    for idx, (kind, vi, si, seg, prefix) in enumerate(segments):
        mechanical = rule_formatter.split_two_lines(seg, prefix=prefix) or rule_formatter.wrap_line(seg, prefix=prefix)
        ai_lines = ai_results.get(idx)
        # only prefer the AI's break points when they don't fragment the
        # segment into more lines than the deterministic packing would --
        # a "natural" split that uses more, shorter lines than necessary is
        # exactly the over-fragmentation this whole thing is meant to avoid.
        lines = ai_lines if ai_lines and len(ai_lines) <= len(mechanical) else mechanical
        groups = rule_formatter.pair_lines(lines)
        if kind == "verse":
            verse_blocks.setdefault(vi, []).extend(groups)
        else:
            refrain_blocks.extend(groups)

    blocks = []
    for i in range(len(verses)):
        blocks.extend(verse_blocks.get(i, []))
        blocks.extend(refrain_blocks)

    return "\n\n".join(blocks)


def format_ccm(title: str, lyrics: str) -> str:
    user_content = f"[{title}]\n\n{lyrics}"

    client = _client()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        thinking={"type": "disabled"},
        system=CCM_SYSTEM_PROMPT,
        tools=[CCM_TOOL],
        tool_choice={"type": "tool", "name": "structure_lyrics"},
        messages=[{"role": "user", "content": user_content}],
    )

    tool_use = next(b for b in resp.content if getattr(b, "type", None) == "tool_use")
    sections = tool_use.input.get("sections", [])
    if isinstance(sections, str):
        # occasionally the model double-encodes this field as a JSON string
        parsed = json.loads(sections)
        sections = parsed.get("sections", parsed) if isinstance(parsed, dict) else parsed

    blocks = [
        f"{sec['label']}\n" + "\n".join(ln.strip() for ln in sec["lines"] if ln.strip())
        for sec in sections
        if sec.get("lines")
    ]
    return "\n\n".join(blocks)


def format_ad(image_b64: str, media_type: str) -> str:
    client = _client()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        thinking={"type": "disabled"},
        system=AD_SYSTEM_PROMPT,
        tools=[AD_TOOL],
        tool_choice={"type": "tool", "name": "extract_announcements"},
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": image_b64},
                },
                {"type": "text", "text": "이 이미지에서 번호별 광고/공지를 모두 순서대로 추출해주세요."},
            ],
        }],
    )

    tool_use = next(b for b in resp.content if getattr(b, "type", None) == "tool_use")
    items = tool_use.input.get("items", [])
    if isinstance(items, str):
        # occasionally the model double-encodes this field as a JSON string
        parsed = json.loads(items)
        items = parsed.get("items", parsed) if isinstance(parsed, dict) else parsed

    blocks = [
        f"{item['number']}. {(item.get('title') or '').strip()}\n{(item.get('content') or '').strip()}"
        for item in items
    ]
    return "\n\n".join(blocks)


def format_sermon(raw_text: str) -> str:
    book_list = ", ".join(name for name, _ in BOOKS)
    system = SERMON_SYSTEM_PROMPT.format(book_list=book_list)

    client = _client()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        thinking={"type": "disabled"},
        system=system,
        tools=[SERMON_TOOL],
        tool_choice={"type": "tool", "name": "segment_sermon"},
        messages=[{"role": "user", "content": raw_text}],
    )

    tool_use = next(b for b in resp.content if getattr(b, "type", None) == "tool_use")
    segments = tool_use.input.get("segments", [])
    if isinstance(segments, str):
        # occasionally the model double-encodes this field as a JSON string
        parsed = json.loads(segments)
        segments = parsed.get("segments", parsed) if isinstance(parsed, dict) else parsed

    blocks = []
    for seg in segments:
        content = (seg.get("content") or "").strip()
        if seg.get("type") == "reference" and seg.get("book") and seg.get("chapter"):
            try:
                start = int(seg.get("startVerse") or 1)
                end = int(seg.get("endVerse") or start)
                data = scrapers.fetch_bible(seg["book"], int(seg["chapter"]), start, end)
                blocks.append(formatters.format_bible(data))
                continue
            except Exception:
                pass  # fall back to the raw reference text below
        if content:
            blocks.append(content)

    return "\n\n".join(blocks)
