"""
Kaloclip Auto — สร้างวิดีโอจาก Kalodata Top 7 สินค้า วนลำดับทีละวัน
วันที่ 1 → #1, วันที่ 2 → #2, ... วันที่ 7 → #7, รอบใหม่ → ดึง Top 7 ใหม่
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

# ===== CONFIG =====
HEADLESS = False          # False = เปิด browser ให้เห็น
TOP_N = 7                 # จำนวนสินค้าใน 1 รอบ
KALODATA_URL = "https://www.kalodata.com/product"
COOKIES_FILE = "session_cookies.json"
STATE_FILE = "state.json"
OUTPUT_DIR = "downloads"

# ==================

def load_state():
    """โหลดสถานะ: ทำถึงสินค้าลำดับไหนแล้ว + รายการ 7 สินค้า"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"index": 0, "products": [], "last_run": None}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def save_cookies(cookies):
    with open(COOKIES_FILE, "w") as f:
        json.dump(cookies, f)

def load_cookies():
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE) as f:
            return json.load(f)
    return None

# ==================

async def ensure_logged_in(page, context):
    """เช็คว่า login อยู่ไหม ถ้าไม่ → ให้ BossMhee login มือ แล้วบันทึก session"""
    await page.goto(KALODATA_URL, wait_until="networkidle")
    await page.wait_for_timeout(2000)

    # เช็ค login โดยดูว่ามี "เข้าสู่ระบบ" ปรากฏไหม
    login_text = await page.query_selector('text="เข้าสู่ระบบ"')
    en_login = await page.query_selector('text="Sign in"')

    if login_text or en_login:
        print("=" * 50)
        print("⚠️  ยังไม่ได้ Login!")
        print("กรุณา Login ด้วย Gmail ใน browser ที่เปิดอยู่")
        print("เมื่อ Login เสร็จแล้ว กลับมากด Enter ที่นี่")
        print("=" * 50)
        input(">>> กด Enter หลัง Login เสร็จ...")
        # บันทึก cookies
        cookies = await context.cookies()
        save_cookies(cookies)
        print("✅ บันทึก session เรียบร้อย ครั้งหน้าไม่ต้อง login อีก")
    else:
        print("✅ Login อยู่แล้ว")

async def get_top7_products(page):
    """ดึงรายการ Top 7 สินค้าจากหน้า Kalodata ranking"""
    print(f"📊 กำลังดึง Top {TOP_N} สินค้าจากชาร์ต...")

    await page.goto(KALODATA_URL, wait_until="networkidle")
    await page.wait_for_timeout(3000)

    products = []

    # วิธีที่ 1: ดักจับ network request ที่ Kalodata ส่งมา (เร็วกว่า scrape)
    # วิธีที่ 2: Scrape จาก DOM table
    # ลองหา rows ในตาราง
    rows = await page.query_selector_all("table tbody tr")
    if not rows:
        # ลอง selector อื่น
        rows = await page.query_selector_all('[class*="tableRow"], [class*="table-row"]')

    print(f"พบ {len(rows)} แถวในตาราง")

    for i, row in enumerate(rows[:TOP_N]):
        try:
            # ดึงชื่อสินค้า
            name_el = await row.query_selector('[class*="name"], [class*="title"], td:nth-child(2)')
            name = await name_el.inner_text() if name_el else f"สินค้าลำดับ {i+1}"
            name = name.strip()[:60]

            # ดึง link ของสินค้า (เพื่อหา productId)
            link_el = await row.query_selector("a[href]")
            href = await link_el.get_attribute("href") if link_el else ""

            products.append({
                "rank": i + 1,
                "name": name,
                "href": href,
                "row_index": i
            })
            print(f"  #{i+1}: {name[:40]}")
        except Exception as e:
            print(f"  ⚠️ ข้ามแถว {i+1}: {e}")

    return products

async def click_kaloclip_for_product(page, product):
    """เปิด Kaloclip สำหรับสินค้าที่เลือก"""
    print(f"\n🎬 สร้างคลิปสำหรับ: {product['name'][:50]}")

    # กลับไปหน้า ranking ก่อน
    await page.goto(KALODATA_URL, wait_until="networkidle")
    await page.wait_for_timeout(3000)

    rows = await page.query_selector_all("table tbody tr")
    if not rows:
        rows = await page.query_selector_all('[class*="tableRow"], [class*="table-row"]')

    if product["row_index"] < len(rows):
        target_row = rows[product["row_index"]]

        # Hover เพื่อให้ปุ่ม Kaloclip ปรากฏ (บางครั้ง hidden)
        await target_row.hover()
        await page.wait_for_timeout(500)

        # หาปุ่ม Kaloclip ในแถวนั้น
        kaloclip_btn = await target_row.query_selector('[class*="kaloclip"], text="Kaloclip"')
        if not kaloclip_btn:
            # ลองหา button ที่มีคำว่า AI หรือ video
            kaloclip_btn = await target_row.query_selector('button[class*="ai"], button[class*="video"]')

        if kaloclip_btn:
            await kaloclip_btn.click()
            print("✅ กด Kaloclip แล้ว")
            return True

    # ถ้าหาปุ่มในแถวไม่เจอ → กด Kaloclip button หลักแล้ว filter สินค้า
    kaloclip_main = await page.query_selector('text="Kaloclip AI สร้างวิดีโอ"')
    if kaloclip_main:
        await kaloclip_main.click()
        print("✅ กด Kaloclip หลักแล้ว")
        return True

    print("❌ หาปุ่ม Kaloclip ไม่เจอ")
    return False

async def fill_and_submit_kaloclip(page):
    """กรอกฟอร์ม Kaloclip 3 ขั้นตอน แล้ว Render"""
    print("\n📝 กรอกฟอร์ม Kaloclip...")

    # รอหน้า Kaloclip โหลด
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(2000)

    # === STEP 1: จุดขาย + ตั้งค่าเบื้องต้น ===
    print("  ขั้นตอน 1: เลือกจุดขาย...")

    # Check all selling point checkboxes
    checkboxes = await page.query_selector_all('input[type="checkbox"]')
    for cb in checkboxes:
        checked = await cb.is_checked()
        if not checked:
            await cb.click()
            await page.wait_for_timeout(200)

    print(f"  เลือก {len(checkboxes)} จุดขายแล้ว")

    # กดถัดไป (Step 1 → Step 2)
    await _click_next(page)
    await page.wait_for_timeout(2000)

    # === STEP 2: ตั้งค่าวิดีโอ ===
    print("  ขั้นตอน 2: ตั้งค่าวิดีโอ...")
    # ค่า default ที่เห็นในภาพ: 9:16, 20s, 720p — ปล่อย default ไว้ได้เลย
    await _click_next(page)
    await page.wait_for_timeout(2000)

    # === STEP 3: ตรวจสอบสคริปต์ → กด Generate ===
    print("  ขั้นตอน 3: สร้างวิดีโอ...")
    # หาปุ่ม generate / สร้างวิดีโอ / ยืนยัน
    for btn_text in ["สร้างวิดีโอ", "Generate", "ยืนยัน", "เริ่มสร้าง", "ต่อไป"]:
        btn = await page.query_selector(f'text="{btn_text}"')
        if btn:
            await btn.click()
            print(f"  กดปุ่ม '{btn_text}' แล้ว")
            break

async def _click_next(page):
    """กดปุ่มถัดไป"""
    for btn_text in ["ถัดไป", "Next", "ต่อไป"]:
        btn = await page.query_selector(f'text="{btn_text}"')
        if btn:
            await btn.click()
            print(f"  → กด '{btn_text}'")
            return
    print("  ⚠️ หาปุ่มถัดไปไม่เจอ")

async def wait_render_and_download(page):
    """รอ Render เสร็จแล้ว Download"""
    print("\n⏳ รอ Kalodata render วิดีโอ... (อาจใช้เวลา 1-3 นาที)")

    Path(OUTPUT_DIR).mkdir(exist_ok=True)

    try:
        # รอปุ่ม download ปรากฏ (timeout 5 นาที)
        download_btn = await page.wait_for_selector(
            'text="ดาวน์โหลด", text="Download", [class*="download"]',
            timeout=300_000
        )

        if download_btn:
            async with page.expect_download(timeout=60_000) as dl_info:
                await download_btn.click()
            download = await dl_info.value

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"kaloclip_{timestamp}.mp4"
            save_path = os.path.join(OUTPUT_DIR, filename)
            await download.save_as(save_path)
            print(f"✅ ดาวน์โหลดแล้ว: {save_path}")
            return save_path

    except Exception as e:
        print(f"⚠️ ดาวน์โหลด error: {e}")
        print("กรุณา download ด้วยมือจาก browser ที่เปิดอยู่")
        input("กด Enter เมื่อ download เสร็จ...")

    return None

# ==================

async def main():
    Path(OUTPUT_DIR).mkdir(exist_ok=True)

    state = load_state()

    print("=" * 55)
    print("  Kaloclip Auto — สร้างคลิปสินค้าขายดีอัตโนมัติ")
    print("=" * 55)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS, slow_mo=300)
        context = await browser.new_context(viewport={"width": 1366, "height": 768})

        # โหลด cookies ที่บันทึกไว้
        saved = load_cookies()
        if saved:
            await context.add_cookies(saved)
            print("✅ โหลด session เก่าแล้ว")

        page = await context.new_page()

        # Login check
        await ensure_logged_in(page, context)

        # ถ้า product list หมดหรือยังไม่มี → ดึง Top 7 ใหม่
        if not state["products"] or state["index"] >= TOP_N:
            print("\n🔄 ดึงรายการ Top 7 ใหม่...")
            state["products"] = await get_top7_products(page)
            state["index"] = 0
            save_state(state)

        if not state["products"]:
            print("❌ ดึงสินค้าไม่ได้ — ลองรันใหม่อีกครั้ง")
            await browser.close()
            return

        # เลือกสินค้าตาม index วันนี้
        current = state["products"][state["index"]]
        print(f"\n🎯 วันนี้ทำสินค้า #{current['rank']}: {current['name'][:50]}")
        print(f"   (รอบนี้ทำไปแล้ว {state['index']}/{TOP_N} ตัว)")

        # กด Kaloclip
        ok = await click_kaloclip_for_product(page, current)
        if not ok:
            print("\n⚠️  หาปุ่ม Kaloclip ไม่อัตโนมัติ")
            print("กรุณากดปุ่ม Kaloclip ด้วยมือใน browser แล้วกด Enter")
            input(">>> กด Enter เพื่อดำเนินการต่อ...")

        # กรอกฟอร์ม
        await fill_and_submit_kaloclip(page)

        # รอ render + download
        filepath = await wait_render_and_download(page)

        # อัปเดต state
        state["index"] += 1
        state["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save_state(state)

        # สรุป
        print("\n" + "=" * 55)
        if filepath:
            print(f"🎉 เสร็จ! วิดีโออยู่ที่: {filepath}")
        else:
            print("🎉 เสร็จแล้ว! ตรวจสอบโฟลเดอร์ downloads/")
        remaining = TOP_N - state["index"]
        print(f"📋 รอบนี้เหลืออีก {remaining} สินค้า")
        print("=" * 55)

        input("\nกด Enter เพื่อปิด browser...")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
