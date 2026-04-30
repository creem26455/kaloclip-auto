"""Telegram notification — แจ้ง BossMhee"""

import os
import httpx


def send_message(text: str, log=print) -> bool:
    token = os.environ.get("TELEGRAM_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        log("⏭ Telegram: ไม่มี token/chat_id — ข้าม")
        return False

    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
            },
            timeout=15,
        )
        if resp.status_code == 200:
            return True
        log(f"❌ Telegram error: {resp.status_code} {resp.text[:200]}")
        return False
    except Exception as e:
        log(f"❌ Telegram error: {e}")
        return False


def notify_video_done(
    title: str,
    publish_id: str,
    duration: float,
    cost_usd: float,
    log=print,
    video_url: str = "",
    caption: str = "",
):
    lines = [
        f"✅ <b>วิดีโอใหม่พร้อม Post!</b>",
        f"",
        f"📝 <b>เรื่อง:</b> {title}",
        f"🎬 <b>ความยาว:</b> {duration:.0f}s",
        f"💰 <b>ต้นทุน:</b> ${cost_usd:.2f}",
    ]
    if video_url:
        lines.append(f"📥 <b>ดาวน์โหลด:</b> {video_url}")
    if caption:
        lines.append(f"")
        lines.append(f"📋 <b>Caption:</b>")
        lines.append(f"<code>{caption[:800]}</code>")
    if not video_url:
        lines.append(f"")
        lines.append(f"📱 TikTok → Creator Inbox → Publish")
    text = "\n".join(lines)
    return send_message(text, log)


def notify_error(title: str, error: str, log=print):
    text = (
        f"❌ <b>สร้างวิดีโอล้มเหลว</b>\n\n"
        f"📝 <b>เรื่อง:</b> {title}\n"
        f"⚠️ <b>Error:</b> <code>{error[:300]}</code>"
    )
    return send_message(text, log)
