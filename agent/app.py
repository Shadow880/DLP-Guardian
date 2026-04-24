from flask import Flask, request, jsonify
from flask_cors import CORS

from engine.policy_engine import decide_on_text
from engine.site_policy_engine import load_site_policies
from engine.user_context import get_active_user
from agent.logger import log_decision

app = Flask(__name__)
CORS(app)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/site-policies", methods=["GET"])
def site_policies():
    return jsonify({"sites": load_site_policies()}), 200


@app.route("/active-user", methods=["GET"])
def active_user():
    return jsonify({"active_user": get_active_user()}), 200


@app.route("/check", methods=["POST"])
def check():
    data = request.get_json(force=True) or {}
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"error": "text is required"}), 400

    user = data.get("user", "unknown")
    source = data.get("source", "unknown")
    channel = data.get("channel", "unknown")

    decision = decide_on_text(text, user=user, source=source)

    audit_payload = {
        "text": text,
        "user": user,
        "source": source,
        "channel": channel,
        "decision": decision
    }

    log_decision(audit_payload)

    return jsonify(audit_payload), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)