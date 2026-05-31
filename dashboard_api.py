# dashboard_api.py - Dashboard uchun Flask REST API

import json
import logging
from functools import wraps
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from config import DASHBOARD_SECRET_KEY
import database as db

logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="dashboard_dist", static_url_path="")
CORS(app)


# ── Oddiy API kalit himoyasi ───────────────────────────────────────────────────

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if key != DASHBOARD_SECRET_KEY:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


# ── Endpointlar ───────────────────────────────────────────────────────────────

@app.route("/api/stats", methods=["GET"])
@require_api_key
def get_stats():
    data = db.get_dashboard_data()
    return jsonify(data)


@app.route("/api/users", methods=["GET"])
@require_api_key
def get_users():
    with db.get_connection() as conn:
        users = conn.execute(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT 100"
        ).fetchall()
    return jsonify([dict(u) for u in users])


@app.route("/api/videos", methods=["GET"])
@require_api_key
def get_videos():
    with db.get_connection() as conn:
        videos = conn.execute("""
            SELECT vl.*, u.telegram_username, u.instagram_username
            FROM video_logs vl
            LEFT JOIN users u ON u.telegram_id = vl.telegram_id
            ORDER BY vl.created_at DESC LIMIT 50
        """).fetchall()
    return jsonify([dict(v) for v in videos])


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


# ── Statik fayllar (dashboard frontend) ───────────────────────────────────────

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_dashboard(path):
    return app.send_static_file("index.html") if path == "" \
        else send_from_directory(app.static_folder, path)


def run_dashboard(host="0.0.0.0", port=5000):
    logger.info("🌐 Dashboard API: http://%s:%s", host, port)
    app.run(host=host, port=port, debug=False, use_reloader=False)
