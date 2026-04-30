# TikTok Automation — Grok Imagine Video Bot

> ✅ **Production-Ready** — 2026-04-30
> ทดสอบ E2E ผ่าน 4 รอบ + Compliance Hardened V2.1

---

## ภาพรวม

ระบบสร้างวิดีโอสั้น TikTok Shop Affiliate อัตโนมัติ:
- 🤖 **Claude Haiku 4.5** เจน script ภาษาไทย (random หมวด/มุมกล้อง/setting)
- 🎬 **Grok Imagine Video** render 2 ฉาก × 15 วินาที (480p, native audio)
- 🎞️ **FFmpeg** merge + ต่อ end-card รูปสินค้าจริง
- 🛒 **Caption Generator** — Thai + hashtag + disclaimer + AI label reminder

---

## 🎭 Cast (Universe ตัวละคร)

### Main Cast (ทุกคลิป)
- 🦊 **ดอลอ้วน (Dolla)** — แพนด้าแดงอ้วน ตัวเอกมีปัญหา ขี้กลัว น่ารัก
- 👴 **ลุงพัน (Uncle Pan)** — แพนด้าแดงสูงวัย mentor ดุน่ารัก แว่น+vest+scroll

### Supporting Cast (random cameo)
- 🐱 **น้องเบลล์ (Bluebell)** — แมว British Shorthair สีบลู สาวหรู
- 🐼 **พี่หม่ำ (Mam)** — Giant Panda พี่ใหญ่ใจดี
- 🐕 **เจ้ามอจิ (Mochi)** — Shiba Inu เพื่อนซน

---

## 💊 หมวดสินค้า — 8 ประเภท (รูปสินค้าจริงพร้อม)

| # | หมวด | Brand จริง | ไฟล์ |
|---|---|---|---|
| 1 | ไฟเบอร์ดีท็อกซ์ | DONUTT Total Fibely | `fiber_jelly.jpg` |
| 2 | ซิงค์ ดูแลผิว | INZENT Multi+Zinc Plus | `zinc.jpg` |
| 3 | คอลลาเจน | DONUTT Collagen Di-Peptide | `collagen.jpg` |
| 4 | กาแฟ/โกโก้คุมหิว | DONUTT Cocoa | `diet_coffee.jpg` |
| 5 | ลูทีน | Blackmores Lutein-Vis | `lutein.jpg` |
| 6 | เวย์โปรตีน | Plantaé Complete | `plant_protein.jpg` |
| 7 | วิตามินซี | MEGA We Care NAT C 1000 | `vitamin_c.jpg` |
| 8 | โพรไบโอติก | Life-Space LSP080 | `probiotic.jpg` |

---

## 💰 Cost Per Video

| รายการ | Cost |
|---|---|
| Claude Haiku script gen | ~$0.001 |
| Grok Scene 1 (15s, 480p) | $0.75 |
| Grok Scene 2 (15s, 480p) | $0.75 |
| FFmpeg merge + end-card | ฟรี |
| **รวม 1 คลิป (35s)** | **$1.50 (~52฿)** |

**Budget Plans:**
- $25 → ~16 คลิป (ทดสอบ + 2 อาทิตย์โพส 1 คลิป/วัน)
- $75 → ~50 คลิป (~6 อาทิตย์)
- $150 → ~100 คลิป (~3 เดือน)

---

## 🛡️ Compliance Rules (V2.1 Hardened)

### Banned Content (ห้ามใน script + visual)
- ❌ "ตลอดกาล", "100%", "หาย", "FDA approved", "ผลทันที"
- ❌ "ลามทั้งหน้า", "พังหมด", "หายวับ", "ก่อนสายเกินไป"
- ❌ Instant magical transformation
- ❌ Aggressive Uncle Pan (ตะคอก, ไม้เรียว, ชี้หน้า)
- ❌ Re-seller watermarks (Pharma4U, Beauty Healthshop)

### Required Elements
- ✅ Time-skip narrative (Day 1 → Day 30) ในฉาก 2
- ✅ Disclaimer overlay: "*ผลลัพธ์ขึ้นอยู่กับแต่ละบุคคล"
- ✅ Soft CTA ("ลอง...ดูนะ" ไม่ใช่ "เร็ว!")
- ✅ AI-generated label toggle (manual ตอนโพส)
- ✅ FDA disclaimer ใน caption: "*อาหารเสริม ไม่มีผลในการป้องกันหรือรักษาโรค"

---

## 📁 โครงสร้างโฟลเดอร์

```
C:\tiktokautomation\
├── MASTER.md              ← ไฟล์นี้
├── FLOW.md                ← E2E pipeline detail
├── README.md
├── requirements.txt
├── .env                   ← API keys (gitignored)
├── .env.example
├── .gitignore
├── Dockerfile
├── Procfile
├── railway.json
├── supabase_schema.sql
├── app.py                 ← Flask dashboard + OAuth + Cron
├── src/
│   ├── grok_client.py     ← Grok Imagine Video API
│   ├── ffmpeg_merge.py    ← รวม 2 คลิป
│   ├── end_card.py        ← End-card 5s + product image
│   ├── caption_gen.py     ← TikTok caption + hashtag
│   ├── script_gen.py      ← Claude เจน script (random)
│   ├── tiktok_upload.py   ← Inbox API (port จาก kaloclip)
│   ├── telegram_notify.py
│   ├── pipeline.py        ← Full E2E orchestrator
│   ├── db.py              ← Supabase queue
│   ├── compliance_rules.py ← TikTok + อย. กฎ
│   ├── variety_config.py  ← 8 supplements + 10 cameras + 6 moods + 3 cameos
│   └── main.py            ← Phase 1 PoC
├── data/
│   ├── products/          ← รูปสินค้าจริง 8 หมวด
│   ├── downloads/         ← Final mp4 + caption.txt
│   └── temp/              ← Scene1/2 + cartoon merge
├── legacy/                ← Kaloclip docs (archived reference)
└── API_*.txt              ← API key references (gitignored)
```

---

## 🎬 Pipeline Flow

```
[1] Random Config: หมวด + camera + mood + setting + cameo
        ↓
[2] Claude Haiku → JSON script (Thai dialogue + EN visual)
        ↓
[3] Submit Grok 2 ฉาก parallel ($1.50)
        ↓ (~3-5 นาที)
[4] Wait + Download mp4 → /data/temp/
        ↓
[5] FFmpeg merge → 30s cartoon
        ↓
[6] [Hybrid mode] ต่อ end-card 5s รูปสินค้าจริง → 35s mp4
        ↓
[7] Caption gen → /data/downloads/{ts}.caption.txt
        ↓
[8] [Optional] TikTok Inbox upload + Telegram notify
        ↓
[9] BossMhee เปิด TikTok → Edit → ปักตะกร้า + AI label → Post
```

---

## ✅ ทดสอบที่ผ่านมา (Production Quality)

| Test | Cost | Result |
|---|---|---|
| Pixza farmer 3D test | $0.75 | ✅ Style works |
| Red panda Thai voice | $0.75 | ✅ Character good |
| V1 Probiotic (no end-card) | $1.50 | ✅ ผ่าน UI ทดสอบ |
| V1 Probiotic Hybrid (placeholder) | +FFmpeg | ✅ End-card flow ผ่าน |
| Lutein Audio Mode | $1.50 | ✅ Fallback ทำงาน |
| **V1 INZENT Zinc Hybrid** | $1.50 | ✅ Production-grade |
| **V2 INZENT Zinc (compliance hardened)** | $1.50 | ✅ Soft tone |
| **V2.1 INZENT Zinc Final (Uncle Pan ดุนิดเดียว)** | $1.50 | ✅ ⭐ Best |

**Cost ใช้ไปทั้งหมด:** $14.21 / $25 (เหลือ $10.79 = ~7 คลิป)

---

## 🚀 Status & Next Steps

### ✅ ที่ทำแล้ว
- [x] Phase 1: Grok API integration
- [x] Phase 2: Claude script gen + Variety config
- [x] Phase 3: TikTok upload + Telegram + End-card
- [x] Compliance V2.1 (TikTok + อย. hardened)
- [x] 8 หมวดสินค้า + รูปสินค้าจริง 8 รูป
- [x] Universe characters (Dolla, Uncle Pan + 3 cameos)
- [x] Caption generator + AI label reminder

### ⏭️ ขั้นต่อไป
- [ ] BossMhee โพสคลิป INZENT Zinc V2.1 ทดสอบ TikTok จริง
- [ ] Track engagement (views, clicks, conversions) 24-48 ชม.
- [ ] ถ้าผ่าน → Setup Supabase + batch gen 30 scripts
- [ ] Deploy Railway + Cron 09:00 daily
- [ ] Reconnect TikTok OAuth (token หาย)

---

## 🔑 Credentials (Reuse จาก Kaloclip)

ทั้งหมดใน `.env` (gitignored):
- ✅ XAI_API_KEY (Grok Imagine)
- ✅ ANTHROPIC_API_KEY (Claude Haiku)
- ✅ SUPABASE_URL + KEY (จาก Gridbot project)
- ✅ TIKTOK_CLIENT_KEY + SECRET
- ✅ TELEGRAM_TOKEN + CHAT_ID

Railway service เดิม: `9d84badf-bca0-4afa-b07c-d98805d0e526`

---

*อัปเดตล่าสุด: 2026-04-30 21:30 — Production V2.1 พร้อมโพสทดสอบ*
