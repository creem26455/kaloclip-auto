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

    def load_kwave_session(self):
        """โหลด Kalowave (clip.kalowave.com) session จาก env vars"""
        return {
            "access_token": os.environ.get("KWAVE_ACCESS_TOKEN", ""),
            "_l_KPLiPs": os.environ.get("KWAVE_TOKEN", ""),
            "device_uuid": os.environ.get("KWAVE_DEVICE", ""),
            "userName": os.environ.get("KALO_USER", ""),
            "language": "th-TH",
            "phonePrefix": "66",
            "phoneRegion": "TH",
        }

    async def inject_session(self, context, session):
        """Inject localStorage ตาม domain — kalodata.com และ kalowave.com ใช้ token ต่างกัน"""
        kwave = self.load_kwave_session()

        # สร้าง JS สำหรับ kalodata.com
        kalo_lines = [f"localStorage.setItem({json.dumps(k)}, {json.dumps(v)})"
                      for k, v in session.items() if v]
        kalo_js = ";\n".join(kalo_lines)

        # สร้าง JS สำหรับ kalowave.com
        kwave_lines = [f"localStorage.setItem({json.dumps(k)}, {json.dumps(v)})"
                       for k, v in kwave.items() if v]
        kwave_js = ";\n".join(kwave_lines)

        # Inject ตาม domain
        script = f"""() => {{
            try {{
                var host = window.location.hostname;
                if (host.includes('kalowave.com')) {{
                    {kwave_js};
                }} else {{
                    {kalo_js};
                }}
            }} catch(e) {{}}
        }}"""
        await context.add_init_script(script)

        # เพิ่ม Authorization: Bearer header ให้ทุก API request ไป kalowave.com
        access_token = kwave.get("access_token", "")
        if access_token:
            async def add_auth_header(route):
                headers = {**route.request.headers, "Authorization": f"Bearer {access_token}"}
                await route.continue_(headers=headers)
            await context.route("**kalowave.com**", add_auth_header)
            self.log("✅ Inject session สำเร็จ (kalodata + kalowave + Bearer token)")
        else:
            self.log("✅ Inject session สำเร็จ (kalodata + kalowave)")

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
                # แวะ kalodata.com ก่อน เพื่อให้ session ทำงานและ SSO กับ kalowave.com
                self.log("🌐 เปิด Kalodata เพื่อ auth...")
                await page.goto("https://www.kalodata.com", wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(3000)
                self.log(f"📄 Title: {await page.title()}")

                # ดึง Top 7 ใหม่ถ้าหมดรอบ
                cycle_complete = state.get("index", 0) >= TOP_N
                if not state.get("products") or cycle_complete:
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
                    # รีเซต index เฉพาะตอนครบรอบ ถ้าโหลดครั้งแรกให้คงค่าที่ตั้งไว้
                    if cycle_complete:
                        state["index"] = 0
                    self.save_state(state)

                if not state["products"]:
                    self.log("❌ ดึงสินค้าไม่ได้ — อาจต้อง refresh cookies")
                    return

                idx = state.get("index", 0)
                product = state["products"][idx]
                self.log(f"🎯 สินค้า #{product['rank']}: {product['name'][:50]}")

                # ไปหน้า Kaloclip (คืน page ที่ถูก navigate ไป อาจเป็น popup)
                kaloclip_page = await self._open_kaloclip(page, product)
                if not kaloclip_page:
                    self.log("❌ เปิด Kaloclip ไม่ได้")
                    return

                # กรอกฟอร์ม
                await self._fill_form(kaloclip_page)

                # รอ render + download
                filepath = await self._download_video(kaloclip_page, product)

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
        pid = product.get("id") or product.get("product_id")
        if not pid:
            self.log("⚠️ ไม่มี product id")
            return None

        # ไป product detail บน kalodata.com ก่อน เพื่อให้ Kaloclip โหลดข้อมูลสินค้าได้
        detail_url = f"https://www.kalodata.com/product/detail?productId={pid}&region=TH"
        self.log(f"🔗 เปิด Kalodata product detail: {detail_url}")
        await page.goto(detail_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)
        self.log(f"📄 Title: {await page.title()} | URL: {page.url}")

        # หาปุ่ม Kaloclip/AI Video บน kalodata.com
        kaloclip_btn = None
        for sel in [
            'a:has-text("Kaloclip")', 'button:has-text("Kaloclip")',
            'a:has-text("AI Video")', 'button:has-text("AI Video")',
            '[class*="kaloclip"]', '[class*="clip"]',
            'a[href*="kalowave.com"]',
        ]:
            try:
                el = await page.query_selector(sel)
                if el:
                    kaloclip_btn = el
                    self.log(f"  ✅ พบปุ่ม: {sel}")
                    break
            except Exception:
                pass

        if kaloclip_btn:
            self.log("  → คลิกปุ่ม Kaloclip...")
            try:
                # รอ popup ที่จะเปิดขึ้นมา
                async with page.expect_popup(timeout=10000) as popup_info:
                    await kaloclip_btn.click()
                new_page = await popup_info.value
                await new_page.wait_for_load_state("domcontentloaded", timeout=30000)
                await new_page.wait_for_timeout(5000)
                self.log(f"  ✅ Kaloclip popup: {new_page.url}")
                return new_page
            except Exception as e:
                self.log(f"  ⚠️ popup ไม่เปิด: {e} — ลอง navigate ตรงๆ")

        # Fallback: navigate ตรงไป Kaloclip URL
        kaloclip_url = f"https://clip.kalowave.com/video-creating?productId={pid}&country=th"
        self.log(f"⚠️ Fallback → {kaloclip_url}")
        await page.goto(kaloclip_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(6000)
        return page

    async def _fill_form(self, page):
        self.log("📝 กรอกฟอร์ม...")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(6000)

        # Screenshot + debug info
        try:
            ss_path = os.path.join(self.output_dir, "debug_form.png")
            await page.screenshot(path=ss_path, full_page=True)
            title = await page.title()
            self.log(f"📸 Screenshot saved | URL: {page.url} | Title: {title}")
            # ดูว่า login หรือเปล่า
            login_el = await page.query_selector('text="Login"')
            login_th = await page.query_selector('text="เข้าสู่ระบบ"')
            sign_in = await page.query_selector('text="Sign in"')
            all_text = await page.evaluate("document.body.innerText")
            self.log(f"  Login button: {bool(login_el or login_th or sign_in)}")
            self.log(f"  Body snippet: {all_text[:300]}")
        except Exception as e:
            self.log(f"⚠️ screenshot error: {e}")

        # รอให้จุดขาย (checkboxes) โหลด — สัญญาณว่า auth ผ่านและข้อมูลสินค้าโหลดแล้ว
        try:
            await page.wait_for_selector('input[type="checkbox"]', timeout=20000)
            self.log("  ✅ ฟอร์มโหลดแล้ว (พบ checkbox)")
        except Exception:
            self.log("⚠️ ไม่พบ checkbox หลังรอ 20s — อาจยังไม่ได้ auth")

        # Step 1: เลือกจุดขายทั้งหมด
        checkboxes = await page.query_selector_all('input[type="checkbox"]')
        checked_count = 0
        for cb in checkboxes:
            try:
                if not await cb.is_checked():
                    await cb.click()
                    await page.wait_for_timeout(200)
                    checked_count += 1
            except Exception:
                pass
        self.log(f"  เลือก {len(checkboxes)} จุดขาย (checked {checked_count})")

        # Step 1: ตั้งกลุ่มตลาด = ไทย
        await self._select_dropdown(page, ["ไทย", "Thailand", "TH"], "กลุ่มตลาดเป้าหมาย")

        # Step 1: ตั้งภาษา = ภาษาไทย
        await self._select_dropdown(page, ["ภาษาไทย", "Thai", "th"], "ภาษา")

        # ตั้ง video duration = 20S (คลิก duration dropdown ที่ bottom bar)
        await self._set_video_duration(page, "20")

        # กดถัดไป (Step 1 → Step 2 หรือ Step 2 → Step 3)
        await self._click_next(page)
        await page.wait_for_timeout(3000)

        # Step 2/3 — กดถัดไปอีกครั้ง ถ้ายังมี
        await self._click_next(page)
        await page.wait_for_timeout(3000)

        # Step 3 (ตรวจสอบสคริปต์) — กด Generate/สร้างวิดีโอ
        for btn_text in ["สร้างวิดีโอ", "Generate Video", "Generate", "ยืนยัน", "เริ่มสร้าง", "ถัดไป"]:
            btn = await page.query_selector(f'text="{btn_text}"')
            if btn:
                await btn.click()
                self.log(f"  กด '{btn_text}'")
                await page.wait_for_timeout(2000)
                break

    async def _set_video_duration(self, page, seconds="20"):
        """ตั้ง duration ที่ bottom bar เป็น 20S"""
        self.log(f"  ⏱ ตั้ง duration = {seconds}S...")
        try:
            # คลิก duration dropdown ที่ bottom bar (มักแสดงเป็น "15 S" หรือ "20 S")
            for current in ["15 S", "15S", "15", "10 S", "10S"]:
                btn = await page.query_selector(f'text="{current}"')
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(500)
                    # เลือก 20S จาก dropdown ที่เปิดออกมา
                    for opt in [f"{seconds} S", f"{seconds}S", seconds]:
                        el = await page.query_selector(f'text="{opt}"')
                        if el:
                            await el.click()
                            self.log(f"  ✅ duration = {seconds}S")
                            return
            self.log(f"  ⚠️ ไม่พบ duration dropdown")
        except Exception as e:
            self.log(f"  ⚠️ set duration error: {e}")

    async def _select_dropdown(self, page, options, label="dropdown"):
        """เลือก dropdown โดย text options (รองรับทั้ง native select และ custom dropdown)"""
        for opt_text in options:
            try:
                # ลอง native select ก่อน
                selects = await page.query_selector_all("select")
                for sel in selects:
                    opts = await sel.query_selector_all("option")
                    for o in opts:
                        t = (await o.inner_text()).strip()
                        v = await o.get_attribute("value") or ""
                        if opt_text.lower() in t.lower() or opt_text.lower() in v.lower():
                            await sel.select_option(value=v)
                            self.log(f"  ✅ {label}: เลือก '{t}'")
                            return
                # ลอง custom dropdown (คลิก element ที่มี text นั้น)
                el = await page.query_selector(f'text="{opt_text}"')
                if el:
                    await el.click()
                    self.log(f"  ✅ {label}: คลิก '{opt_text}'")
                    await page.wait_for_timeout(300)
                    return
            except Exception:
                pass
        self.log(f"  ⚠️ {label}: ไม่พบ option {options}")

    async def _set_video_language(self, page):
        """ตั้งภาษา script เป็นไทยใน Video Settings"""
        self.log("  🌏 ตั้งภาษาไทย...")
        # ลองหา dropdown ภาษา
        for lang_sel in [
            'text="Thai"', 'text="ไทย"', 'text="th"',
            '[class*="language"] [value="th"]',
            'select[name*="lang"]',
        ]:
            try:
                el = await page.query_selector(lang_sel)
                if el:
                    await el.click()
                    self.log(f"  ✅ เลือกภาษาไทย: {lang_sel}")
                    await page.wait_for_timeout(500)
                    return
            except Exception:
                pass

        # ลอง select element
        selects = await page.query_selector_all("select")
        for sel in selects:
            try:
                options = await sel.query_selector_all("option")
                for opt in options:
                    val = await opt.get_attribute("value") or ""
                    text = await opt.inner_text()
                    if "th" in val.lower() or "ไทย" in text or "Thai" in text:
                        await sel.select_option(value=val)
                        self.log(f"  ✅ select ภาษาไทย: {val}")
                        return
            except Exception:
                pass
        self.log("  ⚠️ ไม่พบ dropdown ภาษา (อาจยังไม่โหลด)")

    async def _click_next(self, page):
        for text in ["ถัดไป", "Next", "ต่อไป"]:
            try:
                btn = await page.query_selector(f'text="{text}"')
                if btn:
                    await btn.click(timeout=5000)
                    self.log(f"  → กด '{text}'")
                    return
            except Exception as e:
                self.log(f"  ⚠️ กด '{text}' ไม่ได้: {e}")
        self.log("  ⚠️ ไม่พบปุ่มถัดไป")

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
