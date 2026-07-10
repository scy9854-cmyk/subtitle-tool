import re
import requests
from bs4 import BeautifulSoup

from bible_books import NAME_TO_CODE

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


class ScrapeError(Exception):
    pass


def fetch_hymn(number: int) -> dict:
    """Scrape a hymn's title, numbered verses, and refrain from hbible.co.kr."""
    url = f"https://www.hbible.co.kr/hb/hymn/view/{number}/"
    res = requests.get(url, headers=HEADERS, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    title_el = soup.select_one("#id_hymn_title h4")
    if not title_el:
        raise ScrapeError(f"{number}장을 찾을 수 없습니다.")
    title = re.sub(r"\s+", " ", title_el.get_text(strip=True))

    body = soup.select_one(".textSpacing")
    if not body:
        raise ScrapeError(f"{number}장 가사 본문을 찾을 수 없습니다.")

    for br in body.find_all("br"):
        br.replace_with("\n")
    raw_lines = [ln.strip() for ln in body.get_text().split("\n")]
    raw_lines = [ln for ln in raw_lines if ln]

    verses = []
    refrain = None
    for line in raw_lines:
        if line == "아멘":
            continue
        m = re.match(r"^(\d+)\.\s*(.+)$", line)
        if m:
            verses.append(m.group(2).strip())
            continue
        m = re.match(r"^<?후렴>?\s*(.*)$", line)
        if m:
            refrain = m.group(1).strip()
            continue
        # hymn with a single unlabeled verse (e.g. no numbering, no refrain)
        if not verses and not refrain:
            verses.append(line)

    if not verses:
        raise ScrapeError(f"{number}장 가사를 파싱하지 못했습니다.")

    return {"number": number, "title": title, "verses": verses, "refrain": refrain}


def search_ccm(query: str) -> list:
    """Search Bugs Music lyrics search and return a list of candidate tracks."""
    url = "https://music.bugs.co.kr/search/lyrics"
    res = requests.get(url, headers=HEADERS, params={"q": query}, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    results = []
    for row in soup.select("tr[trackid]"):
        track_id = row.get("trackid")
        title_el = row.select_one("p.title a")
        artist_el = row.select_one("p.artist a")
        if not track_id or not title_el:
            continue
        results.append({
            "trackId": track_id,
            "title": title_el.get_text(strip=True),
            "artist": artist_el.get_text(strip=True) if artist_el else "",
        })
        if len(results) >= 15:
            break
    return results


def fetch_ccm_lyrics(track_id: str) -> dict:
    """Scrape raw (unstructured) lyrics text for a Bugs Music track."""
    url = f"https://music.bugs.co.kr/track/{track_id}"
    res = requests.get(url, headers=HEADERS, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    title_el = soup.select_one("header.pgTitle h1") or soup.select_one("title")
    title = title_el.get_text(strip=True) if title_el else track_id

    xmp = soup.select_one("div.lyricsContainer xmp")
    if not xmp:
        raise ScrapeError("가사를 찾을 수 없습니다 (미등록 곡일 수 있습니다).")
    lyrics = xmp.get_text().strip()
    if not lyrics:
        raise ScrapeError("가사가 비어 있습니다.")
    return {"trackId": track_id, "title": title, "lyrics": lyrics}


def fetch_bible(book_name: str, chapter: int, start: int, end: int) -> dict:
    """Scrape a full chapter (개역개정) from bskorea.or.kr and slice to [start, end]."""
    code = NAME_TO_CODE.get(book_name)
    if not code:
        raise ScrapeError(f"'{book_name}'은(는) 알 수 없는 책 이름입니다.")

    url = "https://www.bskorea.or.kr/bible/korbibReadpage.php"
    params = {"version": "GAE", "book": code, "chap": chapter, "sec": 1}
    res = requests.get(url, headers=HEADERS, params=params, timeout=10)
    res.raise_for_status()
    res.encoding = "utf-8"

    verse_pattern = re.compile(
        r'<span class="number">\s*(\d+)\s*(?:&nbsp;)*\s*</span>(.*?)</font></span>',
        re.DOTALL,
    )
    matches = verse_pattern.findall(res.text)
    if not matches:
        raise ScrapeError(f"{book_name} {chapter}장 본문을 찾을 수 없습니다.")

    verses = {}
    for num_str, html_fragment in matches:
        text = BeautifulSoup(html_fragment, "html.parser").get_text()
        text = re.sub(r"\s+", " ", text).strip()
        verses[int(num_str)] = text

    selected = []
    for v in range(start, end + 1):
        if v in verses:
            selected.append((v, verses[v]))

    if not selected:
        raise ScrapeError(f"{book_name} {chapter}장에 {start}-{end}절이 없습니다.")

    return {"book": book_name, "chapter": chapter, "start": start, "end": end, "verses": selected}
