"""
TikTok Direct Post API — Auto-publish with caption + hashtag + AI label
ใช้ video.publish scope (ต้อง enable ใน TikTok Sandbox)

ต่างจาก tiktok_upload.py (Inbox API) ที่:
- Inbox: upload → user manual publish
- Direct Post: upload + publish + caption + AI label = auto 100%
"""

import json
import os
import time
import httpx


def publish_video(
    video_path: str,
    title: str,
    token_file: str,
    caption: str = "",
    hashtags: list[str] | None = None,
    ai_generated: bool = True,
    privacy_level: str = "PUBLIC_TO_EVERYONE",
    disable_comment: bool = False,
    disable_duet: bool = False,
    disable_stitch: bool = False,
    log=print,
) -> dict:
    """
    Auto-publish video to TikTok with full metadata

    Args:
        video_path: path to mp4
        title: short title (will be combined with caption)
        token_file: path to /data/tiktok_token.json
        caption: full Thai caption
        hashtags: list ["#ซิงค์", "#ดูแลผิว"]
        ai_generated: bool — set to True for AI content (TikTok requires)
        privacy_level: "PUBLIC_TO_EVERYONE" | "MUTUAL_FOLLOW_FRIENDS" | "SELF_ONLY"

    Returns:
        {"publish_id": "...", "publicaly_available_post_id": "...", "url": "..."}
    """
    if not os.path.exists(token_file):
        log("⏭ TikTok: ยังไม่ได้ connect")
        return {}

    with open(token_file) as f:
        token_data = json.load(f)

    access_token = token_data.get("access_token", "")
    if not access_token:
        log("⚠️ TikTok token ว่าง")
        return {}

    if not os.path.exists(video_path):
        log(f"⚠️ ไม่พบไฟล์ {video_path}")
        return {}

    file_size = os.path.getsize(video_path)
    log(f"📤 Direct Post: {os.path.basename(video_path)} ({file_size//1024}KB)")

    # Combine title + caption + hashtags
    full_title = title
    if caption:
        full_title = f"{title}\n\n{caption}"
    if hashtags:
        full_title += "\n\n" + " ".join(hashtags)

    # Truncate to TikTok 2200 char limit
    full_title = full_title[:2200]

    try:
        # Step 1: Init Direct Post (with all metadata in post_info)
        init_resp = httpx.post(
            "https://open.tiktokapis.com/v2/post/publish/video/init/",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={
                "post_info": {
                    "title": full_title,
                    "privacy_level": privacy_level,
                    "disable_comment": disable_comment,
                    "disable_duet": disable_duet,
                    "disable_stitch": disable_stitch,
                    "video_cover_timestamp_ms": 1000,  # cover frame at 1s
                    "ai_generated_content_label": ai_generated,
                    "auto_add_music": False,
                },
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
            log(f"❌ Init error: {err}")
            return {}

        publish_id = init_data["data"]["publish_id"]
        upload_url = init_data["data"]["upload_url"]
        log(f"  publish_id={publish_id}")

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
            log(f"❌ Upload failed: {upload_resp.status_code}")
            return {}

        log(f"✅ Upload OK — รอ TikTok process + publish...")

        # Step 3: Poll status until published
        status = poll_publish_status(publish_id, access_token, log=log)

        return {
            "publish_id": publish_id,
            "status": status.get("status", ""),
            "publicaly_available_post_id": status.get("publicaly_available_post_id", ""),
            "fail_reason": status.get("fail_reason", ""),
        }

    except Exception as e:
        log(f"❌ Direct Post error: {e}")
        return {}


def poll_publish_status(
    publish_id: str,
    access_token: str,
    timeout_s: int = 120,
    log=print,
) -> dict:
    """Poll publish status — TikTok processes the video before going live"""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            r = httpx.post(
                "https://open.tiktokapis.com/v2/post/publish/status/fetch/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"publish_id": publish_id},
                timeout=15,
            )
            data = r.json().get("data", {})
            status = data.get("status", "")
            log(f"   📊 status={status}")

            if status in ("PUBLISH_COMPLETE", "PUBLICLY_AVAILABLE"):
                log(f"✅ Published! post_id={data.get('publicaly_available_post_id', '')}")
                return data
            if status in ("FAILED", "PROCESSING_FAILED"):
                log(f"❌ Publish failed: {data.get('fail_reason', '')}")
                return data

            time.sleep(5)
        except Exception as e:
            log(f"⚠️ Status poll error: {e}")
            time.sleep(5)

    log(f"⏰ Timeout — publish_id={publish_id}")
    return {"status": "TIMEOUT", "publish_id": publish_id}


def refresh_token_if_needed(token_file: str, client_key: str, client_secret: str, log=print) -> bool:
    """Refresh access_token if expired (run before publishing)"""
    if not os.path.exists(token_file):
        return False

    with open(token_file) as f:
        token_data = json.load(f)

    refresh_token = token_data.get("refresh_token", "")
    if not refresh_token:
        log("⚠️ ไม่มี refresh_token — ต้อง re-auth")
        return False

    try:
        r = httpx.post(
            "https://open.tiktokapis.com/v2/oauth/token/",
            data={
                "client_key": client_key,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        new_data = r.json()
        if "access_token" in new_data:
            token_data.update({
                "access_token": new_data["access_token"],
                "refresh_token": new_data.get("refresh_token", refresh_token),
                "expires_in": new_data.get("expires_in", 0),
                "refreshed_at": time.time(),
            })
            with open(token_file, "w") as f:
                json.dump(token_data, f, indent=2)
            log("🔄 Token refreshed")
            return True
    except Exception as e:
        log(f"❌ Refresh error: {e}")

    return False
