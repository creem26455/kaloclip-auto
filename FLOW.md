# Kaloclip Auto — FLOW ที่ใช้งานได้จริง

> ยืนยันใช้งานได้: 2026-04-26

---

## Flow สมบูรณ์ (End-to-End)

```
[1] kalodata.com — ดึง Top7 สินค้าขายดี
        ↓  (Playwright + Session Cookies)
[2] คลิก "Kaloclip AI" บนสินค้า index ปัจจุบัน
        ↓
[3] กรอก form อัตโนมัติ:
      - เลือก selling points (จุดขาย)
      - ปรับสคริปต์ AI
      - เลือก format (Vertical 9:16)
      - กด "Render"
        ↓
[4] รอ render เสร็จ (~2-5 นาที) → กด Download
      บันทึกไฟล์ไว้ที่: /data/downloads/{ชื่อสินค้า}.mp4
        ↓
[5] TikTok Direct Post API
      POST https://open.tiktokapis.com/v2/post/publish/video/init/
      Headers:
        Authorization: Bearer {access_token}
        Content-Type: application/json; charset=UTF-8
      Body:
        post_info:
          title: "สินค้าน่าซื้อ! {product_name} 🛍️\n#TikTokShop #affiliate #สินค้าแนะนำ ..."
          privacy_level: PUBLIC_TO_EVERYONE
          ai_generated_video: true   ← AI Label (บังคับ)
          disable_duet: false
          disable_comment: false
          disable_stitch: false
          brand_content_toggle: false
        source_info:
          source: FILE_UPLOAD
          video_size: {file_size_bytes}
          chunk_size: {file_size_bytes}
          total_chunk_count: 1
      Response → publish_id + upload_url
        ↓
[6] PUT {upload_url} — upload ไฟล์วิดีโอ
      Headers:
        Content-Type: video/mp4
        Content-Range: bytes 0-{N-1}/{N}
        Content-Length: {N}
        ↓
[7] Telegram แจ้ง BossMhee: โพสสำเร็จ + publish_id
        ↓
[8] state["index"] += 1 → รอบถัดไปทำสินค้า #ถัดไป
    (ครบ 7 → refresh Top7 ใหม่, reset index=0)
```

---

## TikTok OAuth Setup

### ขั้นตอนเชื่อมต่อ TikTok ครั้งแรก
1. เปิด https://kaloclip-auto-production.up.railway.app
2. กด **"Connect TikTok"** (หรือไปที่ `/tiktok-auth`)
3. Login ด้วย TikTok account ที่เป็น Sandbox Tester
4. Authorize → ระบบ save token ไว้ที่ `/data/tiktok_token.json`
5. หน้า dashboard จะแสดง ✅ TikTok Connected

### TikTok App (Sandbox)
| ข้อมูล | ค่า |
|--------|-----|
| App Name | BossMhee_Test |
| App ID | 7626771916891899925 |
| Scope | `video.upload` |
| Redirect URI | `https://kaloclip-auto-production.up.railway.app/tiktok-callback` |
| Env var: Client Key | `TIKTOK_CLIENT_KEY` |
| Env var: Client Secret | `TIKTOK_CLIENT_SECRET` |

**หมายเหตุ:** Sandbox app ใช้ได้เฉพาะ account ที่เพิ่มเป็น Sandbox Tester ใน TikTok Developer Portal

---

## Railway ENV Variables ที่จำเป็น

```
TIKTOK_CLIENT_KEY=<จาก TikTok Developer Portal>
TIKTOK_CLIENT_SECRET=<จาก TikTok Developer Portal> ← อ่านให้ครบทุกตัวอักษร!
TIKTOK_REDIRECT_URI=https://kaloclip-auto-production.up.railway.app/tiktok-callback
TELEGRAM_TOKEN=<bot token>
TELEGRAM_CHAT_ID=<chat id>
```

---

## ข้อผิดพลาดที่พบและวิธีแก้

### `unauthorized_client` / `invalid_client`
- **สาเหตุ:** client_key หรือ client_secret ผิด
- **แก้:** ไปที่ TikTok Developer Portal → Manage Apps → เปิด Credentials → **คลิก eye icon เพื่อดูค่าจริง** (อย่าพิมพ์ตาม เพราะตัวอักษรบางตัวหน้าตาคล้ายกัน เช่น `1` กับ `l`, `0` กับ `O`)
- ตั้งค่าใหม่ใน Railway Environment → Redeploy

### TikTok init error: `post_info not supported`
- **สาเหตุ:** ใช้ inbox endpoint (`/inbox/video/init/`) แทน direct endpoint
- **แก้:** ต้องใช้ `https://open.tiktokapis.com/v2/post/publish/video/init/` เท่านั้น

### Upload ไม่เสร็จ / timeout
- **สาเหตุ:** ไฟล์ใหญ่เกิน, timeout 180s น้อยเกินไป
- **แก้:** เพิ่ม timeout หรือแบ่ง chunk (ปัจจุบันใช้ single chunk)

---

## ไฟล์หลัก

| ไฟล์ | หน้าที่ |
|------|--------|
| `kaloclip.py` | Bot หลัก — scraping, rendering, TikTok upload |
| `app.py` | Flask dashboard + TikTok OAuth routes |
| `requirements.txt` | Python dependencies |
| `Procfile` | Railway start command |
| `/data/tiktok_token.json` | TikTok access token (Railway volume) |
| `/data/session_cookies.json` | Kalodata session cookies (Railway volume) |
| `/data/state.json` | index + product list + log |
| `/data/downloads/` | วิดีโอที่ดาวน์โหลด |

---

## Cron Schedule

- **เวลา:** 09:00 น. (Asia/Bangkok) ทุกวัน
- **Library:** APScheduler (BackgroundScheduler)
- **หรือ:** กด "Run Now" บน dashboard เพื่อรันทันที
