"""
TikTok + Thai FDA Compliance Rules
=========================================================
อัปเดต: 2026-04-30 (BossMhee สั่งให้ตรวจทุก script + video)

⚠️ ทุก script ที่ Claude เจน + ทุก prompt ที่ส่ง Grok
ต้องผ่านกฎเหล่านี้ — ป้องกัน TikTok ban / Shop disabled / โดน อย. ปรับ
"""

# ============================================================
# 1. HEALTH CLAIMS — ห้ามอย่างเด็ดขาด
# ============================================================

BANNED_HEALTH_CLAIMS = [
    # คำที่ห้ามใช้ในบทพูด/visual text/prompt
    # หมายเหตุ: ลบ "รักษาโรค" ออก เพราะเป็นส่วนของ disclaimer มาตรฐาน อย.
    # ("ไม่มีผลในการป้องกันหรือรักษาโรค")
    "รักษาให้หาย", "รักษาหายขาด", "100% หาย", "หายขาด", "หายเด็ดขาด",
    "ตลอดกาล", "ไปตลอดกาล", "ตลอดชีวิต",
    "FDA approved", "อ.ย. รับรอง",
    "ลด 10 kg ใน 7 วัน", "ลด N กก. ใน N วัน",
    "ป้องกันมะเร็ง", "รักษาเบาหวาน", "หายความดัน",
    "ผลทันที", "instant cure", "instant transformation", "miracle",
    "เปลี่ยนชีวิต", "life-changing supplement",
    # v2: คำใหม่ที่ AI feedback เตือน
    "ลามทั้งหน้า", "ก่อนสายเกินไป", "เร่งด่วน",
    "พังหมด", "พังแล้ว",
    "หายวับ", "หายเป็นปลิดทิ้ง",
    # Prompt-level banned (Grok render keywords)
    "magical sparkles disappear pimple", "instant transformation",
    "pimple poofs away", "deflates dramatically",
    "muscles inflate one-by-one",
]

# คำที่อนุญาตใช้แทน
SAFE_ALTERNATIVES = {
    "รักษา": "ดูแล / บำรุง / ช่วยให้",
    "หาย": "ดีขึ้น / สบายขึ้น",
    "ป้องกัน": "เสริม / สนับสนุน",
    "ลด N kg": "เสริมการคุมน้ำหนัก",
    "ผลทันที": "ผลใน N วัน / สังเกตได้ใน N สัปดาห์",
}


# ============================================================
# 2. PRODUCT DISPLAY — กฎการโชว์สินค้า
# ============================================================

PRODUCT_DISPLAY_RULES = """
**ขนาดสินค้า:**
- ❌ ห้ามขยายขวด/ซองให้ใหญ่ผิดสัดส่วน เช่น "giant magical bottle"
- ✅ ต้องเป็นขนาดของจริงในมือตัวละคร (proportional to character)
- ✅ คำว่า "regular-sized supplement bottle" หรือ "normal-sized sachet"

**Magical effects:**
- ❌ ห้าม "instant transformation" รุนแรงเกินจริง (เช่น แก่ → หนุ่มเลย)
- ✅ Magical sparkles อนุญาต — แต่เป็น "mood" ไม่ใช่ "ผลจริง"
- ✅ Visual metaphor (เช่น เกราะป้องกัน, ออร่า) เป็น cartoon style ได้

**Brand/Logo:**
- ❌ ห้ามโชว์ logo brand จริง (เช่น Mega We Care, Blackmores)
- ✅ ใช้ generic packaging "supplement bottle with simple label"
- ✅ ถ้ามี brand เอง ใส่ชื่อ brand ของเราเองได้

**Competitor products:**
- ❌ ห้ามแสดง competitor brand
- ❌ ห้ามเปรียบเทียบกับยี่ห้ออื่น
"""


# ============================================================
# 3. AUDIENCE & SAFETY
# ============================================================

AUDIENCE_RULES = """
**กลุ่มเป้าหมาย:**
- ❌ ห้าม target เด็กอายุต่ำกว่า 18
- ❌ ห้ามใส่ตัวละครเด็กในวิดีโอขายอาหารเสริม
- ✅ ตัวละครต้องดู adult/วัยทำงาน (animal character ไม่มีปัญหานี้)

**Medical advice:**
- ❌ ห้ามแนะนำให้เลิกยาที่หมอสั่ง
- ❌ ห้ามแสดงตัวเองเป็นหมอ/นักวิชาการที่ไม่มีอยู่จริง
- ✅ Uncle Pan = friendly mentor ไม่ใช่หมอ — ห้ามใส่เครื่องแบบหมอ/พยาบาล

**Body image:**
- ⚠️ ใช้ "พุงป่อง/ผอม/อ้วน" ระวังให้เป็น cartoon comedy ไม่ body shaming
- ✅ Tone ต้อง playful และ uplifting ไม่ดูถูก
- ❌ ห้าม "ผอมเฉพาะที่สวย" / "อ้วนน่าเกลียด"
"""


# ============================================================
# 4. AI-GENERATED CONTENT DISCLOSURE
# ============================================================

AI_DISCLOSURE_RULES = """
**TikTok บังคับ disclose AI-generated content:**
- ทุกคลิปที่ generate ด้วย AI ต้องติดป้าย "AI-generated" ตอน publish
- bot ของเราจะใช้ TikTok upload API ที่รองรับ flag "ai_generated_video"
- หรือ user ต้อง toggle "AI-generated content" ใน TikTok app ตอน publish

**ในวิดีโอ:**
- ✅ คาแร็คเตอร์ cartoon ไม่ต้องระบุว่า "AI made"
- ✅ ถ้ามีคนจริง — ต้องบอกว่า "AI-generated person" (แต่เราใช้แต่ cartoon)
"""


# ============================================================
# 5. THAI FDA (อย.) — สำหรับอาหารเสริมในไทย
# ============================================================

THAI_FDA_RULES = """
**Disclaimer ภาษาไทยที่ต้องใส่ (ถ้าโพสในไทย):**

ในข้อความ caption หรือ on-screen text ต้องมี:
"*ผลลัพธ์อาจแตกต่างกันในแต่ละบุคคล"
"*อาหารเสริม ไม่มีผลในการป้องกันหรือรักษาโรค"

**ห้ามอ้าง:**
- ❌ "เลขที่ อย. xxxxxx" ถ้าไม่มีจริง
- ❌ "ผ่านการรับรอง FDA" ถ้าไม่ได้รับ
- ❌ "งานวิจัยจาก Harvard" ถ้าอ้างไม่มีอยู่จริง

**ใส่ได้:**
- ✅ "ส่วนผสมจากธรรมชาติ"
- ✅ "ผ่านการตรวจสอบคุณภาพในประเทศไทย"
"""


# ============================================================
# 6. CTA LANGUAGE — บทพูดที่ปลอดภัย
# ============================================================

SAFE_CTA_TEMPLATES = [
    "กดสั่งในตะกร้าได้เลยจ้า!",
    "สั่งในแอปพลิเคชัน TikTok Shop ได้เลย",
    "กดตะกร้าเลย ส่งฟรี!",
    "อยากลองมั้ยคะ กดดูในตะกร้าเลย",
    "เก็บปลายทางได้นะคะ กดสั่งเลย",
]

UNSAFE_CTA = [
    # อย่าใช้
    "ซื้อเลย หายแน่!",
    "100% ไม่หายคืนเงิน!",
    "FDA approved!",
    "หมอแนะนำ!",
]


# ============================================================
# 7. COMBINED MASTER PROMPT (ใส่ใน script_gen.py)
# ============================================================

COMPLIANCE_INSTRUCTIONS = """
**กฎ TikTok + อย. ที่ต้องปฏิบัติตามทุก script (v2 — Hardened):**

1. **ห้ามอ้างผลทางการแพทย์เกินจริง:**
   - ห้ามใช้คำ: รักษา, หาย, 100%, ตลอดกาล, FDA approved, ผลทันที, instant
   - ห้ามใช้: "ลามทั้งหน้า", "พังหมด", "หายวับ", "ก่อนสายเกินไป"
   - ใช้แทน: "ดูแล / บำรุง / เสริม / ช่วยให้ / ตัวช่วย"

2. **🚨 NEW v2: ห้าม Instant Transformation — บังคับ Time-skip narrative:**
   - ❌ ห้าม "magical sparkles + instant cure" / "pimple disappears in seconds"
   - ❌ ห้าม "muscles inflate dramatically" / "belly deflates instantly"
   - ✅ ต้องเป็น: "ทานทุกวัน → time skip (Day 1, Day 7, Day 30)"
   - ✅ Show calendar pages flipping or text overlay "Week 1, Week 4"
   - ✅ Result ค่อยเป็นค่อยไป (gradual improvement)

3. **🚨 NEW v2: บังคับ Disclaimer text overlay ใน Scene 2:**
   - มี text เล็กๆ มุมจอ: "*ผลลัพธ์ขึ้นอยู่กับแต่ละบุคคล"
   - หรือ "*อาหารเสริม ไม่มีผลในการป้องกันหรือรักษาโรค"

4. **🚨 NEW v2: Uncle Pan = Caring Mentor (ไม่ใช่ Bully):**
   - ❌ ห้ามไม้เรียวจี้หน้า, ตะคอก, screaming
   - ❌ ห้ามชี้ pointer aggressive ที่ตัวละคร
   - ✅ Tone: stern but caring, friendly advice
   - ✅ Hold scroll/clipboard แทนไม้
   - ✅ Stand arms-crossed with frown (not threatening)

5. **สินค้าในฉาก:**
   - ขนาดของจริงเท่านั้น (regular-sized bottle/sachet)
   - Generic packaging — ห้าม brand logo
   - Magical effects = subtle (sparkles for "ambient mood" only)

6. **Body image — comedy ไม่ shaming:**
   - ตัวละครต้องดู adorable ตลอด
   - หลีกเลี่ยงเสียดสีรูปร่าง — focus on "feeling better"

7. **CTA ปลอดภัย (v2 — softer):**
   - ✅ "ลองสั่งในตะกร้าได้เลยจ้า"
   - ✅ "อยากดูแล... ลองดูนะ"
   - ❌ ห้าม "เร็ว!", "อย่ารอ!", "ก่อนสายเกินไป!"
   - ❌ ห้าม "หายแน่นอน 100%", "FDA approved"

8. **Dolla = adult cartoon, NOT child**
9. **Uncle Pan = vest + glasses + scroll (ห้าม doctor/medical uniform)**
"""


def get_compliance_summary() -> str:
    """ใช้ใส่ใน Claude master prompt"""
    return COMPLIANCE_INSTRUCTIONS


def validate_script(script: dict) -> tuple[bool, list[str]]:
    """
    เช็คว่า script ที่ Claude เจนผ่านกฎไหม
    Return (passed, list_of_issues)
    """
    issues = []
    text_to_check = " ".join([
        script.get("title", ""),
        script.get("scene1_prompt", ""),
        script.get("scene2_prompt", ""),
    ]).lower()

    for banned in BANNED_HEALTH_CLAIMS:
        if banned.lower() in text_to_check:
            issues.append(f"พบคำต้องห้าม: '{banned}'")

    # เช็คขนาดสินค้า
    if any(word in text_to_check for word in ["giant bottle", "huge supplement", "massive pill"]):
        issues.append("สินค้าขนาดเกินจริง — ใช้ 'regular-sized' แทน")

    # เช็คเครื่องแบบหมอ
    if any(word in text_to_check for word in ["doctor coat", "white coat", "stethoscope", "lab coat"]):
        issues.append("Uncle Pan ห้ามใส่ชุดหมอ — ใช้ vest/glasses เท่านั้น")

    return len(issues) == 0, issues
