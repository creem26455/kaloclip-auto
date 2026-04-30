"""
Full Pipeline (Phase 3) — รัน end-to-end:
1. ดึง 1 script จาก Supabase queue
2. Grok gen ฉาก 1 + ฉาก 2 (15s แต่ละฉาก)
3. FFmpeg merge → 30s mp4
4. Upload TikTok Inbox
5. Telegram notify
6. Update DB status

ใช้รัน: python src/pipeline.py
"""

import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from grok_client import generate_video, download_video
from ffmpeg_merge import merge_clips, get_video_duration
from tiktok_upload import upload_to_inbox
from tiktok_publish import publish_video, refresh_token_if_needed
from telegram_notify import notify_video_done, notify_error

# Mode: "DIRECT_POST" (auto-publish) | "INBOX" (manual publish)
TIKTOK_MODE = os.environ.get("TIKTOK_MODE", "DIRECT_POST")
from end_card import has_product_image, get_product_image_path, make_end_card, append_end_card
from caption_gen import generate_caption
import db


# Cost per clip (จาก usage.cost_in_usd_ticks ของ API จริง)
# 480p: $0.05/วินาที = $0.75 per 15s clip
# 720p: $0.07/วินาที = $1.05 per 15s clip
COST_PER_15S_CLIP_480P = 0.75


def run_one(token_file: str, output_dir: str, temp_dir: str, log=print) -> bool:
    """ทำงาน 1 รอบ — ดึง script ใหม่ + gen + upload + แจ้ง"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    Path(temp_dir).mkdir(parents=True, exist_ok=True)

    # 1. Fetch script
    script = db.fetch_next_script()
    if not script:
        log("📭 Queue ว่าง — ไม่มี script ที่ pending")
        return False

    sid = script["id"]
    title = script["title"]
    log(f"\n🎬 Script #{sid}: {title}")
    db.mark_processing(sid)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c for c in title if c.isalnum() or c in " _-")[:40].replace(" ", "_")
    s1_path = Path(temp_dir) / f"{timestamp}_s1.mp4"
    s2_path = Path(temp_dir) / f"{timestamp}_s2.mp4"
    out_path = Path(output_dir) / f"{timestamp}_{safe_title}.mp4"

    try:
        # 2. Grok generate (480p, 15s — ถูกพอ + คุณภาพ TikTok ดี)
        log(f"📹 [1/4] Generating Scene 1...")
        r1 = generate_video(script["scene1_prompt"], duration=15, log=log)
        download_video(r1["video_url"], str(s1_path))

        log(f"📹 [2/4] Generating Scene 2...")
        r2 = generate_video(script["scene2_prompt"], duration=15, log=log)
        download_video(r2["video_url"], str(s2_path))

        # 3. Merge cartoon scenes
        log(f"🎞️ [3/4] Merging scenes...")
        cartoon_path = Path(temp_dir) / f"{timestamp}_cartoon.mp4"
        merge_clips(str(s1_path), str(s2_path), str(cartoon_path))

        # 3b. lookup supplement data จาก category → variety_config
        from variety_config import SUPPLEMENT_CATEGORIES
        category = script.get("category", "")
        supplement_data = next(
            (s for s in SUPPLEMENT_CATEGORIES if s["name_en"] == category),
            {},
        )

        # ถ้ามีรูปสินค้า → Hybrid: ต่อ end-card 5s
        if supplement_data and has_product_image(supplement_data):
            log(f"🛒 [3b] Hybrid mode: ต่อ end-card รูปสินค้าจริง...")
            end_card_path = Path(temp_dir) / f"{timestamp}_endcard.mp4"
            make_end_card(
                product_image_path=get_product_image_path(supplement_data),
                cta_text_th=supplement_data.get("cta_th", "กดสั่งในตะกร้าเลย!"),
                output_path=str(end_card_path),
                duration=5.0,
            )
            append_end_card(str(cartoon_path), str(end_card_path), str(out_path))
            end_card_path.unlink(missing_ok=True)
        else:
            # Mode A: Pure cartoon
            log(f"🎬 [3b] Pure cartoon mode (ไม่มีรูปสินค้า)")
            os.rename(str(cartoon_path), str(out_path))

        duration = get_video_duration(str(out_path))

        # 3c. Generate TikTok caption (ภาษาไทย + hashtag + disclaimer)
        if supplement_data:
            caption = generate_caption(supplement_data, title)
            caption_path = out_path.with_suffix(".caption.txt")
            with open(caption_path, "w", encoding="utf-8") as f:
                f.write(caption)
            log(f"📝 Caption saved: {caption_path.name}")

        # 4. Upload + Publish TikTok (Direct Post = auto with caption + AI label)
        if TIKTOK_MODE == "DIRECT_POST":
            log(f"📤 [4/4] Direct Posting to TikTok (auto-publish)...")
            # Refresh token if needed
            client_key = os.environ.get("TIKTOK_CLIENT_KEY", "")
            client_secret = os.environ.get("TIKTOK_CLIENT_SECRET", "")
            refresh_token_if_needed(token_file, client_key, client_secret, log=log)

            # Build hashtags from supplement
            hashtag_list = []
            if supplement_data:
                from caption_gen import HASHTAG_BANK, UNIVERSAL_TAGS
                import random
                tags = HASHTAG_BANK.get(supplement_data.get("name_en", ""), [])
                hashtag_list = tags[:5] + random.sample(UNIVERSAL_TAGS, k=min(5, len(UNIVERSAL_TAGS)))

            result = publish_video(
                video_path=str(out_path),
                title=title,
                token_file=token_file,
                caption=caption if 'caption' in dir() else "",
                hashtags=hashtag_list,
                ai_generated=True,
                privacy_level="PUBLIC_TO_EVERYONE",
                log=log,
            )
            publish_id = result.get("publish_id", "")
            post_id = result.get("publicaly_available_post_id", "")
            if not publish_id:
                raise RuntimeError("TikTok Direct Post returned empty result")
            log(f"🎉 Posted! post_id={post_id}")
        else:
            log(f"📤 [4/4] Uploading to TikTok Inbox (manual publish)...")
            publish_id = upload_to_inbox(str(out_path), token_file, log=log)
            if not publish_id:
                raise RuntimeError("TikTok upload returned empty publish_id")

        # Real cost จาก response API
        cost = r1.get("cost_usd", COST_PER_15S_CLIP_480P) + r2.get("cost_usd", COST_PER_15S_CLIP_480P)
        db.mark_done(sid, publish_id, str(out_path), cost)

        # 5. Telegram
        notify_video_done(title, publish_id, duration, cost, log=log)

        log(f"\n✅ DONE: Script #{sid} — publish_id={publish_id}")
        return True

    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        log(f"❌ Error: {err}")
        log(traceback.format_exc())
        db.mark_failed(sid, err)
        notify_error(title, err, log=log)
        return False

    finally:
        # cleanup temp
        s1_path.unlink(missing_ok=True)
        s2_path.unlink(missing_ok=True)


if __name__ == "__main__":
    from dotenv import load_dotenv
    _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(_ROOT, ".env"), override=True)

    # Local mode (Railway will use /data/)
    base = "/data" if os.path.exists("/data") else "data"
    run_one(
        token_file=f"{base}/tiktok_token.json",
        output_dir=f"{base}/downloads",
        temp_dir=f"{base}/temp",
    )
