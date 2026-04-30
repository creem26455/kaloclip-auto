# TikTok Automation — Grok Imagine Video Bot

ระบบสร้างวิดีโอ TikTok อัตโนมัติด้วย Grok Imagine API

## Quick Start (Phase 1 — Proof of Concept)

### 1. Install
```bash
pip install -r requirements.txt
```

### 2. ติดตั้ง FFmpeg
- Windows: `winget install ffmpeg` หรือดาวน์โหลดจาก https://ffmpeg.org/
- เช็ค: `ffmpeg -version`

### 3. ตั้ง ENV
```bash
cp .env.example .env
# แก้ .env ให้ใส่ XAI_API_KEY
```

### 4. รัน Test
```bash
python src/main.py
```
จะได้ไฟล์ผลลัพธ์ที่ `data/downloads/{timestamp}_Cute_Puppy_Adventure.mp4` (30 วินาที)

## ค่าใช้จ่าย
- 1 คลิป (30s): ~$2.10 (~75฿)
- 30 คลิป/เดือน: ~$63 (~2,250฿)

## Phases
- [x] **Phase 1**: PoC — Hardcoded prompt → Grok → FFmpeg merge
- [ ] **Phase 2**: Claude เจน script → Supabase queue
- [ ] **Phase 3**: TikTok auto-upload + Telegram notify + Cron

ดูรายละเอียดเพิ่มเติมใน `MASTER.md`
