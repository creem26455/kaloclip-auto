"""
TikTok Automation — Flask Dashboard + TikTok OAuth + Cron
- Reuse ชื่อ Railway service เดิม → /data/tiktok_token.json ยังอยู่
- Cron ทุกวัน 09:00 (Asia/Bangkok)
"""

import asyncio
import json
import os
import sys
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template_string, request, jsonify, redirect

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from pipeline import run_one
import db

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    _HAS_SCHEDULER = True
except ImportError:
    _HAS_SCHEDULER = False

app = Flask(__name__)

# Use /data/ on Railway, local fallback
BASE = "/data" if os.path.exists("/data") else "data"
TOKEN_FILE = f"{BASE}/tiktok_token.json"
LOG_FILE = f"{BASE}/run.log"
OUTPUT_DIR = f"{BASE}/downloads"
TEMP_DIR = f"{BASE}/temp"

for d in [BASE, OUTPUT_DIR, TEMP_DIR]:
    Path(d).mkdir(parents=True, exist_ok=True)

TIKTOK_CLIENT_KEY = os.environ.get("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.environ.get("TIKTOK_CLIENT_SECRET", "")
TIKTOK_REDIRECT_URI = os.environ.get(
    "TIKTOK_REDIRECT_URI",
    "https://kaloclip-auto-production.up.railway.app/tiktok-callback",
)
TIKTOK_MODE = os.environ.get("TIKTOK_MODE", "INBOX")

running = False


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ========== Dashboard ==========
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>TikTok Automation</title>
  <meta charset="utf-8">
  <style>
    body { font-family: sans-serif; max-width: 800px; margin: 30px auto; padding: 20px; }
    .card { background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 10px 0; }
    .ok { color: green; } .err { color: red; }
    button { padding: 10px 20px; margin: 5px; cursor: pointer; }
    pre { background: #222; color: #0f0; padding: 10px; max-height: 400px; overflow: auto; }
  </style>
</head>
<body>
  <h1>🎬 TikTok Automation Dashboard</h1>

  <div class="card">
    <h3>📊 Status</h3>
    <p>TikTok: {% if tiktok_ok %}<span class="ok">✅ Connected</span>{% else %}<span class="err">❌ Not connected</span>{% endif %}</p>
    <p>Pending scripts: <b>{{ pending }}</b></p>
    <p>Running: {% if running %}<span class="err">🔄 Yes</span>{% else %}<span class="ok">⏸️ Idle</span>{% endif %}</p>
  </div>

  <div class="card">
    <h3>🎮 Actions</h3>
    <button onclick="run()">▶️ Run Now (1 video)</button>
    <a href="/tiktok-auth"><button>🔑 Connect TikTok</button></a>
    <button onclick="if(confirm('Disconnect TikTok?')) disconnect()">🔌 Disconnect</button>
  </div>

  <div class="card">
    <h3>📜 Logs (last 30)</h3>
    <pre>{{ logs }}</pre>
  </div>

<script>
  function run() {
    fetch('/run', {method: 'POST'}).then(r => r.json()).then(d => {
      alert(d.msg); setTimeout(() => location.reload(), 2000);
    });
  }
  function disconnect() {
    fetch('/tiktok-disconnect', {method: 'POST'}).then(() => location.reload());
  }
  setInterval(() => location.reload(), 30000);
</script>
</body>
</html>
"""


@app.route("/")
def index():
    logs = ""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, encoding="utf-8") as f:
            logs = "".join(f.readlines()[-30:])

    try:
        pending = db.count_pending()
    except Exception:
        pending = "N/A"

    return render_template_string(
        DASHBOARD_HTML,
        tiktok_ok=os.path.exists(TOKEN_FILE),
        pending=pending,
        running=running,
        logs=logs,
    )


@app.route("/run", methods=["POST"])
def run_now():
    global running
    if running:
        return jsonify({"ok": False, "msg": "กำลังรันอยู่..."})

    def _go():
        global running
        running = True
        try:
            run_one(TOKEN_FILE, OUTPUT_DIR, TEMP_DIR, log=log)
        except Exception as e:
            log(f"❌ Run error: {e}")
        finally:
            running = False

    threading.Thread(target=_go, daemon=True).start()
    return jsonify({"ok": True, "msg": "▶️ เริ่มรันแล้ว — เช็ค logs ใน 1-2 นาที"})


@app.route("/status")
def status():
    try:
        pending = db.count_pending()
    except Exception:
        pending = -1
    return jsonify({
        "running": running,
        "tiktok_connected": os.path.exists(TOKEN_FILE),
        "pending": pending,
    })


# ========== TikTok OAuth ==========

@app.route("/tiktok-auth")
def tiktok_auth():
    import secrets, urllib.parse
    state = secrets.token_urlsafe(16)
    scope = "video.upload,video.publish" if TIKTOK_MODE == "DIRECT_POST" else "video.upload"
    params = urllib.parse.urlencode({
        "client_key": TIKTOK_CLIENT_KEY,
        "response_type": "code",
        "scope": scope,
        "redirect_uri": TIKTOK_REDIRECT_URI,
        "state": state,
    })
    log(f"🔑 เริ่ม TikTok OAuth (scope={scope})...")
    return redirect(f"https://www.tiktok.com/v2/auth/authorize/?{params}")


@app.route("/tiktok-callback")
def tiktok_callback():
    code = request.args.get("code")
    error = request.args.get("error")
    if error:
        log(f"❌ TikTok OAuth error: {error}")
        return redirect("/?msg=tiktok_error")
    if not code:
        return "ไม่ได้รับ code จาก TikTok", 400

    import httpx
    try:
        resp = httpx.post(
            "https://open.tiktokapis.com/v2/oauth/token/",
            data={
                "client_key": TIKTOK_CLIENT_KEY,
                "client_secret": TIKTOK_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": TIKTOK_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        data = resp.json()
    except Exception as e:
        log(f"❌ TikTok token exchange error: {e}")
        return redirect("/?msg=tiktok_error")

    if "access_token" in data:
        token_data = {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", ""),
            "open_id": data.get("open_id", ""),
            "expires_in": data.get("expires_in", 0),
            "scope": data.get("scope", ""),
            "saved_at": datetime.now().isoformat(),
        }
        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        with open(TOKEN_FILE, "w") as f:
            json.dump(token_data, f, indent=2)
        log(f"✅ TikTok auth สำเร็จ! scope={token_data['scope']}")
        return redirect("/?msg=tiktok_ok")

    log(f"❌ TikTok token error: {data}")
    return redirect("/?msg=tiktok_error")


@app.route("/tiktok-disconnect", methods=["POST"])
def tiktok_disconnect():
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        log("🔌 ยกเลิก TikTok แล้ว")
    return jsonify({"ok": True})


@app.route("/tiktokESmb9IKmb0pmd1Qgizk0YU1E1QOFQJXa.txt")
def tiktok_verify():
    return ("tiktok-developers-site-verification=ESmb9IKmb0pmd1Qgizk0YU1E1QOFQJXa", 200,
            {"Content-Type": "text/plain"})


# ========== Cron ==========

def _cron_run():
    global running
    if running:
        log("⏭ Cron: กำลังรันอยู่ — ข้าม")
        return
    log("🕘 Cron: เริ่มรันประจำวัน")
    running = True
    try:
        run_one(TOKEN_FILE, OUTPUT_DIR, TEMP_DIR, log=log)
    except Exception as e:
        log(f"❌ Cron error: {e}")
    finally:
        running = False


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    if _HAS_SCHEDULER:
        scheduler = BackgroundScheduler(timezone="Asia/Bangkok")
        scheduler.add_job(
            _cron_run,
            CronTrigger(hour=9, minute=0, timezone="Asia/Bangkok"),
            id="daily",
            replace_existing=True,
        )
        scheduler.start()
        log("✅ Cron ตั้งแล้ว — รันทุกวัน 09:00 (Asia/Bangkok)")

    app.run(host="0.0.0.0", port=port)
