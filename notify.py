"""ส่ง Telegram notification"""
import os
import httpx

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"


async def send_message(text: str):
    if not BOT_TOKEN or not CHAT_ID:
        return
    async with httpx.AsyncClient() as client:
        await client.post(f"{BASE}/sendMessage", json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        })


async def send_video(filepath: str, caption: str = ""):
    if not BOT_TOKEN or not CHAT_ID or not filepath:
        return
    async with httpx.AsyncClient(timeout=120) as client:
        with open(filepath, "rb") as f:
            await client.post(f"{BASE}/sendVideo", data={
                "chat_id": CHAT_ID,
                "caption": caption,
                "parse_mode": "HTML"
            }, files={"video": f})
