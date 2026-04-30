"""
TikTok Inbox Upload (port จาก kaloclip-auto.archive)
- ใช้ video.upload scope (ไม่ต้องการ video.publish)
- วิดีโอจะไปอยู่ใน TikTok Creator Inbox → user publish เอง
"""

import json
import os
import httpx


def upload_to_inbox(
    video_path: str,
    token_file: str,
    log=print,
) -> str:
    """
    Upload วิดีโอเข้า TikTok Creator Inbox

    Returns:
        publish_id (str) ถ้าสำเร็จ, "" ถ้าข้าม/ล้มเหลว
    """
    if not os.path.exists(token_file):
        log("⏭ TikTok: ยังไม่ได้ connect — ไปที่ /tiktok-auth")
        return ""

    with open(token_file) as f:
        token_data = json.load(f)

    access_token = token_data.get("access_token", "")
    if not access_token:
        log("⚠️ TikTok token ว่าง")
        return ""

    if not os.path.exists(video_path):
        log(f"⚠️ ไม่พบไฟล์ {video_path}")
        return ""

    file_size = os.path.getsize(video_path)
    log(f"📤 TikTok upload: {os.path.basename(video_path)} ({file_size//1024}KB)")

    try:
        # Step 1: Init Inbox Upload
        init_resp = httpx.post(
            "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": file_size,
                    "chunk_size": file_size,
                    "total_chunk_count": 1,
                },
            },
            timeout=30,
        )
        init_data = init_resp.json()

        err = init_data.get("error", {})
        if err.get("code", "ok") != "ok":
            log(f"❌ TikTok init error: {err}")
            return ""

        publish_id = init_data["data"]["publish_id"]
        upload_url = init_data["data"]["upload_url"]

        # Step 2: Upload file
        with open(video_path, "rb") as f:
            video_bytes = f.read()

        upload_resp = httpx.put(
            upload_url,
            content=video_bytes,
            headers={
                "Content-Type": "video/mp4",
                "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
                "Content-Length": str(file_size),
            },
            timeout=180,
        )

        if upload_resp.status_code not in [200, 201, 204, 206]:
            log(f"❌ Upload failed: {upload_resp.status_code} {upload_resp.text[:200]}")
            return ""

        log(f"✅ TikTok upload สำเร็จ: publish_id={publish_id}")
        return publish_id

    except Exception as e:
        log(f"❌ TikTok upload error: {e}")
        return ""
