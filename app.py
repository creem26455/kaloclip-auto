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

app = Flask(__name__)

STATE_FILE = "/data/state.json"
COOKIES_FILE = "/data/session_cookies.json"
LOG_FILE = "/data/run.log"
OUTPUT_DIR = "/data/downloads"

# ใช้ local path ถ้าไม่มี /data (dev mode)
if not os.path.exists("/data"):
    STATE_FILE = "data/state.json"
    COOKIES_FILE = "data/session_cookies.json"
    LOG_FILE = "data/run.log"
    OUTPUT_DIR = "data/downloads"

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
    from flask import send_file
    path = os.path.join(OUTPUT_DIR, "debug_form.png")
    if os.path.exists(path):
        return send_file(path, mimetype="image/png")
    return "No screenshot yet", 404


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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
