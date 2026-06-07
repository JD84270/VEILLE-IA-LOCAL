import sqlite3
from pathlib import Path
from flask import Flask, request, jsonify, make_response

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "veille.db"

ALLOWED_STATUS = {"new", "viewed", "in_progress", "done", "archived"}
ALLOWED_FEEDBACK = {None, "relevant", "not_relevant", "tested", "implemented", "archived"}

app = Flask(__name__)


def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.after_request
def after_request(response):
    return add_cors_headers(response)


@app.route("/update-status", methods=["POST", "OPTIONS"])
def update_status():
    if request.method == "OPTIONS":
        return add_cors_headers(make_response("", 204))

    data = request.get_json(force=True)

    item_id = data.get("id")
    status = data.get("status")
    feedback = data.get("feedback")

    if not item_id or status not in ALLOWED_STATUS:
        return jsonify({"ok": False, "error": "Invalid status request"}), 400

    if feedback not in ALLOWED_FEEDBACK:
        return jsonify({"ok": False, "error": "Invalid feedback request"}), 400

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        UPDATE items
        SET status = ?, user_feedback = ?
        WHERE id = ?
        """,
        (status, feedback, item_id)
    )
    conn.commit()
    conn.close()

    return jsonify({
        "ok": True,
        "id": item_id,
        "status": status,
        "feedback": feedback
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
   