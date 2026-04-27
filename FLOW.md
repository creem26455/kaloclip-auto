# Kaloclip Auto — FLOW ที่ใช้งานได้จริง

> ✅ ยืนยันใช้งานได้: 2026-04-27 (Top1 + Top2 ผ่าน E2E)

---

## Flow สมบูรณ์ (End-to-End)

```
[1] kalodata.com — ดึง Top7 สินค้าขายดี
        ↓  (Playwright + Session Cookies / localStorage token)
[2] เปิด clip.kalowave.com/?productId=... โดยตรง (fallback จาก Kalodata)
        ↓
[3] กรอก form อัตโนมัติ (3 Steps):
      Step 1 — ตั้งค่าสินค้า: รอ product โหลด → กด ถัดไป
      Step 2 — ตั้งค่าวิดีโอ: เลือก 5 จุดขาย, ตลาด=ไทย, ภาษา=ภาษาไทย → กด ถัดไป
      Step 3 — ตรวจสอบสคริปต์: รอ render button (สร้าง+เลข) enabled → กด Render
        ↓
[4] รอ render เสร็จ (~5-15 นาที) → กด Download (2 ครั้ง: ครั้งแรก = modal, ครั้งสอง = download จริง)
      บันทึกไฟล์: /data/downloads/{timestamp}_{productName}.mp4  (~9-10MB)
        ↓
[5] TikTok Inbox Upload API
      POST https://open.tiktokapis.com/v2/post/publish/inbox/video/init/
      Headers:
        Authorization: Bearer {access_token}
        Content-Type: application/json; charset=UTF-8
      Body:
        source_info:
          source: FILE_UPLOAD
          video_size: {file_size_bytes}
          chunk_size: {file_size_bytes}
          total_chunk_count: 1
      Response → publish_id (v_inbox_file~v2.xxx) + upload_url
        ↓
[6] PUT {upload_url} — upload ไฟล์วิดีโอ
      Headers:
        Content-Type: video/mp4
        Content-Range: bytes 0-{N-1}/{N}
        Content-Length: {N}
      Response: HTTP 201
        ↓
[7] Telegram แจ้ง BossMhee: เสร็จแล้ว + publish_id
        ↓
[8] BossMhee เปิด TikTok App → Creator Inbox → กด Publish เอง
        ↓
[9] state["index"] += 1 → รอบถัดไปทำสินค้า #ถัดไป
    (ครบ 7 → refresh Top7 ใหม่, reset index=0)
```

---

## TikTok OAuth Setup

### ขั้นตอนเชื่อมต่อ TikTok
1. เปิด https://kaloclip-auto-production.up.railway.app
2. กด **"Connect TikTok"** (หรือไปที่ `/tiktok-auth`)
3. Login ด้วย TikTok account ที่เป็น Sandbox Tester (zefour.o)
4. Authorize → ระบบ save token ไว้ที่ `/data/tiktok_token.json`
5. หน้า dashboard จะแสดง ✅ TikTok Connected

### TikTok App (Sandbox — BossMhee_Test)
| ข้อมูล | ค่า |
|--------|-----|
| App Name | BossMhee_Test |
| Parent App | BossMhee_AI_Project (ID: 7626752266627893268) |
| Sandbox ID | 7626771916891899925 |
| Scope | `video.upload` |
| Sandbox Tester | zefour.o |
| Redirect URI | `https://kaloclip-auto-production.up.railway.app/tiktok-callback` |
| Env: Client Key | `TIKTOK_CLIENT_KEY` |
| Env: Client Secret | `TIKTOK_CLIENT_SECRET` |

**หมายเหตุ:** Sandbox app ใช้ได้เฉพาะ account ที่เพิ่มเป็น Sandbox Tester ใน TikTok Developer Portal

---

## Kalodata / Kalowave Session

### วิธีตั้ง Session Cookies (Kalodata)
1. เปิด kalodata.com → Login
2. F12 → Console → พิมพ์ `copy(document.cookie)`
3. วาง cookies ที่ได้ในช่อง Dashboard → "Save Cookies"

### Railway ENV Variables (Kalowave)
```
KWAVE_ACCESS_TOKEN=<Bearer token จาก clip.kalowave.com>
KWAVE_TOKEN=<_l_KPLiPs cookie>
KWAVE_DEVICE=<device_uuid>
KALO_TOKEN=<_l_KPLiPs จาก kalodata.com>
KALO_DEVICE=<device_uuid จาก kalodata.com>
KALO_USER=<userName>
```

---

## Railway ENV Variables ที่จำเป็น

```
TIKTOK_CLIENT_KEY=<จาก TikTok Developer Portal>
TIKTOK_CLIENT_SECRET=<จาก TikTok Developer Portal>
TIKTOK_REDIRECT_URI=https://kaloclip-auto-production.up.railway.app/tiktok-callback
TELEGRAM_TOKEN=<bot token>
TELEGRAM_CHAT_ID=<chat id>
```

---

## ข้อผิดพลาดที่พบและวิธีแก้

### `scope_not_authorized` (Direct Post API)
- **สาเหตุ:** ใช้ `/v2/post/publish/video/init/` ต้องการ `video.publish` scope ซึ่ง Sandbox ไม่รองรับ
- **แก้:** ใช้ **Inbox API** (`/inbox/video/init/`) แทน — ต้องการแค่ `video.upload`

### `non_sandbox_target` (TikTok OAuth)
- **สาเหตุ:** Login TikTok ด้วย account ที่ไม่ใช่ Sandbox Tester
- **แก้:** ต้อง Login ด้วย account "zefour.o" หรือ account ที่ add ใน Sandbox Settings

### `unauthorized_client` / `invalid_client`
- **สาเหตุ:** client_key หรือ client_secret ผิด
- **แก้:** ไปที่ TikTok Developer Portal → เปิด Credentials → **คลิก eye icon** อ่านค่าจริง (ระวัง `1` vs `l`, `0` vs `O`)

### Leave-dialog "สร้าง{n} / ยกเลิก / ออก"
- **สาเหตุ:** Navigate ออกจาก Kaloclip form ขณะ render กำลังทำงาน
- **แก้:** กด **"ออก"** เสมอ (render เริ่มแล้วใน _fill_form → ไม่ต้องรันใหม่)

### Token หายหลัง Railway Redeploy
- **สาเหตุ:** Railway volume `/data/` รีเซ็ตเมื่อ redeploy
- **แก้:** ไปที่ dashboard → กด Connect TikTok ใหม่ทุกครั้งหลัง redeploy

---

## ไฟล์หลัก

| ไฟล์ | หน้าที่ |
|------|--------|
| `kaloclip.py` | Bot หลัก — scraping, form fill, download, TikTok upload |
| `app.py` | Flask dashboard + TikTok OAuth routes |
| `requirements.txt` | Python dependencies |
| `Procfile` | Railway start command |
| `/data/tiktok_token.json` | TikTok access token (Railway volume) |
| `/data/session_cookies.json` | Kalodata session cookies |
| `/data/state.json` | index + product list |
| `/data/downloads/` | วิดีโอที่ดาวน์โหลด |

---

## Cron Schedule

- **เวลา:** 09:00 น. (Asia/Bangkok) ทุกวัน
- **Library:** APScheduler (BackgroundScheduler)
- **หรือ:** กด "Run Now" บน dashboard เพื่อรันทันที
