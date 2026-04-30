"""
Grok Imagine API Client
- Endpoint: https://api.x.ai/v1/videos/generations
- Model: grok-imagine-video (default 8s, 480p, with native audio)
- Async job: submit → poll status → download mp4
"""

import os
import time
import httpx
from pathlib import Path

GROK_BASE_URL = "https://api.x.ai/v1"

# ราคา (จาก usage.cost_in_usd_ticks ÷ 10^10)
COST_PER_8S_CLIP = 0.40  # ~$0.40 per 8-second clip


def _get_key() -> str:
    key = os.environ.get("XAI_API_KEY", "")
    if not key:
        raise RuntimeError("XAI_API_KEY ไม่ได้ตั้งค่า")
    return key


def submit_video(
    prompt: str,
    duration: int | None = None,
    resolution: str | None = None,
    image_url: str | None = None,
) -> str:
    """
    ส่ง request สร้างวิดีโอ — return request_id (async)

    Args:
        prompt: text description
        duration: 8 (default), 15
        resolution: 480p (default), 720p
        image_url: URL ของรูป reference (เปลี่ยนเป็น Image-to-Video mode)
                   ใช้ตอนอยากให้ขวดสินค้า/วัตถุในคลิปเหมือนของจริง
    """
    body: dict = {
        "model": "grok-imagine-video",
        "prompt": prompt,
    }
    if duration:
        body["duration"] = duration
    if resolution:
        body["resolution"] = resolution
    if image_url:
        body["image_url"] = image_url

    r = httpx.post(
        f"{GROK_BASE_URL}/videos/generations",
        headers={
            "Authorization": f"Bearer {_get_key()}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    return data["request_id"]


def get_video_status(request_id: str) -> dict:
    """Poll status — return dict ตาม API
    - pending: {"status":"pending","progress":N}
    - done:    {"status":"done","video":{"url":"...","duration":N},...}
    """
    r = httpx.get(
        f"{GROK_BASE_URL}/videos/{request_id}",
        headers={"Authorization": f"Bearer {_get_key()}"},
        timeout=15,
    )
    return r.json()


def wait_for_video(
    request_id: str,
    timeout_s: int = 300,
    poll_every: int = 10,
    log=print,
) -> dict:
    """รอ render เสร็จ — return result dict (status=done)"""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        d = get_video_status(request_id)
        status = d.get("status", "").lower()

        if status == "done":
            return d
        if status in ("failed", "error"):
            raise RuntimeError(f"Render failed: {d}")

        progress = d.get("progress", 0)
        log(f"   ⏳ {status} {progress}%...")
        time.sleep(poll_every)

    raise TimeoutError(f"Video gen เกิน {timeout_s}s (req={request_id})")


def generate_video(
    prompt: str,
    duration: int | None = None,
    resolution: str | None = None,
    timeout_s: int = 300,
    log=print,
) -> dict:
    """
    Submit + wait + return result
    Returns: {
        "video_url": "https://vidgen.x.ai/...",
        "duration": 8,
        "request_id": "...",
        "cost_usd": 0.40,
    }
    """
    log(f"📤 Submit: {prompt[:60]}...")
    req_id = submit_video(prompt, duration, resolution)
    log(f"   request_id={req_id}")

    result = wait_for_video(req_id, timeout_s, log=log)

    video = result.get("video", {})
    usage = result.get("usage", {})
    ticks = usage.get("cost_in_usd_ticks", 0)
    cost_usd = ticks / 10_000_000_000  # 10^10 ticks per dollar

    return {
        "video_url": video.get("url"),
        "duration": video.get("duration", 0),
        "request_id": req_id,
        "cost_usd": cost_usd,
    }


def download_video(video_url: str, save_path: str) -> str:
    """ดาวน์โหลด mp4 ลง local"""
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        with client.stream("GET", video_url) as r:
            r.raise_for_status()
            with open(save_path, "wb") as f:
                for chunk in r.iter_bytes(chunk_size=8192):
                    f.write(chunk)
    size_mb = os.path.getsize(save_path) / 1024 / 1024
    print(f"✅ Downloaded: {save_path} ({size_mb:.1f} MB)")
    return save_path


if __name__ == "__main__":
    from dotenv import load_dotenv
    _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(_ROOT, ".env"), override=True)

    test_prompt = "A golden retriever puppy chasing a butterfly in a sunflower field, golden hour"
    result = generate_video(test_prompt)
    print(f"\n✅ Result: {result}")
    download_video(result["video_url"], "data/downloads/test.mp4")
