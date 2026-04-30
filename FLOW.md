# Pipeline Flow — Production V2.1

> ✅ ทดสอบ E2E ผ่าน — 2026-04-30
> Latest production video: `data/downloads/20260430_211645_INZENT_Zinc_FINAL.mp4`

---

## 🎬 End-to-End Flow

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Random Config (variety_config.py)                   │
│   • Pick supplement (random or specified)                   │
│   • Pick camera angle (10 options)                          │
│   • Pick mood (6 options)                                   │
│   • Pick setting (8 options)                                │
│   • Pick 0-2 cameos (Bluebell / Mam / Mochi)                │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Claude Haiku → Script JSON                          │
│   Input:  config + compliance rules                         │
│   Output: {title, scene1_prompt, scene2_prompt}             │
│   Cost:   ~$0.001                                           │
│                                                             │
│   ⚠️ Auto-wrap with STYLE_PREFIX/SUFFIX                     │
│      → "3D Pixar Disney cartoon, NO real humans"            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Submit Grok Imagine Video (parallel)                │
│   POST https://api.x.ai/v1/videos/generations               │
│   body: {model: "grok-imagine-video",                       │
│          prompt: <scene>, duration: 15}                     │
│   → returns request_id (async)                              │
│                                                             │
│   Cost: $0.75 × 2 scenes = $1.50                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Poll + Download                                     │
│   GET /v1/videos/{request_id}                               │
│   • status: pending → done (3-5 minutes)                    │
│   • Download mp4 from response.video.url                    │
│   • Specs: 848x480 H.264 + AAC, ~3-5 MB each                │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: FFmpeg Merge                                        │
│   ffmpeg concat:                                            │
│     scene1.mp4 + scene2.mp4 → cartoon.mp4 (30s)            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: End-card (Hybrid mode)                              │
│   IF data/products/{name}.jpg exists:                       │
│     1. PIL composite: gradient + product + Thai CTA         │
│     2. FFmpeg: image → 5s mp4 (with audio track)            │
│     3. ffmpeg concat: cartoon + endcard → final.mp4 (35s)   │
│   ELSE (Audio Mode):                                        │
│     final = cartoon (30s)                                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 7: Caption Generator                                   │
│   • Title (Thai) + product name (TH/EN)                     │
│   • Target audience + CTA                                   │
│   • Disclaimer (อย. + AI label reminder)                   │
│   • Hashtags (specific + universal, ~10 tags)               │
│   • Save: final.caption.txt                                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 8: Output (ready to post)                              │
│   data/downloads/                                           │
│   ├── {timestamp}_{category}_FINAL.mp4   (35s, 3-7 MB)      │
│   └── {timestamp}_{category}_FINAL.caption.txt              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 9 (Manual): TikTok Posting                             │
│   1. Open TikTok app → Profile → Affiliate                  │
│   2. Add product to Showcase (e.g., INZENT Zinc Plus)       │
│   3. + Post → Upload video                                  │
│   4. ⚠️ Toggle "AI-generated content" → ON                  │
│   5. Paste caption (skip first AI reminder line)            │
│   6. Pin product → Post                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔑 API Endpoints Used

### Grok Imagine Video API
```
POST https://api.x.ai/v1/videos/generations
Headers:
  Authorization: Bearer {XAI_API_KEY}
  Content-Type: application/json
Body:
  {
    "model": "grok-imagine-video",
    "prompt": "...",
    "duration": 15  // 8 (default) or 15
  }
Response: { "request_id": "..." }

GET https://api.x.ai/v1/videos/{request_id}
Response (pending): { "status": "pending", "progress": 50 }
Response (done):    { "status": "done", "video": {"url": "...", "duration": 15},
                      "usage": {"cost_in_usd_ticks": 7500000000} }
```

**Pricing:**
- 480p: $0.05/วินาที (15s = $0.75)
- 720p: $0.07/วินาที (15s = $1.05)

### Anthropic Claude Haiku 4.5
```
POST https://api.anthropic.com/v1/messages
model: "claude-haiku-4-5"
~$0.001 per script
```

---

## 🎯 Compliance Hardening (V2.1)

### What Changed from V1

| Rule | V1 | V2.1 |
|---|---|---|
| Transformation | Instant magical sparkles | Time-skip (Day 1 → 30) |
| Uncle Pan | ตะคอก ไม้เรียว ชี้หน้า | Stern but caring, scroll |
| Scolding tone | Loud commanding | Comedy frustrated uncle |
| CTA | "เร็ว!" "อย่ารอ!" | "ลอง...ดูนะ" |
| Disclaimer | Caption only | Caption + scene 2 overlay |
| AI Label | Manual | Caption reminder added |

### Banned Words List (compliance_rules.py)

```python
BANNED_HEALTH_CLAIMS = [
    "รักษาโรค", "หายขาด", "ตลอดกาล", "100%",
    "FDA approved", "ผลทันที", "instant cure",
    "ลามทั้งหน้า", "ก่อนสายเกินไป",
    "พังหมด", "หายวับ",
    # Prompt-level banned (Grok keywords):
    "magical sparkles disappear pimple",
    "instant transformation",
    "pimple poofs away",
    "deflates dramatically",
    "muscles inflate one-by-one",
]
```

---

## 🔧 Manual Steps (User Tasks)

### Setup ครั้งเดียว (15 นาที)
1. ✅ Create TikTok Shop Affiliate account (1000+ follower)
2. ✅ Add API keys to `.env`
3. ✅ Run `pip install -r requirements.txt`
4. ✅ Verify `ffmpeg -version` works

### ทุกครั้งก่อนรัน
1. เลือกสินค้าใน TikTok Shop Affiliate Marketplace
2. "Add to Showcase" → ได้ affiliate link
3. (Optional) ดาวน์โหลดรูปสินค้าใส่ `data/products/{name}.jpg`

### หลังรัน Pipeline (โพสจริง)
1. โอนคลิปจาก PC → มือถือ (LINE Keep / Google Drive)
2. TikTok app → + → upload → เปิด AI label toggle
3. Paste caption (ลบบรรทัด AI reminder)
4. Pin product จาก Showcase
5. Post

---

## 📊 Expected Performance

### Per Click
| Metric | Realistic Range |
|---|---|
| Render time | 4-7 นาที |
| File size | 3-7 MB |
| Resolution | 848x480 (480p) |
| Codec | H.264 + AAC |
| Duration | 30-35 วินาที |

### Per Day Production (ถ้าใช้ Cron 1 คลิป/วัน)
- Cost: $1.50/วัน = ~$45/เดือน (~1,575฿)
- Output: 30 คลิป/เดือน
- Manual time: ~3-5 นาที/คลิป (โพส + pin)

---

## 🚨 Known Issues + Workarounds

### Issue 1: Grok แสดง Thai text ในวิดีโอเพี้ยน
**Workaround:** ใส่ disclaimer + Day labels ผ่าน FFmpeg post-processing แทน
**Status:** ยังไม่ implement (low priority)

### Issue 2: Claude อาจส่ง category ไม่ตรง config
**ตัวอย่าง:** "Zinc Supplement" แทน "Zinc"
**Workaround:** Lookup supplement ผ่าน supplement_name parameter โดยตรง
**Status:** Pipeline ใช้ approach นี้แล้ว

### Issue 3: TikTok token หายหลัง Railway redeploy
**Workaround:** Reconnect ผ่าน `/tiktok-auth` endpoint
**Status:** ปกติ — ทำครั้งเดียวต่อ deploy

### Issue 4: Lutein image 500x500 (ต่ำกว่า 1024 อื่น)
**Workaround:** End-card scale รูปขึ้นอัตโนมัติ — quality acceptable
**Status:** Cosmetic only

---

## 🎬 Best Production Video (V2.1)

**File:** `data/downloads/20260430_211645_INZENT_Zinc_FINAL.mp4`

**Specs:**
- Title: "ลุงพัน ดุดอล! ผิวดูแลด้วยซิงค์"
- Duration: 35.1s
- Size: 3.1 MB
- Format: H.264 + AAC, 848x480

**Story Beats:**
- 0-15s: ดอลส่องกระจกเห็นผิวไม่สดใส → ลุงพันโผล่มาดุน่ารัก
- 15-30s: ลุงพันสอน "ซิงค์ช่วยเสริมการดูแลผิว" + time-skip + CTA
- 30-35s: End-card รูป INZENT Multi+Zinc Plus จริง

**Caption pre-generated:** `.caption.txt` (with AI label reminder + hashtags)

---

*อัปเดตล่าสุด: 2026-04-30 — V2.1 Production-Ready*
