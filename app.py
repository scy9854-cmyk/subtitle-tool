import os
import sys

if getattr(sys, "frozen", False):
    # PyInstaller unpacks templates/static into a temp dir (sys._MEIPASS);
    # .env has to live beside the actual .exe instead, since that's the
    # only location that (a) persists across runs and (b) the user can
    # actually find and edit.
    ASSET_DIR = sys._MEIPASS
    APP_DIR = os.path.dirname(sys.executable)
else:
    ASSET_DIR = APP_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(APP_DIR, ".env"))

import anthropic
from flask import Flask, jsonify, render_template, request, Response

import ai_formatter
import formatters
import rule_formatter
import scrapers
from bible_books import BOOKS

app = Flask(__name__, root_path=ASSET_DIR)

APP_PASSWORD = os.environ.get("APP_PASSWORD")


@app.before_request
def require_password():
    if not APP_PASSWORD:
        return  # no password configured -> local-only convenience mode
    auth = request.authorization
    if not auth or auth.password != APP_PASSWORD:
        return Response(
            "인증이 필요합니다.", 401, {"WWW-Authenticate": 'Basic realm="subtitle-tool"'}
        )


@app.get("/")
def index():
    return render_template("index.html", books=[b[0] for b in BOOKS])


@app.post("/api/hymn")
def api_hymn():
    body = request.get_json(force=True)
    try:
        number = int(body.get("number"))
    except (TypeError, ValueError):
        return jsonify({"error": "장 번호를 숫자로 입력해주세요."}), 400

    try:
        hymn = scrapers.fetch_hymn(number)
        # ai_formatter.format_hymn is self-contained: it only calls the AI for
        # segments that don't fit a clean deterministic 2-line split, verifies
        # every returned line against the character limit, and falls back to
        # the mechanical wrap (no AI needed) for anything that fails or if
        # there's no API key at all.
        result = ai_formatter.format_hymn(hymn["verses"], hymn["refrain"])
        return jsonify({"title": hymn["title"], "result": result})
    except scrapers.ScrapeError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"처리 중 오류가 발생했습니다: {e}"}), 500


@app.post("/api/ccm/search")
def api_ccm_search():
    body = request.get_json(force=True)
    query = (body.get("query") or "").strip()
    if not query:
        return jsonify({"error": "검색어를 입력해주세요."}), 400

    try:
        results = scrapers.search_ccm(query)
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": f"검색 중 오류가 발생했습니다: {e}"}), 500


@app.post("/api/ccm/lyrics")
def api_ccm_lyrics():
    body = request.get_json(force=True)
    track_id = (body.get("trackId") or "").strip()
    if not track_id:
        return jsonify({"error": "trackId가 필요합니다."}), 400

    try:
        track = scrapers.fetch_ccm_lyrics(track_id)
        try:
            result = ai_formatter.format_ccm(track["title"], track["lyrics"])
            mode = "ai"
        except (RuntimeError, anthropic.APIError):
            result = rule_formatter.format_ccm_rule(track["lyrics"])
            mode = "rule"
        return jsonify({"title": track["title"], "result": result, "mode": mode})
    except scrapers.ScrapeError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"처리 중 오류가 발생했습니다: {e}"}), 500


@app.post("/api/ad")
def api_ad():
    body = request.get_json(force=True)
    image_b64 = body.get("image")
    media_type = body.get("mediaType") or "image/png"
    if not image_b64:
        return jsonify({"error": "이미지를 첨부해주세요."}), 400

    try:
        result = ai_formatter.format_ad(image_b64, media_type)
        return jsonify({"result": result, "mode": "ai"})
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"처리 중 오류가 발생했습니다: {e}"}), 500


@app.post("/api/ad/text")
def api_ad_text():
    body = request.get_json(force=True)
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "광고 텍스트를 붙여넣어주세요."}), 400

    try:
        result = rule_formatter.format_ad_rule(text)
        if not result:
            return jsonify({"error": '번호 형식("1 | 제목" 또는 "1. 제목")을 찾지 못했습니다.'}), 400
        return jsonify({"result": result, "mode": "rule"})
    except Exception as e:
        return jsonify({"error": f"처리 중 오류가 발생했습니다: {e}"}), 500


@app.post("/api/sermon")
def api_sermon():
    body = request.get_json(force=True)
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "설교 스크립트를 붙여넣어주세요."}), 400

    try:
        result = ai_formatter.format_sermon(text)
        mode = "ai"
    except (RuntimeError, anthropic.APIError):
        result = rule_formatter.format_sermon_rule(text)
        mode = "rule"
    except Exception as e:
        return jsonify({"error": f"처리 중 오류가 발생했습니다: {e}"}), 500
    return jsonify({"result": result, "mode": mode})


@app.post("/api/bible")
def api_bible():
    body = request.get_json(force=True)
    book = (body.get("book") or "").strip()
    try:
        chapter = int(body.get("chapter"))
        start = int(body.get("start"))
        end = int(body.get("end") or start)
    except (TypeError, ValueError):
        return jsonify({"error": "장/절은 숫자로 입력해주세요."}), 400

    try:
        data = scrapers.fetch_bible(book, chapter, start, end)
        result = formatters.format_bible(data)
        return jsonify({"result": result})
    except scrapers.ScrapeError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"처리 중 오류가 발생했습니다: {e}"}), 500


if __name__ == "__main__":
    # debug (auto-reload + interactive debugger) is only safe on localhost.
    # once a tunnel/public host exposes this port, set APP_PASSWORD in .env
    # and debug is automatically turned off.
    debug = APP_PASSWORD is None
    host = "0.0.0.0" if APP_PASSWORD else "127.0.0.1"
    app.run(debug=debug, host=host, port=5050)
