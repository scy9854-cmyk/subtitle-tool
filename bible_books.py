from __future__ import annotations

BOOKS = [
    ("창세기", "gen"), ("출애굽기", "exo"), ("레위기", "lev"), ("민수기", "num"),
    ("신명기", "deu"), ("여호수아", "jos"), ("사사기", "jdg"), ("룻기", "rut"),
    ("사무엘상", "1sa"), ("사무엘하", "2sa"), ("열왕기상", "1ki"), ("열왕기하", "2ki"),
    ("역대상", "1ch"), ("역대하", "2ch"), ("에스라", "ezr"), ("느헤미야", "neh"),
    ("에스더", "est"), ("욥기", "job"), ("시편", "psa"), ("잠언", "pro"),
    ("전도서", "ecc"), ("아가", "sng"), ("이사야", "isa"), ("예레미야", "jer"),
    ("예레미야애가", "lam"), ("에스겔", "ezk"), ("다니엘", "dan"), ("호세아", "hos"),
    ("요엘", "jol"), ("아모스", "amo"), ("오바댜", "oba"), ("요나", "jnh"),
    ("미가", "mic"), ("나훔", "nam"), ("하박국", "hab"), ("스바냐", "zep"),
    ("학개", "hag"), ("스가랴", "zec"), ("말라기", "mal"), ("마태복음", "mat"),
    ("마가복음", "mrk"), ("누가복음", "luk"), ("요한복음", "jhn"), ("사도행전", "act"),
    ("로마서", "rom"), ("고린도전서", "1co"), ("고린도후서", "2co"), ("갈라디아서", "gal"),
    ("에베소서", "eph"), ("빌립보서", "php"), ("골로새서", "col"), ("데살로니가전서", "1th"),
    ("데살로니가후서", "2th"), ("디모데전서", "1ti"), ("디모데후서", "2ti"), ("디도서", "tit"),
    ("빌레몬서", "phm"), ("히브리서", "heb"), ("야고보서", "jas"), ("베드로전서", "1pe"),
    ("베드로후서", "2pe"), ("요한1서", "1jn"), ("요한2서", "2jn"), ("요한3서", "3jn"),
    ("유다서", "jud"), ("요한계시록", "rev"),
]

NAME_TO_CODE = {name: code for name, code in BOOKS}

# Common Korean abbreviations pastors actually write, mapped to the full
# (canonical) book name used everywhere else -- e.g. scrapers.fetch_bible
# only knows the full names in BOOKS.
ABBREVIATIONS = {
    "창": "창세기", "출": "출애굽기", "레": "레위기", "민": "민수기", "신": "신명기",
    "수": "여호수아", "삿": "사사기", "룻": "룻기",
    "삼상": "사무엘상", "삼하": "사무엘하", "왕상": "열왕기상", "왕하": "열왕기하",
    "대상": "역대상", "대하": "역대하", "스": "에스라", "느": "느헤미야", "에": "에스더",
    "욥": "욥기", "시": "시편", "잠": "잠언", "전": "전도서", "아": "아가",
    "사": "이사야", "렘": "예레미야", "애": "예레미야애가", "겔": "에스겔", "단": "다니엘",
    "호": "호세아", "욜": "요엘", "암": "아모스", "옵": "오바댜", "욘": "요나",
    "미": "미가", "나": "나훔", "합": "하박국", "습": "스바냐", "학": "학개",
    "슥": "스가랴", "말": "말라기",
    "마": "마태복음", "막": "마가복음", "눅": "누가복음", "요": "요한복음", "행": "사도행전",
    "롬": "로마서", "고전": "고린도전서", "고후": "고린도후서", "갈": "갈라디아서",
    "엡": "에베소서", "빌": "빌립보서", "골": "골로새서",
    "살전": "데살로니가전서", "살후": "데살로니가후서",
    "딤전": "디모데전서", "딤후": "디모데후서", "딛": "디도서", "몬": "빌레몬서",
    "히": "히브리서", "약": "야고보서", "벧전": "베드로전서", "벧후": "베드로후서",
    "요일": "요한1서", "요이": "요한2서", "요삼": "요한3서", "유": "유다서",
    "계": "요한계시록",
}

# Every recognizable spelling (full name first, then abbreviations), longest
# first so e.g. "요한복음" matches before the "요" abbreviation could.
ALL_BOOK_NAMES = sorted(
    {name for name, _ in BOOKS} | set(ABBREVIATIONS.keys()),
    key=len, reverse=True,
)


def resolve_book_name(name: str) -> str | None:
    """Map a full name or common abbreviation to the canonical full name."""
    if name in NAME_TO_CODE:
        return name
    return ABBREVIATIONS.get(name)
