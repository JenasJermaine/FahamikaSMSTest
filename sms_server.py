import os
import urllib3
import requests as req
from flask import Flask, request, jsonify
from pipeline import process_message

# Disable SSL warnings for sandbox — AT sandbox cert verification fails
# in this environment due to network SSL interception
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

AT_USERNAME = os.getenv("AT_USERNAME", "sandbox")
AT_API_KEY = os.getenv("AT_API_KEY")
AT_SMS_URL = os.getenv(
    "AT_SMS_URL", "https://api.sandbox.africastalking.com/version1/messaging"
)

app = Flask(__name__)


@app.route("/incoming-sms", methods=["POST"])
def incoming_sms():
    """Receives inbound SMS forwarded by Africa's Talking."""
    if not AT_API_KEY:
        return jsonify({"error": "Missing environment variable: AT_API_KEY"}), 500

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()
    
    print(f"📥 Received: {data}")

    sender = data.get("from")
    message = data.get("text")

    if not sender or not message:
        return jsonify({"error": "Missing 'from' or 'text'"}), 400

    # Run the full Fahamika pipeline: match → fetch → simplify
    reply_text = process_message(message)

    # Trim to 1 SMS segment (160 chars) — later we'll handle multi-segment
    if len(reply_text) > 160:
        reply_text = reply_text[:157] + "..."

    try:
        # Direct REST call with verify=False — AT sandbox cert fails SSL
        # verification in this environment (network SSL interception)
        resp = req.post(
            AT_SMS_URL,
            headers={
                "apiKey": AT_API_KEY,
                "Accept": "application/json",
            },
            data={
                "username": AT_USERNAME,
                "to": sender,
                "message": reply_text,
            },
            verify=False,
            timeout=15,
        )
        result = resp.json()
        print(f"📤 Reply: {result}")
    except Exception as e:
        print(f"❌ Send failed: {e}")
        return jsonify({"error": "Failed to send reply"}), 500

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
