"""
Kaloclip Auto — Railway Web Dashboard
- หน้าเว็บให้ BossMhee วาง Cookies ครั้งแรก
- กด "Run Now" เพื่อสั่งทำคลิปทันที
- Cron รันอัตโนมัติทุกวัน
"""

import asyncio
import json
import os
import threading
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect

# APScheduler — daily cron ทุกวัน 09:00 (Asia/Bangkok)
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    _HAS_SCHEDULER = True
except ImportError:
    _HAS_SCHEDULER = False

app = Flask(__name__)

STATE_FILE = "/data/state.json"
COOKIES_FILE = "/data/session_cookies.json"
LOG_FILE = "/data/run.log"
OUTPUT_DIR = "/data/downloads"
TIKTOK_TOKEN_FILE = "/data/tiktok_token.json"

# ใช้ local path ถ้าไม่มี /data (dev mode)
if not os.path.exists("/data"):
    STATE_FILE = "data/state.json"
    COOKIES_FILE = "data/session_cookies.json"
    LOG_FILE = "data/run.log"
    OUTPUT_DIR = "data/downloads"
    TIKTOK_TOKEN_FILE = "data/tiktok_token.json"

# TikTok OAuth config (ใช้ Production key — ไม่มี sandbox restriction)
TIKTOK_CLIENT_KEY = os.environ.get("TIKTOK_CLIENT_KEY", "awai8imabqjlf4hd")
TIKTOK_CLIENT_SECRET = os.environ.get("TIKTOK_CLIENT_SECRET", "1owkHMTLgUAofa6DTP5zQvyuZCGu5Dah")
TIKTOK_REDIRECT_URI = os.environ.get(
    "TIKTOK_REDIRECT_URI",
    "https://kaloclip-auto-production.up.railway.app/tiktok-callback"
)

for d in [os.path.dirname(STATE_FILE), OUTPUT_DIR]:
    Path(d).mkdir(parents=True, exist_ok=True)

running = False  # ป้องกันรันซ้อน


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"index": 0, "products": [], "last_run": None, "last_video": None, "logs": []}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def append_log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


@app.route("/")
def index():
    state = load_state()
    has_cookies = os.path.exists(COOKIES_FILE) or bool(os.environ.get("KALO_TOKEN"))
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, encoding="utf-8") as f:
            logs = f.readlines()[-30:]  # แสดง 30 บรรทัดล่าสุด
    return render_template("index.html",
                           state=state,
                           has_cookies=has_cookies,
                           logs=logs,
                           running=running)


@app.route("/save-cookies", methods=["POST"])
def save_cookies_route():
    data = request.get_json()
    cookies_raw = data.get("cookies", "")
    if not cookies_raw:
        return jsonify({"ok": False, "msg": "ไม่มีข้อมูล cookies"})

    # แปลง cookie string → list of dicts สำหรับ Playwright
    cookies_list = []
    for part in cookies_raw.split(";"):
        part = part.strip()
        if "=" in part:
            name, _, value = part.partition("=")
            cookies_list.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": ".kalodata.com",
                "path": "/"
            })

    with open(COOKIES_FILE, "w") as f:
        json.dump(cookies_list, f)

    append_log("✅ บันทึก Cookies สำเร็จ")
    return jsonify({"ok": True, "msg": f"บันทึก {len(cookies_list)} cookies แล้ว"})


@app.route("/run", methods=["POST"])
def run_now():
    global running
    if running:
        return jsonify({"ok": False, "msg": "กำลังรันอยู่แล้ว..."})
    if not os.path.exists(COOKIES_FILE) and not os.environ.get("KALO_TOKEN"):
        return jsonify({"ok": False, "msg": "ยังไม่ได้ตั้งค่า Cookies!"})

    def _run():
        global running
        running = True
        try:
            asyncio.run(run_kaloclip())
        except Exception as e:
            append_log(f"❌ Error: {e}")
        finally:
            running = False

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({"ok": True, "msg": "เริ่มรันแล้ว! ดู log ด้านล่าง"})


@app.route("/logs")
def get_logs():
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, encoding="utf-8") as f:
            logs = f.readlines()[-50:]
    return jsonify({"logs": logs})


@app.route("/screenshot")
def debug_screenshot():
    from flask import send_file, request as req
    name = req.args.get("name", "debug_form")
    path = os.path.join(OUTPUT_DIR, f"{name}.png")
    if os.path.exists(path):
        return send_file(path, mimetype="image/png")
    return f"No screenshot: {name}", 404


@app.route("/status")
def status():
    state = load_state()
    return jsonify({"running": running, "state": state})


@app.route("/set-index", methods=["POST"])
def set_index():
    """ตั้งค่า index สินค้าที่จะทำต่อ (0=Top1, 1=Top2, ...)"""
    data = request.get_json() or {}
    idx = data.get("index", 0)
    state = load_state()
    state["index"] = int(idx)
    save_state(state)
    product_num = int(idx) + 1
    append_log(f"✅ ตั้ง index เป็น {idx} (สินค้า #{product_num})")
    return jsonify({"ok": True, "msg": f"จะเริ่มจากสินค้า #{product_num} ในรอบถัดไป"})


# ===== TikTok OAuth =====

@app.route("/tiktok-auth")
def tiktok_auth():
    import secrets, urllib.parse
    state = secrets.token_urlsafe(16)
    params = urllib.parse.urlencode({
        "client_key": TIKTOK_CLIENT_KEY,
        "response_type": "code",
        "scope": "video.upload",
        "redirect_uri": TIKTOK_REDIRECT_URI,
        "state": state,
    })
    auth_url = f"https://www.tiktok.com/v2/auth/authorize/?{params}"
    append_log(f"🔑 เริ่ม TikTok OAuth...")
    return redirect(auth_url)


@app.route("/tiktok-callback")
def tiktok_callback():
    code = request.args.get("code")
    error = request.args.get("error")
    if error:
        append_log(f"❌ TikTok OAuth error: {error}")
        return redirect("/?msg=tiktok_error")
    if not code:
        return "ไม่ได้รับ code จาก TikTok", 400

    # Exchange code → access_token
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
        append_log(f"❌ TikTok token exchange error: {e}")
        return redirect("/?msg=tiktok_error")

    if "access_token" in data:
        token_data = {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", ""),
            "open_id": data.get("open_id", ""),
            "expires_in": data.get("expires_in", 0),
            "refresh_expires_in": data.get("refresh_expires_in", 0),
            "scope": data.get("scope", ""),
            "saved_at": datetime.now().isoformat(),
        }
        os.makedirs(os.path.dirname(TIKTOK_TOKEN_FILE), exist_ok=True)
        with open(TIKTOK_TOKEN_FILE, "w") as f:
            json.dump(token_data, f, indent=2)
        append_log(f"✅ TikTok auth สำเร็จ! scope={token_data['scope']}")
        return redirect("/?msg=tiktok_ok")
    else:
        append_log(f"❌ TikTok token error: {data}")
        return redirect("/?msg=tiktok_error")


@app.route("/tiktok-status")
def tiktok_status():
    has_token = os.path.exists(TIKTOK_TOKEN_FILE)
    token_data = {}
    if has_token:
        with open(TIKTOK_TOKEN_FILE) as f:
            token_data = json.load(f)
    return jsonify({"connected": has_token, "open_id": token_data.get("open_id", ""), "saved_at": token_data.get("saved_at", "")})


@app.route("/tiktok-disconnect", methods=["POST"])
def tiktok_disconnect():
    if os.path.exists(TIKTOK_TOKEN_FILE):
        os.remove(TIKTOK_TOKEN_FILE)
        append_log("🔌 ยกเลิกการเชื่อมต่อ TikTok แล้ว")
    return jsonify({"ok": True})


# ===== TikTok URL Prefix Verification =====

@app.route("/tiktokESmb9IKmb0pmd1Qgizk0YU1E1QOFQJXa.txt")
def tiktok_verification():
    """TikTok URL prefix verification file"""
    return "tiktok-developers-site-verification=ESmb9IKmb0pmd1Qgizk0YU1E1QOFQJXa", 200, {
        "Content-Type": "text/plain"
    }


# ===== Kaloclip Logic =====

async def run_kaloclip():
    from kaloclip import KaloclipBot
    bot = KaloclipBot(
        cookies_file=COOKIES_FILE,
        state_file=STATE_FILE,
        output_dir=OUTPUT_DIR,
        log_fn=append_log
    )
    await bot.run()


def _cron_run():
    """เรียกจาก APScheduler ทุกวัน 09:00 Asia/Bangkok"""
    global running
    if running:
        append_log("⏭ Cron: กำลังรันอยู่แล้ว ข้ามรอบนี้")
        return
    append_log("🕘 Cron: เริ่มรันประจำวัน")
    running = True
    try:
        asyncio.run(run_kaloclip())
    except Exception as e:
        append_log(f"❌ Cron error: {e}")
    finally:
        running = False


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    # ตั้ง APScheduler (ถ้ามี package)
    if _HAS_SCHEDULER:
        scheduler = BackgroundScheduler(timezone="Asia/Bangkok")
        scheduler.add_job(
            _cron_run,
            CronTrigger(hour=9, minute=0, timezone="Asia/Bangkok"),
            id="daily_kaloclip",
            replace_existing=True,
        )
        scheduler.start()
        append_log("✅ Daily cron ตั้งแล้ว — รันทุกวัน 09:00 (Asia/Bangkok)")
    else:
        append_log("⚠️ APScheduler ไม่ได้ติดตั้ง — ไม่มี daily cron")

    app.run(host="0.0.0.0", port=port)
