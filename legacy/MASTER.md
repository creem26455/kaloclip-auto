# Kaloclip Auto — Shopee & TikTok Video Automation

> ✅ E2E ยืนยันทำงานได้จริง: 2026-04-27 (Top1 + Top2 ผ่านแล้ว)

---

## ภาพรวม
ระบบสร้างวิดีโอสินค้าขายดีอัตโนมัติจาก Kalodata → Kaloclip AI สร้างวิดีโอ → อัปโหลด TikTok Creator Inbox → BossMhee กด Publish เอง

---

## Links สำคัญ
| ชื่อ | URL |
|------|-----|
| **Dashboard** | https://kaloclip-auto-production.up.railway.app |
| **GitHub** | https://github.com/creem26455/kaloclip-auto |
| **Railway Project** | https://railway.app (project: accomplished-nurturing) |
| **Kalodata** | https://www.kalodata.com/product |
| **Kaloclip (Kalowave)** | https://clip.kalowave.com |
| **TikTok Developer Portal** | https://developers.tiktok.com/app/7626752266627893268/sandbox/7626771916891899925 |

---

## Credentials
| Key | Value |
|-----|-------|
| Railway API Token | ca5cae58-d492-4a5f-a889-fc0fbd2e5209 |
| Telegram Bot Token | 8769283566:AAFNnyKf9KrWTUbfnJr6YRlJ6KAxN325xYg |
| Telegram Chat ID | 8591956462 |
| GitHub | creem26455/kaloclip-auto |
| TikTok Sandbox App ID | 7626771916891899925 |
| TikTok Sandbox Tester | zefour.o |

---

## โค้ดโปรเจค
- **Local folder:** `C:\kaloclip-auto\`
- **Railway service ID:** 9d84badf-bca0-4afa-b07c-d98805d0e526
- **Environment ID:** 0a75e367-51ec-4203-bcbf-554b9646744a

---

## FLOW ทำงาน (E2E ✅)

```
Kalodata Top7 scrape
    ↓
clip.kalowave.com กรอก form 3 steps
    ↓
Render วิดีโอ (~5-15 นาที)
    ↓
Download MP4 (~9-10MB) → /data/downloads/
    ↓
TikTok Inbox Upload API
POST /v2/post/publish/inbox/video/init/
    ↓
PUT {upload_url} → HTTP 201
    ↓
วิดีโออยู่ใน Creator Inbox → BossMhee กด Publish
    ↓
index++ → วันถัดไปทำสินค้า #ถัดไป
```

---

## TikTok Integration

### API ที่ใช้: Inbox Upload (video.upload scope)
```
POST https://open.tiktokapis.com/v2/post/publish/inbox/video/init/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "source_info": {
    "source": "FILE_UPLOAD",
    "video_size": <bytes>,
    "chunk_size": <bytes>,
    "total_chunk_count": 1
  }
}
→ Response: { publish_id: "v_inbox_file~v2.xxx", upload_url: "..." }

PUT {upload_url}
Content-Type: video/mp4
Content-Range: bytes 0-{N-1}/{N}
→ HTTP 201 = สำเร็จ
```

### เชื่อมต่อ TikTok (ต้องทำหลังทุก Redeploy)
1. เปิด Dashboard: https://kaloclip-auto-production.up.railway.app
2. กด **Connect TikTok**
3. Login TikTok ด้วย account **zefour.o** (Sandbox Tester)
4. Authorize → token save ที่ `/data/tiktok_token.json`

---

## การใช้งาน (ทุกวัน)

### วิธีที่ 1 — ผ่าน Dashboard (แนะนำ)
1. เปิด https://kaloclip-auto-production.up.railway.app
2. ตรวจสอบ ✅ TikTok Connected
3. กด **Run Now**
4. รอ Telegram แจ้งว่า upload เสร็จ
5. เปิด TikTok app → Creator Inbox → กด Publish

### Auto Cron
- รันอัตโนมัติทุกวัน **09:00 น. (Asia/Bangkok)**

---

## Logic วนสินค้า
- ดึง **Top 7** สินค้าขายดีจาก Kalodata
- วันที่ 1 → สินค้า #1, วันที่ 2 → สินค้า #2 ... วันที่ 7 → สินค้า #7
- รอบใหม่ → ดึง Top 7 ใหม่อัตโนมัติ
- ตั้ง index เองได้ที่ dashboard

---

## Files โปรเจค
| ไฟล์ | หน้าที่ |
|------|---------|
| `app.py` | Flask web dashboard + TikTok OAuth |
| `kaloclip.py` | Playwright bot หลัก (scrape + form fill + upload) |
| `FLOW.md` | เอกสาร flow และ debug guide |
| `/data/tiktok_token.json` | TikTok token (หายหลัง redeploy) |
| `/data/session_cookies.json` | Kalodata session cookies |
| `/data/state.json` | index + product list |
| `/data/downloads/` | MP4 วิดีโอที่ดาวน์โหลด |

---

## ปัญหาที่เคยเจอ
| ปัญหา | วิธีแก้ |
|-------|--------|
| `scope_not_authorized` | ใช้ Inbox API แทน Direct Post |
| `non_sandbox_target` | Login TikTok เป็น zefour.o |
| Token หายหลัง deploy | Connect TikTok ใหม่ที่ dashboard |
| Leave-dialog วนซ้ำ | แก้แล้ว v11fa329 — กด "ออก" เสมอ |

---

## TODO ถัดไป
- [ ] Production TikTok app → video.publish scope → Direct Post อัตโนมัติ
- [ ] Auto-post Shopee Video
- [ ] Retry logic เมื่อ TikTok upload fail

---

*อัปเดตล่าสุด: 2026-04-27 — E2E ผ่าน Top1 + Top2*
