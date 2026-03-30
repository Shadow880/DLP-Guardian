from flask import Flask, request, jsonify
from engine.policy_engine import decide_on_text
from agent.logger import log_decision

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/check", methods=["POST"])
def check():
    data = request.get_json(force=True) or {}
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"error": "text is required"}), 400

    user = data.get("user", "unknown")
    source = data.get("source", "unknown")
    channel = data.get("channel", "unknown")

    decision = decide_on_text(text)

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