import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

from flask import Flask, jsonify, render_template, request, Response

import ai_formatter
import formatters
import rule_formatter
import scrapers
from bible_books import BOOKS

app = Flask(__name__, root_path=os.path.dirname(os.path.abspath(__file__)))

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
        try:
            result = ai_formatter.format_hymn(hymn["title"], hymn["verses"], hymn["refrain"])
            mode = "ai"
        except RuntimeError:
            result = rule_formatter.format_hymn_rule(hymn["verses"], hymn["refrain"])
            mode = "rule"
        return jsonify({"title": hymn["title"], "result": result, "mode": mode})
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
        except RuntimeError:
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


@app.post("/api/sermon")
def api_sermon():
    body = request.get_json(force=True)
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "설교 스크립트를 붙여넣어주세요."}), 400

    try:
        result = ai_formatter.format_sermon(text)
        return jsonify({"result": result, "mode": "ai"})
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"처리 중 오류가 발생했습니다: {e}"}), 500


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
