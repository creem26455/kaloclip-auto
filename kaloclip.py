"""
Kaloclip Bot — Playwright automation สำหรับ Kalodata
วน Top 7 สินค้า ทีละ 1 ตัวต่อวัน
"""

import json
import os
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

TOP_N = 7
KALODATA_URL = "https://www.kalodata.com/product"


class KaloclipBot:
    def __init__(self, cookies_file, state_file, output_dir, log_fn=print):
        self.cookies_file = cookies_file
        self.state_file = state_file
        self.output_dir = output_dir
        self.log = log_fn
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    def load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, encoding="utf-8") as f:
                return json.load(f)
        return {"index": 0, "products": [], "last_run": None, "last_video": None}

    def save_state(self, state):
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def load_cookies(self):
        with open(self.cookies_file) as f:
            return json.load(f)

    def load_session(self):
        """โหลด Kalodata session จาก env vars"""
        return {
            "_l_KPLiPs": os.environ.get("KALO_TOKEN", ""),
            "device_uuid": os.environ.get("KALO_DEVICE", ""),
            "userName": os.environ.get("KALO_USER", ""),
            "region": "TH",
            "phonePrefix": "66",
            "phoneRegion": "TH",
        }

    async def inject_session(self, context, session):
        """Inject localStorage ผ่าน add_init_script — ทำงานก่อนโหลดทุกหน้า ไม่ต้อง navigate"""
        js_lines = [f"localStorage.setItem({json.dumps(k)}, {json.dumps(v)})" for k, v in session.items() if v]
        js = ";\n".join(js_lines)
        await context.add_init_script(f"() => {{ try {{ {js}; }} catch(e) {{}} }}")
        self.log("✅ Inject session สำเร็จ")

    async def run(self):
        state = self.load_state()
        session = self.load_session()

        if not session.get("_l_KPLiPs"):
            self.log("❌ ไม่พบ KALO_TOKEN — กรุณาตั้งค่า env vars")
            return

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ]
            )
            context = await browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
            )
            page = await context.new_page()

            # Inject session ก่อน (ใช้ context เพื่อให้ทำงานก่อนโหลดทุกหน้า)
            await self.inject_session(context, session)

            try:
                # ดึง Top 7 ใหม่ถ้าหมดรอบ
                if not state.get("products") or state.get("index", 0) >= TOP_N:
                    self.log("🔄 ดึง Top 7 สินค้าใหม่...")
                    env_products = os.environ.get("KALO_PRODUCTS", "")
                    if env_products:
                        try:
                            state["products"] = json.loads(env_products)
                            self.log(f"✅ โหลด {len(state['products'])} สินค้าจาก env")
                        except Exception as e:
                            self.log(f"⚠️ parse env products error: {e}")
                            state["products"] = await self._get_top_products(page)
                    else:
                        state["products"] = await self._get_top_products(page)
                    state["index"] = 0
                    self.save_state(state)

                if not state["products"]:
                    self.log("❌ ดึงสินค้าไม่ได้ — อาจต้อง refresh cookies")
                    return

                idx = state.get("index", 0)
                product = state["products"][idx]
                self.log(f"🎯 สินค้า #{product['rank']}: {product['name'][:50]}")

                # ไปหน้า Kaloclip
                ok = await self._open_kaloclip(page, product)
                if not ok:
                    self.log("❌ เปิด Kaloclip ไม่ได้")
                    return

                # กรอกฟอร์ม
                await self._fill_form(page)

                # รอ render + download
                filepath = await self._download_video(page, product)

                # อัปเดต state
                state["index"] = idx + 1
                state["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                state["last_video"] = filepath
                self.save_state(state)

                self.log(f"✅ เสร็จ! เหลืออีก {TOP_N - state['index']} สินค้าในรอบนี้")

                # แจ้ง Telegram
                from notify import send_message, send_video
                msg = (f"🎬 <b>Kaloclip Auto</b>\n"
                       f"✅ สร้างคลิปเสร็จแล้ว!\n\n"
                       f"📦 สินค้า: {product['name'][:50]}\n"
                       f"📋 รอบนี้: {state['index']}/{TOP_N}\n"
                       f"🕐 {state['last_run']}")
                if filepath:
                    await send_video(filepath, caption=msg)
                else:
                    await send_message(msg)

            except Exception as e:
                self.log(f"❌ Error: {e}")
                raise
            finally:
                await browser.close()

    async def _get_top_products(self, page):
        await page.goto(KALODATA_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)

        products = []

        # ดักจับ API response ที่ Kalodata ใช้ภายใน
        # ลอง scrape table DOM
        rows = await page.query_selector_all("table tbody tr")
        if not rows:
            rows = await page.query_selector_all('[class*="tableRow"]')

        self.log(f"พบ {len(rows)} แถวในตาราง")

        for i, row in enumerate(rows[:TOP_N]):
            try:
                # ดึงชื่อสินค้า
                name_el = await row.query_selector('[class*="name"], td:nth-child(2)')
                name = (await name_el.inner_text()).strip()[:80] if name_el else f"สินค้า #{i+1}"

                # ดึง link
                link_el = await row.query_selector("a[href*='product']")
                href = await link_el.get_attribute("href") if link_el else ""

                # ดึง product ID จาก href
                product_id = ""
                if "productId=" in href:
                    product_id = href.split("productId=")[1].split("&")[0]
                elif "/product/" in href:
                    product_id = href.split("/product/")[-1].split("?")[0]

                products.append({
                    "rank": i + 1,
                    "name": name,
                    "href": href,
                    "product_id": product_id,
                    "row_index": i
                })
                self.log(f"  #{i+1}: {name[:40]}")
            except Exception as e:
                self.log(f"  ข้ามแถว {i+1}: {e}")

        return products

    async def _open_kaloclip(self, page, product):
        # ใช้ id หรือ product_id (รองรับทั้งสองแบบ)
        pid = product.get("id") or product.get("product_id")
        if pid:
            kaloclip_url = f"https://clip.kalowave.com/video-creating?productId={pid}&country=th"
            self.log(f"🔗 เปิด Kaloclip: {kaloclip_url}")
            await page.goto(kaloclip_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(4000)
            return True

        self.log("⚠️ ไม่มี product id")
        return False

    async def _fill_form(self, page):
        self.log("📝 กรอกฟอร์ม...")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        # Step 1 — เลือกจุดขายทั้งหมด
        checkboxes = await page.query_selector_all('input[type="checkbox"]')
        checked_count = 0
        for cb in checkboxes:
            if not await cb.is_checked():
                await cb.click()
                await page.wait_for_timeout(150)
                checked_count += 1
        self.log(f"  เลือก {len(checkboxes)} จุดขาย")

        # กดถัดไป
        await self._click_next(page)
        await page.wait_for_timeout(2000)

        # Step 2 — ตั้งค่าวิดีโอ (ปล่อย default: 9:16, 20s, 720p)
        await self._click_next(page)
        await page.wait_for_timeout(2000)

        # Step 3 — สร้างวิดีโอ
        for btn_text in ["สร้างวิดีโอ", "Generate", "ยืนยัน", "เริ่มสร้าง"]:
            btn = await page.query_selector(f'text="{btn_text}"')
            if btn:
                await btn.click()
                self.log(f"  กด '{btn_text}'")
                break

    async def _click_next(self, page):
        for text in ["ถัดไป", "Next", "ต่อไป"]:
            btn = await page.query_selector(f'text="{text}"')
            if btn:
                await btn.click()
                self.log(f"  → กด '{text}'")
                return

    async def _download_video(self, page, product):
        self.log("⏳ รอ render... (1-3 นาที)")

        try:
            download_btn = await page.wait_for_selector(
                'text="ดาวน์โหลด", text="Download", [class*="download-btn"]',
                timeout=300_000  # 5 นาที
            )
            if download_btn:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_name = "".join(c for c in product["name"][:20] if c.isalnum() or c in "- _")
                filename = f"{timestamp}_{safe_name}.mp4"
                save_path = os.path.join(self.output_dir, filename)

                async with page.expect_download(timeout=60_000) as dl_info:
                    await download_btn.click()
                dl = await dl_info.value
                await dl.save_as(save_path)
                self.log(f"✅ บันทึก: {filename}")
                return save_path

        except Exception as e:
            self.log(f"⚠️ Download error: {e}")

        return None
