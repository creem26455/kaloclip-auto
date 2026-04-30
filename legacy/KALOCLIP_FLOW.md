# Kaloclip Auto — Flow รายละเอียด

> ✅ ยืนยัน 2026-04-27 — Top1 + Top2 ผ่าน E2E

---

## ขั้นตอนที่ 1: Kalodata Scraping

**URL:** https://www.kalodata.com/product

**Auth:** inject localStorage session
```js
localStorage.setItem('_l_KPLiPs', KALO_TOKEN)
localStorage.setItem('device_uuid', KALO_DEVICE)
localStorage.setItem('userName', KALO_USER)
```

**ผลลัพธ์:** รายการ Top 7 สินค้า + productId แต่ละตัว

---

## ขั้นตอนที่ 2: เปิด Kaloclip Form

**URL:** `https://clip.kalowave.com/video-creating?productId={id}&country=th`

**Auth:** inject localStorage (Kalowave session)
```js
localStorage.setItem('access_token', KWAVE_ACCESS_TOKEN)
localStorage.setItem('_l_KPLiPs', KWAVE_TOKEN)
localStorage.setItem('device_uuid', KWAVE_DEVICE)
```

---

## ขั้นตอนที่ 3: กรอก Form 3 Steps

### Step 1 — ตั้งค่าสินค้า
- รอ product images โหลด (spinner หายไป)
- กด "ถัดไป"

### Step 2 — ตั้งค่าวิดีโอ
- เลือก checkbox จุดขาย 5 อัน (selling points)
- เลือก กลุ่มตลาด = "ไทย"
- เลือก ภาษา = "ภาษาไทย"
- กด "ถัดไป"

### Step 3 — ตรวจสอบสคริปต์
- รอ render button (ปุ่ม "สร้าง{n}") ที่มีตัวเลข + enabled
- กด render button

---

## ขั้นตอนที่ 4: รอ Render + Download

**Pre-Phase 1 (หลัง submit form):**
- อาจมี Leave-dialog ปรากฏ: "สร้าง{n} | ยกเลิก | ออก"
- **ต้องกด "ออก"** เสมอ (render เริ่มแล้ว ไม่ต้องรันซ้ำ)

**Phase 1 — รอ render:**
- รอ button "ดาวน์โหลด" ปรากฏในหน้า detail
- Timeout: สูงสุด 15 นาที
- Poll ทุก 30 วินาที

**Phase 2 — Download:**
- คลิก "ดาวน์โหลด" ครั้งแรก → เปิด modal
- คลิก "ดาวน์โหลด" ครั้งสอง (ปุ่มใน modal) → download จริง
- ไฟล์: `{timestamp}_{productName}.mp4` (~9-10MB)
- Save: `/data/downloads/`

---

## ขั้นตอนที่ 5: TikTok Inbox Upload

### Step 5a — Init Upload
```
POST https://open.tiktokapis.com/v2/post/publish/inbox/video/init/
Authorization: Bearer {access_token}
Content-Type: application/json; charset=UTF-8

{
  "source_info": {
    "source": "FILE_UPLOAD",
    "video_size": 9782000,
    "chunk_size": 9782000,
    "total_chunk_count": 1
  }
}
```

**Response (success):**
```json
{
  "data": {
    "publish_id": "v_inbox_file~v2.7633477945981503506",
    "upload_url": "https://open-upload-sg.tiktokapis.com/upload?upload_id=...&upload_token=..."
  },
  "error": { "code": "ok" }
}
```

### Step 5b — Upload File
```
PUT {upload_url}
Content-Type: video/mp4
Content-Range: bytes 0-{N-1}/{N}
Content-Length: {N}
[binary video data]
```
**Response: HTTP 201** = สำเร็จ

---

## ขั้นตอนที่ 6: Telegram Notification

**Format:**
```
✅ สร้างวิดีโอสินค้า #{n} เสร็จแล้ว!
📦 สินค้า: {product_name}
🎵 TikTok: {publish_id}
⏳ เหลืออีก {remaining} สินค้า
```

---

## ขั้นตอนที่ 7: Manual Publish

1. เปิด TikTok App บนมือถือ
2. ไปที่ Profile → Creator Inbox (กล่องจดหมาย)
3. หาวิดีโอที่ bot upload ไว้
4. แก้ Caption / ใส่ Hashtag เพิ่มเติม (optional)
5. กด **Post** / **Publish**

---

## State Management

**ไฟล์:** `/data/state.json`
```json
{
  "index": 1,
  "products": [
    {"id": "1732912041092744232", "name": "Top1", "rank": 1},
    ...
  ],
  "last_run": "2026-04-27 16:36",
  "last_video": "/data/downloads/20260427_163534_Top1.mp4"
}
```

- `index` เพิ่มขึ้นทุกครั้งที่ทำสำเร็จ
- ครบ 7 → scrape Top7 ใหม่ + reset index=0
- ตั้ง index เองได้ที่ `/set-index` endpoint

---

## Dashboard Endpoints

| URL | Method | หน้าที่ |
|-----|--------|--------|
| `/` | GET | Dashboard หลัก |
| `/run` | POST | เริ่มรัน bot ทันที |
| `/logs` | GET | ดู log 50 บรรทัดล่าสุด |
| `/status` | GET | สถานะ running + state |
| `/set-index` | POST | ตั้ง index สินค้าที่จะทำ |
| `/save-cookies` | POST | บันทึก Kalodata cookies |
| `/tiktok-auth` | GET | เริ่ม TikTok OAuth |
| `/tiktok-callback` | GET | TikTok OAuth callback |
| `/tiktok-status` | GET | สถานะ TikTok connection |
| `/tiktok-disconnect` | POST | ยกเลิก TikTok connection |
