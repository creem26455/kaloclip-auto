"""
Script Generator — Random Variety Mode
- Random เลือก: ตัวละคร + มุมกล้อง + สินค้า + mood + scenario + setting
- Claude เจน 2-scene script (ไทย + EN visual prompt) → JSON

Usage:
    python src/script_gen.py --count 5 --dry-run    # ทดสอบไม่ insert DB
    python src/script_gen.py --count 30             # production: insert 30 ตัวเข้า DB
"""

import argparse
import json
import os
import random
import sys

from dotenv import load_dotenv
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"), override=True)

from anthropic import Anthropic

sys.path.insert(0, os.path.dirname(__file__))
from variety_config import (
    MAIN_CHARACTER,
    EDUCATOR_CHARACTER,
    CAMEO_CHARACTERS,
    CAMERA_ANGLES,
    SUPPLEMENT_CATEGORIES,
    MOODS,
    SETTINGS,
    STYLE_PREFIX,
    STYLE_SUFFIX,
)
from compliance_rules import COMPLIANCE_INSTRUCTIONS, validate_script


def _pick_config(supplement_name: str | None = None) -> dict:
    """Random เลือก config 1 ชุด — supplement_name ระบุได้ (None = random)"""
    if supplement_name:
        # ค้นหาจาก name_th หรือ name_en (case insensitive)
        sl = supplement_name.strip().lower()
        match = next(
            (s for s in SUPPLEMENT_CATEGORIES
             if sl in s["name_th"].lower() or sl in s["name_en"].lower()),
            None,
        )
        if not match:
            available = ", ".join(s["name_en"] for s in SUPPLEMENT_CATEGORIES)
            raise ValueError(f"ไม่พบ supplement '{supplement_name}' — ที่มี: {available}")
        supplement = match
    else:
        supplement = random.choice(SUPPLEMENT_CATEGORIES)

    # Random เลือก cameo 0-2 ตัว
    num_cameo = random.choices([0, 1, 2], weights=[30, 50, 20])[0]
    cameos = random.sample(CAMEO_CHARACTERS, k=num_cameo) if num_cameo > 0 else []

    return {
        "character": MAIN_CHARACTER,
        "camera": random.choice(CAMERA_ANGLES),
        "supplement": supplement,
        "mood": random.choice(MOODS),
        "setting": random.choice(SETTINGS),
        "cameos": cameos,
    }


def _build_master_prompt(cfg: dict) -> str:
    s = cfg["supplement"]
    cameos = cfg.get("cameos", [])
    cameo_text = ""
    if cameos:
        cameo_text = "\n**ตัวละครเสริม (Cameo) — ใส่ในฉากด้วย ทำให้น่ารักและฮา:**\n"
        for c in cameos:
            cameo_text += f"\n- **{c['name_en']} ({c['name_th']}):** {c['description']}\n  Personality: {c['personality']}\n  Role: {c['typical_role']}\n"

    return f"""คุณคือ creative director ทำคลิปสั้น TikTok ขายอาหารเสริม สไตล์ "ลุงดุ" ที่กำลังฮิต

โจทย์: สร้าง script วิดีโอ 30 วินาที (2 ฉาก × 15 วิ) — ตัวละครหลัก 2 ตัว + cameo

**ตัวละครหลัก 1 (Dolla / ดอลอ้วน):** {cfg['character']}

**ตัวละครหลัก 2 (Uncle Pan / ลุงพัน — ลุงดุ):** {EDUCATOR_CHARACTER}
{cameo_text}

**Config สำหรับวิดีโอนี้:**
- มุมกล้อง: {cfg['camera']}
- สถานที่: {cfg['setting']}
- สินค้า: {s['name_th']} ({s['name_en']})
- กลุ่มเป้าหมาย: {s['target_th']}
- Mood: {cfg['mood']}

**Scene 1 (15s) — ปัญหา + ลุงโผล่มาดุน่ารัก:**
ใช้ scene1_idea: {s['scene1_idea']}
จบฉาก 1 ด้วย: Uncle Pan walks into frame with **stern comedy scolding face** —
one eyebrow raised, hands on hips, exasperated sigh "เห้อ!" —
strict like a comedy school teacher (NOT yelling in face, NOT pointing weapon)
and says with firm scolding tone:
"{s['scolding_th']}"

**Scene 2 (15s) — ลุงสอน + Time-skip narrative + Disclaimer + CTA:**
Uncle Pan explains in friendly tone: "{s['explanation_th']}"

**Visual MUST follow this pattern (NO instant transformation):**
{s['solution_visual']}

⚠️ ต้องมี text overlay เล็กๆ มุมจอ: "*ผลลัพธ์ขึ้นอยู่กับแต่ละบุคคล"
⚠️ ต้องมี time-skip cue (calendar pages, "Day 1 → Day 30" text, week labels)
⚠️ Result ต้อง "gradual" ไม่ "instant"

จบด้วย Dolla looking healthy and happy + CTA voice: "{s['cta_th']}"

{COMPLIANCE_INSTRUCTIONS}

**สำคัญมาก — กฎแข็งทุกข้อต้องตาม:**

1. **STYLE LOCK:** ทุก scene prompt ต้อง**ขึ้นต้นและจบ**ด้วยการระบุ "3D Pixar Disney cartoon animation, anthropomorphic red panda characters, NO real humans" — กัน Grok หลุดเป็นภาพคนจริง

2. **CHARACTER DESCRIPTION ครบทุก scene:**
   - ต้องเขียน "the chubby red panda Dolla with reddish-brown fur" ทั้ง scene 1 และ scene 2
   - ต้องเขียน "the older red panda Uncle Pan in brown teacher's vest with round eyeglasses" ทั้ง scene 1 และ scene 2
   - **ห้ามใช้แค่ "Uncle Pan" หรือ "Dolla" ลอยๆ — ต้องระบุ "red panda" ทุกครั้งที่กล่าวถึง**

3. **บทพูด:**
   - Uncle Pan = **ดุดัน เสียงดัง** สไตล์ลุงดุครูดุ TikTok (tough love comedy)
   - Dolla = น่ารัก กลัว ขอโทษ

4. **Product display:**
   - regular-sized (ขนาดของจริง) — ห้าม giant/massive
   - generic packaging — ห้าม brand logo

5. **NO HUMANS — กฎเหล็ก:**
   - ห้ามใช้คำว่า "man", "person", "human", "boy", "girl", "people"
   - ใช้ "red panda character" / "panda character" เท่านั้น
   - Uncle Pan = red panda ใส่ vest, ไม่ใช่คน

6. **PRODUCT NAME MENTION — กฎ TikTok Shop:**
   - บทพูด Uncle Pan ใน scene 2 ต้อง**พูดชื่อสินค้าภาษาไทยให้ชัด** อย่างน้อย 1 ครั้ง
   - เช่น "ต้องกิน{s['name_th']}!" หรือ "{s['name_th']}ของลุงนี่แหละ!"
   - CTA ตอนจบต้องพูดชื่อสินค้าอีกครั้ง — เช่น "กดสั่ง {s['name_th']} ในตะกร้า!"
   - ห้ามแค่ "อาหารเสริม" ลอยๆ — ต้องเจาะจงชื่อสินค้า

ตอบเป็น JSON object เท่านั้น (ห้าม markdown fence ห้ามอธิบาย):
{{
  "title": "ชื่อคลิปภาษาไทยสั้นๆ",
  "category": "{s['name_en']}",
  "scene1_prompt": "ขึ้นต้นด้วย '3D Pixar Disney cartoon animation, anthropomorphic red panda characters' + describe Dolla AND Uncle Pan as red pandas + visual + Thai dialogue in quotes",
  "scene2_prompt": "ขึ้นต้นด้วย '3D Pixar Disney cartoon animation, anthropomorphic red panda characters' + describe Dolla AND Uncle Pan as red pandas + visual + Thai dialogue in quotes + CTA"
}}
"""


def generate_one_script(supplement_name: str | None = None) -> dict:
    """Random config + Claude gen 1 script (supplement ระบุได้)"""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY ไม่ได้ตั้งค่า")

    cfg = _pick_config(supplement_name)
    master = _build_master_prompt(cfg)

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": master}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
    text = text.strip()

    script = json.loads(text)

    # ⚙️ Force-wrap ทุก scene ด้วย STYLE_PREFIX/SUFFIX
    # (ชั้นที่ 3 — กันถ้า Claude พลาดไม่ใส่)
    for key in ("scene1_prompt", "scene2_prompt"):
        body = script.get(key, "").strip()
        # ตัดออกถ้ามี style prefix อยู่แล้ว (เพื่อไม่ให้ซ้ำ)
        if not body.lower().startswith("3d pixar"):
            body = STYLE_PREFIX + body
        if "anthropomorphic animals" not in body.lower() and "no real humans" not in body.lower():
            body = body + STYLE_SUFFIX
        script[key] = body

    # เก็บ config ที่ใช้ไว้ (สำหรับ debug + tracking variety)
    script["_config"] = {
        "camera": cfg["camera"],
        "supplement": cfg["supplement"]["name_en"],
        "mood": cfg["mood"],
        "setting": cfg["setting"],
        "cameos": [c["name_en"] for c in cfg.get("cameos", [])],
    }
    return script


def generate_scripts(count: int = 1, supplement: str | None = None) -> list[dict]:
    label = f" supplement={supplement}" if supplement else " (random)"
    print(f"🎲 Generating {count} scripts{label}...")
    scripts = []
    for i in range(count):
        try:
            s = generate_one_script(supplement)
            scripts.append(s)
            print(f"  [{i+1}/{count}] ✅ {s.get('title', '?')} ({s['_config']['supplement']})")
        except Exception as e:
            print(f"  [{i+1}/{count}] ❌ {e}")
    return scripts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--supplement", type=str, default=None,
                        help="ระบุประเภท เช่น Collagen, Biotin, Vitamin C (ว่าง = random)")
    parser.add_argument("--dry-run", action="store_true", help="ไม่ insert เข้า DB แค่ print")
    parser.add_argument("--show-prompts", action="store_true", help="แสดง prompt เต็มๆ")
    args = parser.parse_args()

    scripts = generate_scripts(args.count, args.supplement)

    print("\n" + "=" * 60)
    for i, s in enumerate(scripts, 1):
        print(f"\n[{i}] {s.get('title', '?')}")
        print(f"    Camera:     {s['_config']['camera'][:60]}...")
        print(f"    Supplement: {s['_config']['supplement']}")
        print(f"    Mood:       {s['_config']['mood'][:50]}")
        print(f"    Scenario:   {s['_config']['scenario'][:50]}...")
        if args.show_prompts:
            print(f"\n    📹 Scene 1:\n    {s.get('scene1_prompt', '')[:500]}")
            print(f"\n    📹 Scene 2:\n    {s.get('scene2_prompt', '')[:500]}")
        else:
            print(f"    Scene 1:    {s.get('scene1_prompt', '')[:80]}...")
            print(f"    Scene 2:    {s.get('scene2_prompt', '')[:80]}...")
    print("\n" + "=" * 60)

    if args.dry_run:
        print("🚫 Dry-run: ไม่ insert เข้า DB")
        return

    from db import insert_scripts, count_pending
    inserted = insert_scripts(scripts)
    pending = count_pending()
    print(f"\n✅ Inserted {inserted} scripts")
    print(f"📊 Total pending in queue: {pending}")


if __name__ == "__main__":
    main()
