"""
Caption Generator — สร้าง TikTok caption พร้อม hashtag
ใช้ตอนโพสต์ — ใส่ชื่อสินค้าชัด + tag relevant ให้ AI bot ของ TikTok เห็น
"""

import random


HASHTAG_BANK = {
    "Fiber Detox Jelly": ["#ไฟเบอร์", "#ดีท็อกซ์", "#พุงยุบ", "#ขับถ่ายดี", "#ลำไส้แข็งแรง"],
    "Zinc": ["#ซิงค์", "#ลดสิว", "#สิวฮอร์โมน", "#หน้าใส", "#สกินแคร์"],
    "Collagen Drink": ["#คอลลาเจน", "#ผิวใส", "#ผิวเด้ง", "#ออร่า", "#beauty"],
    "Diet Coffee": ["#กาแฟคุมหิว", "#ลดน้ำหนัก", "#คุมหิว", "#diet"],
    "Lutein": ["#ลูทีน", "#บำรุงสายตา", "#ตาแห้ง", "#เกมเมอร์", "#สายตา"],
    "Plant Protein": ["#โปรตีน", "#เวย์โปรตีน", "#fitness", "#ออกกำลังกาย"],
    "Vitamin C": ["#วิตามินซี", "#ภูมิคุ้มกัน", "#ผิวใส", "#สุขภาพ"],
    "Probiotic": ["#โพรไบโอติก", "#ลำไส้ดี", "#ท้องอืด", "#guthealth"],
}

UNIVERSAL_TAGS = [
    "#TikTokShop", "#TikTokShopThailand", "#กดตะกร้า",
    "#ลุงพัน", "#ดอลอ้วน", "#แพนด้าแดง",
    "#อาหารเสริม", "#supplement",
]


def generate_caption(supplement: dict, title_th: str, max_chars: int = 2200) -> str:
    """
    สร้าง caption สำหรับ TikTok post

    ส่วนประกอบ:
    1. Hook (อิงจาก title)
    2. Product mention (ชื่อสินค้าไทย + EN)
    3. Benefits (จาก config)
    4. CTA
    5. Hashtags
    """
    name_th = supplement["name_th"]
    name_en = supplement["name_en"]
    target = supplement.get("target_th", "")
    cta = supplement.get("cta_th", "กดสั่งในตะกร้าเลย!")

    # Disclaimer (อย. compliance)
    disclaimer = "*ผลลัพธ์อาจแตกต่างกันในแต่ละบุคคล\n*อาหารเสริม ไม่มีผลในการป้องกันหรือรักษาโรค"

    # Hashtags
    specific = HASHTAG_BANK.get(name_en, [])
    universal = random.sample(UNIVERSAL_TAGS, k=min(5, len(UNIVERSAL_TAGS)))
    hashtags = " ".join(specific[:5] + universal)

    caption = f"""⚠️ ก่อนโพส: เปิด Toggle "AI-generated content" ใน TikTok upload settings ก่อนเสมอ

━━━━━━━━━━━━━━━━━━━━━━━━━━

{title_th}

🛒 สินค้า: {name_th} ({name_en})
👥 เหมาะกับ: {target}

✨ {cta}
👇 กดตะกร้าด้านล่างได้เลยจ้า

{disclaimer}

{hashtags}"""

    if len(caption) > max_chars:
        caption = caption[:max_chars - 3] + "..."

    return caption


if __name__ == "__main__":
    test = {
        "name_th": "โพรไบโอติก",
        "name_en": "Probiotic",
        "target_th": "คนท้องอืด สุขภาพลำไส้ไม่ดี",
        "cta_th": "ลำไส้ดี ผิวสวย! กดสั่งในตะกร้าเดี๋ยวนี้!",
    }
    print(generate_caption(test, "ลุงพัน vs ลำไส้พัง 💊"))
