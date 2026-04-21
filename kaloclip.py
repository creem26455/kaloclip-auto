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
            all_text = await page.evaluate("document.body.innerText")
            self.log(f"  Body snippet: {all_text[:300]}")
        except Exception as e:
            self.log(f"⚠️ screenshot error: {e}")

        # ===== STEP 1 (ตั้งค่าสินค้า) =====
        # Step 1 แสดงรูปสินค้า / drag-drop — ไม่มี checkbox
        # รอให้ product โหลดแล้วกด ถัดไป → Step 2
        self.log("  [Step 1] รอ product โหลด...")
        await page.wait_for_timeout(3000)

        # กด ถัดไป Step 1 → Step 2
        self.log("  [Step 1 → Step 2] กด ถัดไป...")
        await self._click_next(page)
        await page.wait_for_timeout(5000)

        # ===== STEP 2 (ตั้งค่าวิดีโอ) =====
        # รอ checkbox จุดขายโหลด
        self.log("  [Step 2] รอ checkbox จุดขาย...")
        try:
            await page.wait_for_selector('input[type="checkbox"]', timeout=20000)
            self.log("  ✅ พบ checkbox บน Step 2")
        except Exception:
            self.log("  ⚠️ ไม่พบ checkbox บน Step 2 — ดำเนินการต่อ")

        # เลือกจุดขายทั้งหมด
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

        # ตั้งกลุ่มตลาด = ไทย (Ant Design dropdown — placeholder: "เลือกภูมิภาค...")
        await self._set_antd_dropdown(page, "เลือกภูมิภาค", ["ไทย", "Thailand", "TH"], "กลุ่มตลาด")

        # ตั้งภาษา = ภาษาไทย (Ant Design dropdown — current: "ภาษาอังกฤษ")
        await self._set_antd_dropdown(page, "ภาษาอังกฤษ", ["ภาษาไทย", "Thai"], "ภาษา")

        # Screenshot หลังกรอก Step 2
        try:
            ss2_path = os.path.join(self.output_dir, "debug_step2.png")
            await page.screenshot(path=ss2_path, full_page=True)
            self.log("  📸 Screenshot Step 2 saved")
        except Exception:
            pass

        # กด ถัดไป Step 2 → Step 3
        self.log("  [Step 2 → Step 3] กด ถัดไป...")
        await self._click_next(page)
        await page.wait_for_timeout(5000)

        # ===== STEP 3 (ตรวจสอบสคริปต์) =====
        # รอ script generate เสร็จ — ปุ่มจะเปลี่ยนจาก "กำลังโหลด..." → "สร้าง +10"
        self.log("  [Step 3] รอ script generate เสร็จ (สูงสุด 5 นาที)...")
        try:
            await page.wait_for_function(
                # ปุ่ม generate จริงๆ คือ "สร้าง" (+ credit cost) ไม่ใช่ "สร้างวิดีโอ"
                """() => Array.from(document.querySelectorAll('button'))
                    .some(b => b.textContent.trim().startsWith('สร้าง') && !b.disabled)""",
                timeout=300_000
            )
            self.log("  ✅ Script โหลดเสร็จ — พบปุ่ม สร้าง")
        except Exception:
            self.log("  ⚠️ Script รอนาน — ดำเนินการต่อ")

        # ตั้ง duration = 20S (bottom bar Step 3) — ใช้ method พิเศษ
        duration_ok = await self._set_duration_step3(page)

        # Screenshot Step 3 หลังตั้งค่า
        try:
            ss3_path = os.path.join(self.output_dir, "debug_step3.png")
            await page.screenshot(path=ss3_path, full_page=True)
            btns = await page.evaluate(
                """Array.from(document.querySelectorAll('button'))
                   .filter(b => b.offsetParent).map(b => b.textContent.trim()).join(' | ')"""
            )
            self.log(f"  📸 Step 3 saved | buttons: {btns}")
        except Exception:
            pass

        # ถ้า duration ไม่ได้ตั้งค่าตามที่กำหนด → abort ไม่สร้างคลิป
        if not duration_ok:
            raise Exception("❌ ตั้งค่า duration ไม่สำเร็จ (ยังเป็น 8S) — ยกเลิกการสร้างคลิป")

        # กด สร้าง (ปุ่มจริงคือ "สร้าง +10" หรือ "สร้าง +XX")
        self.log("  [Step 3] กด สร้าง...")
        clicked = False
        for btn_text in ["สร้าง", "สร้างวิดีโอ", "Generate Video", "Generate", "ยืนยัน", "เริ่มสร้าง"]:
            try:
                btn = await page.query_selector(f'button:has-text("{btn_text}")')
                if not btn:
                    btn = await page.query_selector(f'text="{btn_text}"')
                if btn:
                    await btn.click(timeout=5000)
                    self.log(f"  ✅ กด '{btn_text}'")
                    clicked = True
                    await page.wait_for_timeout(2000)
                    break
            except Exception as e:
                self.log(f"  ⚠️ กด '{btn_text}': {e}")
        if not clicked:
            self.log("  ⚠️ ไม่พบปุ่ม สร้าง — ลอง locator สำรอง")
            # fallback: ลอง locator แบบ startsWith
            try:
                btns = await page.query_selector_all('button')
                for b in btns:
                    txt = (await b.inner_text()).strip()
                    if txt.startswith("สร้าง") and await b.is_visible():
                        await b.click(timeout=5000)
                        self.log(f"  ✅ fallback กด '{txt}'")
                        clicked = True
                        await page.wait_for_timeout(2000)
                        break
            except Exception as ef:
                self.log(f"  ⚠️ fallback error: {ef}")
            if not clicked:
                self.log("  ❌ ไม่พบปุ่ม Generate เลย")

        # ===== Dismiss notification popup =====
        # หลังกด สร้าง — Kaloclip แสดง popup "ไม่ต้องรอ! เปิดการแจ้งเตือน..."
        # ต้องกดปิดก่อนถึงจะ render ต่อได้
        if clicked:
            await page.wait_for_timeout(2000)
            self.log("  🔔 ตรวจ notification popup...")
            dismissed = False
            for dismiss_text in ["ไม่เป็นไร", "ไม่ต้องการ", "ข้าม", "Skip", "No thanks", "No"]:
                try:
                    el = page.locator(f'button:has-text("{dismiss_text}")').first
                    if await el.is_visible(timeout=2000):
                        await el.click()
                        self.log(f"  ✅ ปิด popup: '{dismiss_text}'")
                        dismissed = True
                        await page.wait_for_timeout(1000)
                        break
                except Exception:
                    continue
            if not dismissed:
                # ลอง Ant Design modal cancel button
                for sel in [
                    '.ant-modal-footer button:first-child',
                    '.ant-modal-close',
                    '[class*="modal"] button:first-child',
                    'button[class*="cancel"]',
                ]:
                    try:
                        el = page.locator(sel).first
                        if await el.is_visible(timeout=1000):
                            await el.click()
                            self.log(f"  ✅ ปิด modal: {sel}")
                            dismissed = True
                            await page.wait_for_timeout(1000)
                            break
                    except Exception:
                        continue
            if not dismissed:
                self.log("  ℹ️ ไม่พบ notification popup (หรือปิดแล้ว)")
            # Screenshot หลังปิด popup
            try:
                ss4_path = os.path.join(self.output_dir, "debug_after_dismiss.png")
                await page.screenshot(path=ss4_path, full_page=True)
                btns_after = await page.evaluate(
                    """Array.from(document.querySelectorAll('button'))
                       .filter(b => b.offsetParent !== null)
                       .map(b => b.textContent.trim()).filter(t => t).join(' | ')"""
                )
                self.log(f"  📸 After-dismiss | Btns: {btns_after[:300]}")
            except Exception:
                pass

    async def _set_duration_step3(self, page):
        """ตั้ง duration = 20S ใน Step 3 bottom bar
        Kaloclip ใช้ custom Ant Design — inner element = .ant-select-content (ไม่ใช่ .ant-select-selector)
        """
        self.log("  ⏱ ตั้ง duration = 20S...")

        # Helper: ตรวจว่าเปลี่ยนสำเร็จ
        async def _check_ok():
            body = await page.evaluate("document.body.innerText")
            return "20 S" in body

        # Helper: dump visible elements — ใช้ getAttribute แทน .className เพื่อรองรับ SVG
        async def _dump_new_elements():
            return await page.evaluate("""
                () => {
                    const found = [];
                    for (const el of document.querySelectorAll('*')) {
                        if (el.offsetParent === null) continue;
                        const t = el.textContent.trim();
                        const cls = el.getAttribute('class') || '';  // ไม่ใช้ .className (SVG bug)
                        if (
                            /^\\d{1,2}\\s*[Ss]$/.test(t) ||
                            cls.includes('dropdown') || cls.includes('popup') ||
                            cls.includes('option') || cls.includes('select-item') ||
                            cls.includes('param-') || cls.includes('select-list')
                        ) {
                            const rect = el.getBoundingClientRect();
                            found.push({
                                tag: el.tagName,
                                text: t.substring(0, 20),
                                cls: cls.substring(0, 80),
                                x: Math.round(rect.x), y: Math.round(rect.y)
                            });
                        }
                        if (found.length >= 30) break;
                    }
                    return found;
                }
            """)

        # ===== Approach A: คลิก .ant-select-content บน duration .param-select โดยตรง =====
        # Bottom bar มีหลาย .param-select: [9:16 ratio] [8S duration] [1080P quality]
        # ต้องหา .param-select ที่มี text "8 S" เท่านั้น — ไม่ใช่ first match!
        self.log("  [A] คลิก .ant-select-content บน duration dropdown...")

        # หา duration .param-select ที่ถูกต้อง
        async def _find_duration_param():
            els = await page.locator('.param-select').all()
            for el in els:
                try:
                    t = await el.inner_text()
                    if '8 S' in t or '20 S' in t or ('S' in t and any(c.isdigit() for c in t)):
                        return el
                except Exception:
                    continue
            return None

        try:
            duration_param = await _find_duration_param()
            if duration_param:
                inner = duration_param.locator('.ant-select-content').first
                if await inner.is_visible(timeout=1000):
                    await inner.scroll_into_view_if_needed()
                    await inner.click()
                    self.log("  🖱 [A] clicked duration .ant-select-content")
                    await page.wait_for_timeout(1500)

                    # Dump new elements
                    new_els = await _dump_new_elements()
                    self.log(f"  [A] new elements: {new_els}")

                    # ลองคลิก option 20 S ด้วยหลาย selectors
                    for opt in ["20 S", "20S", "20"]:
                        for sel in [
                            f'.ant-select-item:has-text("{opt}")',
                            f'.ant-select-content-item:has-text("{opt}")',
                            f'[class*="option"]:has-text("{opt}")',
                            f'[class*="item"]:has-text("{opt}")',
                            f'[class*="select"]:has-text("{opt}")',
                            f'li:has-text("{opt}")',
                        ]:
                            try:
                                el = page.locator(sel).first
                                if await el.is_visible(timeout=400):
                                    await el.click()
                                    self.log(f"  ✅ [A] selected '{opt}' via {sel.split(':')[0]}")
                                    await page.wait_for_timeout(500)
                                    if await _check_ok():
                                        return True
                            except Exception:
                                continue

                    # ลอง get_by_text exact
                    for opt in ["20 S", "20S"]:
                        try:
                            el = page.get_by_text(opt, exact=True).first
                            if await el.is_visible(timeout=400):
                                await el.click()
                                self.log(f"  ✅ [A] get_by_text '{opt}'")
                                await page.wait_for_timeout(500)
                                if await _check_ok():
                                    return True
                        except Exception:
                            continue
        except Exception as e:
            self.log(f"  ⚠️ [A]: {e}")

        # ===== Approach B: React __reactProps — เรียก onMouseDown handler โดยตรง =====
        self.log("  [B] React __reactProps onMouseDown...")
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)

        js_b = await page.evaluate("""
            () => {
                // หา .param-select ที่มี "8 S" (duration) ไม่ใช่ 9:16 (ratio)
                const allParams = document.querySelectorAll('.param-select');
                let paramSel = null;
                for (const el of allParams) {
                    const t = el.textContent.trim();
                    if (/^\\d{1,2}\\s*S$/.test(t) || t === '8 S' || t === '20 S') {
                        paramSel = el; break;
                    }
                }
                if (!paramSel) return {err: 'no duration .param-select', found: Array.from(allParams).map(e=>e.textContent.trim().substring(0,10)).join(',')};

                // ค้นหา __reactProps key
                const reactKey = Object.keys(paramSel).find(k =>
                    k.startsWith('__reactProps') || k.startsWith('__reactFiber') ||
                    k.startsWith('__reactInternalInstance')
                );
                if (!reactKey) {
                    // log element keys สำหรับ debug
                    return {err: 'no reactKey', elKeys: Object.keys(paramSel).slice(0,10).join(',')};
                }

                const props = paramSel[reactKey];
                const propsKeys = props ? Object.keys(props).join(',') : 'null';

                // เรียก onMouseDown ถ้ามี
                if (props && props.onMouseDown) {
                    props.onMouseDown({
                        preventDefault: ()=>{}, stopPropagation: ()=>{},
                        target: paramSel, currentTarget: paramSel
                    });
                    return {result: 'called onMouseDown', propsKeys};
                }
                // เรียก onClick ถ้ามี
                if (props && props.onClick) {
                    props.onClick({
                        preventDefault: ()=>{}, stopPropagation: ()=>{},
                        target: paramSel, currentTarget: paramSel
                    });
                    return {result: 'called onClick', propsKeys};
                }
                return {err: 'no onMouseDown/onClick', propsKeys};
            }
        """)
        self.log(f"  [B] React props: {str(js_b)[:300]}")
        await page.wait_for_timeout(1500)

        # Dump body children + inside param-select
        dropdown_html = await page.evaluate("""
            () => {
                const result = {body: [], inside: []};
                // Body level popups (Ant Design portal)
                for (const el of document.body.children) {
                    const cls = el.getAttribute('class') || '';
                    if (cls.includes('dropdown') || cls.includes('popup') ||
                        cls.includes('ant-select') || cls.includes('overlay')) {
                        if (el.offsetParent !== null) {
                            result.body.push({cls: cls.substring(0,80), html: el.innerHTML.substring(0,300)});
                        }
                    }
                }
                // Inside param-select (non-portal dropdown)
                const paramSel = document.querySelector('.param-select');
                if (paramSel) {
                    for (const el of paramSel.querySelectorAll('*')) {
                        const cls = el.getAttribute('class') || '';
                        if (cls.includes('dropdown') || cls.includes('list') ||
                            cls.includes('option') || cls.includes('popup')) {
                            result.inside.push({cls: cls.substring(0,80), disp: window.getComputedStyle(el).display});
                        }
                    }
                }
                return result;
            }
        """)
        self.log(f"  [B] dropdown: {str(dropdown_html)[:500]}")

        try:
            new_els_b = await _dump_new_elements()
            self.log(f"  [B] new elements: {new_els_b}")
        except Exception as e:
            self.log(f"  [B] dump err: {e}")

        # ลองคลิก option 20 S
        for opt in ["20 S", "20S", "20"]:
            for sel in [
                f'[class*="select-item"]:has-text("{opt}")',
                f'[class*="option"]:has-text("{opt}")',
                f'[class*="item"]:has-text("{opt}")',
                f'li:has-text("{opt}")',
                f'[role="option"]:has-text("{opt}")',
                f'text="{opt}"',
            ]:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=400):
                        await el.click()
                        self.log(f"  ✅ [B] '{opt}' via {sel.split(':')[0]}")
                        await page.wait_for_timeout(500)
                        if await _check_ok():
                            return True
                except Exception:
                    continue

        # ===== Approach D: React fiber → onChange บน duration dropdown โดยตรง =====
        self.log("  [D] React fiber onChange on duration...")
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(200)

        js_d = await page.evaluate("""
            () => {
                // หา duration .param-select (text = "8 S" หรือ pattern \\d+S)
                const allParams = document.querySelectorAll('.param-select');
                let paramSel = null;
                for (const el of allParams) {
                    const t = el.textContent.trim();
                    if (/^\\d{1,2}\\s*S$/.test(t) || t === '8 S' || t === '20 S') {
                        paramSel = el; break;
                    }
                }
                if (!paramSel) return {err: 'no duration .param-select'};

                // หา React fiber
                const fiberKey = Object.keys(paramSel).find(k =>
                    k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance')
                );
                if (!fiberKey) return {err: 'no fiber', keys: Object.keys(paramSel).slice(0,10).join(',')};

                // Traverse fiber tree หา Select component ที่มี onChange
                let fiber = paramSel[fiberKey];
                let attempts = 0;
                while (fiber && attempts < 30) {
                    const props = fiber.memoizedProps || fiber.pendingProps;
                    if (props && typeof props.onChange === 'function' && props.options) {
                        // เจอ Select component
                        try {
                            props.onChange(20, {value:20, label:'20 S'});
                            return {result: 'onChange called', opts: JSON.stringify(props.options).substring(0,200)};
                        } catch(e) {
                            return {err: 'onChange failed: ' + e.message};
                        }
                    }
                    fiber = fiber.return;
                    attempts++;
                }
                return {err: 'onChange not found after ' + attempts + ' traversals'};
            }
        """)
        self.log(f"  [D] fiber: {str(js_d)[:300]}")
        await page.wait_for_timeout(1000)  # รอ React re-render
        if await _check_ok():
            self.log("  ✅ [D] Duration = 20S via React onChange ✓")
            return True
        # log body snippet เพื่อ debug ว่า DOM เปลี่ยนหรือยัง
        body_d = await page.evaluate("document.body.innerText")
        self.log(f"  [D] body after onChange: {'20 S' in body_d} | snippet: {body_d[body_d.find('8 S')-10:body_d.find('8 S')+20] if '8 S' in body_d else body_d[:100]}")

        # ===== Approach C: Keyboard navigation บน duration dropdown =====
        self.log("  [C] Keyboard navigation on duration...")
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(200)
        try:
            # Focus .ant-select-content ของ duration param-select เท่านั้น
            duration_param_c = await _find_duration_param()
            if not duration_param_c:
                raise Exception("no duration param")
            param_loc = duration_param_c.locator('.ant-select-content').first
            if await param_loc.is_visible(timeout=1000):
                await param_loc.focus()
                await page.wait_for_timeout(300)
                await page.keyboard.press("Space")
                await page.wait_for_timeout(800)
                opts_c = await _dump_new_elements()
                self.log(f"  [C] after Space: {opts_c}")

                # ลอง ArrowDown หลายครั้ง
                for _ in range(5):
                    await page.keyboard.press("ArrowDown")
                    await page.wait_for_timeout(200)
                    if await _check_ok():
                        await page.keyboard.press("Enter")
                        self.log("  ✅ [C] Duration = 20S via keyboard")
                        return True
                await page.keyboard.press("Escape")
        except Exception as e:
            self.log(f"  ⚠️ [C]: {e}")

        # --- Final check ---
        if await _check_ok():
            self.log("  ✅ Duration = 20S ✓")
            return True

        self.log("  ❌ Duration ยังเป็น 8S — หยุดไม่สร้างคลิป!")
        return False

    async def _set_antd_dropdown(self, page, trigger_contains, options, label=""):
        """เปิด Ant Design dropdown แล้วเลือก option
        ใช้ Playwright ElementHandle.click() เพื่อ trigger React synthetic events ถูกต้อง
        """
        try:
            # 1. หา ant-select ด้วย Playwright (ไม่ใช้ JS eval click)
            target_el = None
            selects = await page.query_selector_all('.ant-select')
            for sel in selects:
                try:
                    text = await sel.inner_text()
                    visible = await sel.is_visible()
                    if trigger_contains in text and visible:
                        target_el = sel
                        self.log(f"  📍 {label}: found '{text.strip()[:30]}'")
                        break
                except Exception:
                    continue

            if not target_el:
                self.log(f"  ⚠️ {label}: ไม่พบ dropdown '{trigger_contains}'")
                return

            # 2. scroll into view ก่อน แล้วคลิก .ant-select-selector (inner div)
            # กรณี bottom bar (duration/quality) — click outer wrapper ไม่ trigger dropdown
            # ต้องคลิกที่ inner .ant-select-selector แทน
            await target_el.scroll_into_view_if_needed()
            await page.wait_for_timeout(300)

            inner_selector = await target_el.query_selector('.ant-select-selector')
            if inner_selector:
                await inner_selector.click()
                self.log(f"  🖱 {label}: click inner selector")
            else:
                await target_el.click()
                self.log(f"  🖱 {label}: click outer wrapper")
            await page.wait_for_timeout(1500)

            # 3. Dump DOM หลัง click เพื่อดูว่า options ปรากฏที่ไหน
            dom_after = await page.evaluate("""
                () => {
                    const results = {};
                    // หา element ที่ visible ใหม่ๆ
                    const candidates = document.querySelectorAll(
                        '[class*="dropdown"], [class*="popup"], [class*="option"], ' +
                        '[class*="menu"], [role="listbox"], [role="option"], ' +
                        '[class*="list"], ul li'
                    );
                    const visible = [];
                    candidates.forEach(el => {
                        if (el.offsetParent !== null) {
                            const cls = el.className ? el.className.substring(0,35) : el.tagName;
                            const txt = el.textContent.trim().substring(0,25);
                            if (txt) visible.push(cls + ':' + txt);
                        }
                    });
                    results.visible = visible.slice(0,15).join(' || ');
                    results.body_new = document.body.innerText.substring(0,200);
                    return JSON.stringify(results);
                }
            """)
            self.log(f"  📊 {label} after-click: {dom_after[:300]}")

            # 4. เลือก option ด้วย Playwright (ไม่ใช้ JS eval click)
            for opt in options:
                # ลอง locator หลายแบบ
                for selector in [
                    f'.ant-select-item:has-text("{opt}")',
                    f'.ant-select-item-option:has-text("{opt}")',
                    f'[role="option"]:has-text("{opt}")',
                    f'li:has-text("{opt}")',
                    f'[class*="option"]:has-text("{opt}")',
                    f'[class*="item"]:has-text("{opt}")',
                ]:
                    try:
                        el = page.locator(selector).first
                        if await el.is_visible(timeout=500):
                            await el.click()
                            self.log(f"  ✅ {label}: '{opt}' via {selector.split(':')[0]}")
                            await page.wait_for_timeout(500)
                            return
                    except Exception:
                        continue

            # log ว่า dropdown มี options อะไรบ้าง (เพื่อ debug)
            available = await page.evaluate("""
                () => Array.from(document.querySelectorAll(
                    '.ant-select-item, .ant-select-item-option, [role="option"]'
                )).filter(e => e.offsetParent !== null)
                  .map(e => e.textContent.trim()).join(' | ')
            """)
            self.log(f"  ⚠️ {label}: ไม่พบ option {options} | available: {available[:200]}")
            await page.keyboard.press("Escape")
        except Exception as e:
            self.log(f"  ⚠️ {label} error: {e}")

    async def _set_video_duration(self, page, seconds="20"):
        """(deprecated) ตั้ง duration ที่ bottom bar เป็น 20S"""
        self.log(f"  ⏱ ตั้ง duration = {seconds}S...")
        try:
            # JS approach: หา element ที่ match pattern \d+S แล้วคลิกเพื่อเปิด dropdown
            # จากนั้นเลือก target
            result = await page.evaluate(f"""
                () => {{
                    const target = "{seconds}";
                    // Log all duration-like elements
                    const durationEls = [];
                    const all = document.querySelectorAll('button, div, span, li, label');
                    for (const el of all) {{
                        const t = el.textContent.trim();
                        if (/^\\d{{1,2}}\\s*[Ss]$/.test(t)) durationEls.push(t);
                    }}
                    return durationEls.join(', ') || 'none found';
                }}
            """)
            self.log(f"  Duration elements found: {result}")

            # คลิก current duration เพื่อเปิด dropdown/popover
            clicked_open = await page.evaluate(f"""
                () => {{
                    const target = "{seconds}";
                    const all = document.querySelectorAll('button, div, span, li, label');
                    for (const el of all) {{
                        const t = el.textContent.trim();
                        // คลิก element ที่ไม่ใช่ target (เพื่อ toggle dropdown)
                        if (/^\\d{{1,2}}\\s*[Ss]$/.test(t) && !t.startsWith(target)) {{
                            el.click();
                            return 'clicked:' + t;
                        }}
                    }}
                    return null;
                }}
            """)
            if clicked_open:
                self.log(f"  📍 {clicked_open}")
                await page.wait_for_timeout(600)

            # เลือก target duration
            selected = await page.evaluate(f"""
                () => {{
                    const target = "{seconds}";
                    const all = document.querySelectorAll('button, div, span, li, label, [role="option"]');
                    for (const el of all) {{
                        const t = el.textContent.trim();
                        if (t === target + 'S' || t === target + ' S' || t === target + 's') {{
                            el.click();
                            return 'selected:' + t;
                        }}
                    }}
                    return null;
                }}
            """)
            if selected:
                self.log(f"  ✅ Duration {selected}")
                await page.wait_for_timeout(400)
            else:
                self.log(f"  ⚠️ ไม่พบ duration {seconds}S")
        except Exception as e:
            self.log(f"  ⚠️ set duration error: {e}")

    async def _select_dropdown(self, page, options, label="dropdown"):
        """เลือก dropdown รองรับทั้ง native select และ custom dropdown"""
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
                            self.log(f"  ✅ {label}: native select '{t}'")
                            return

                # ลอง JS click — เหมาะกับ custom React/Vue dropdown
                result = await page.evaluate(f"""
                    () => {{
                        const text = {json.dumps(opt_text)};
                        // หา dropdown ที่เปิดอยู่ก่อน (li, [role=option], .option, .item)
                        const candidates = document.querySelectorAll(
                            'li, [role="option"], [class*="option"], [class*="item"], [class*="menu-item"]'
                        );
                        for (const el of candidates) {{
                            if (el.textContent.trim().includes(text)) {{
                                el.click();
                                return 'clicked-list:' + el.textContent.trim().substring(0, 30);
                            }}
                        }}
                        // ถ้าไม่มี dropdown เปิด — หา trigger แล้วคลิก
                        const triggers = document.querySelectorAll(
                            '[class*="select"], [class*="dropdown"], [class*="picker"]'
                        );
                        for (const el of triggers) {{
                            if (el.textContent.trim().includes(text)) {{
                                el.click();
                                return 'clicked-trigger:' + el.textContent.trim().substring(0, 30);
                            }}
                        }}
                        return null;
                    }}
                """)
                if result:
                    self.log(f"  ✅ {label}: JS {result}")
                    await page.wait_for_timeout(400)
                    return

                # ลอง Playwright text locator
                el = await page.query_selector(f'text="{opt_text}"')
                if el:
                    await el.click()
                    self.log(f"  ✅ {label}: text click '{opt_text}'")
                    await page.wait_for_timeout(400)
                    return

            except Exception as e:
                self.log(f"  ⚠️ {label} option '{opt_text}' error: {e}")
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
        """
        Flow หลัง click สร้าง + dismiss popup:
        1. Page อาจเป็น detail view (ซ้าย=X% render, ขวา=script panel)
        2. Navigate ไป รายการโปรด (video list)
        3. รอ card แรก (newest) เปลี่ยนจาก รอคิว/กำลังประมวลผล → เสร็จสิ้น
        4. คลิก ⋯ menu บน card แรก → คลิก ดาวน์โหลด
        """
        self.log("⏳ รอ render... (หน้า รายการโปรด)")

        # Helper: screenshot + log
        async def _snap(name):
            try:
                p = os.path.join(self.output_dir, f"{name}.png")
                await page.screenshot(path=p, full_page=True)
                btns = await page.evaluate(
                    """Array.from(document.querySelectorAll('button,a'))
                       .filter(b => b.offsetParent !== null)
                       .map(b => b.textContent.trim()).filter(t => t).join(' | ')"""
                )
                body = await page.evaluate("document.body.innerText")
                self.log(f"  📸 {name} | Btns: {btns[:350]}")
                self.log(f"  Body: {body[:120]}")
                return body
            except Exception as e:
                self.log(f"  ⚠️ snap {name}: {e}")
                return ""

        # Helper: try download click
        async def _try_download(btn):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(c for c in product["name"][:20] if c.isalnum() or c in "- _")
            save_path = os.path.join(self.output_dir, f"{timestamp}_{safe_name}.mp4")
            try:
                async with page.expect_download(timeout=180_000) as dl_info:
                    await btn.click()
                dl = await dl_info.value
                await dl.save_as(save_path)
                self.log(f"✅ บันทึก: {os.path.basename(save_path)}")
                return save_path
            except Exception as e:
                self.log(f"  ⚠️ download error: {e}")
                return None

        # รอ 30s ให้หน้า settle
        await page.wait_for_timeout(30_000)
        await _snap("debug_after_create")

        # ===== Navigate ไป รายการโปรด =====
        self.log("  [Nav] Navigate ไป รายการโปรด...")
        try:
            nav = page.locator('text="รายการโปรด"').first
            if await nav.is_visible(timeout=3000):
                await nav.click()
                await page.wait_for_timeout(2000)
                self.log("  ✅ อยู่ที่ รายการโปรด แล้ว")
        except Exception as e:
            self.log(f"  ⚠️ nav error: {e}")

        await _snap("debug_video_list")

        # ===== Phase 1: รอ render เสร็จ =====
        # สถานะวิดีโอ: รอคิว → กำลังประมวลผล → เสร็จสิ้น
        # รอจนทั้ง "รอคิว" และ "กำลังประมวลผล" หายออกจากหน้า
        self.log("  [Phase 1] รอ render เสร็จ (max 15 นาที)...")
        try:
            await page.wait_for_function(
                """() => {
                    const t = document.body.innerText;
                    return !t.includes('รอคิว') && !t.includes('กำลังประมวลผล');
                }""",
                timeout=900_000
            )
            self.log("  ✅ Render เสร็จสิ้น!")
        except Exception as e:
            self.log(f"  ⚠️ render wait: {e}")

        await _snap("debug_render_done")

        # ===== Phase 2: คลิก ⋯ menu บน card แรก =====
        # ⋯ button อยู่ที่ top-right ของ video card ที่ completed
        self.log("  [Phase 2] หา ⋯ menu บน card แรก...")

        # JS: dump all buttons ที่มี className เพื่อหา class ของ ⋯ button
        btn_info = await page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('button'));
                return btns.map(b => ({
                    text: b.textContent.trim().substring(0, 20),
                    cls: b.className.substring(0, 60),
                    vis: b.offsetParent !== null
                })).filter(b => b.vis).slice(0, 20);
            }
        """)
        self.log(f"  All buttons: {btn_info}")

        # ลอง click ⋯ button ด้วยหลาย approach
        three_dot_clicked = False

        # Approach A: ลอง Playwright locator
        for more_sel in [
            'button:has-text("...")', 'button:has-text("⋯")',
            '[class*="more"]', '[class*="dots"]', '[class*="option"]',
            '.ant-dropdown-trigger', '[aria-label="more"]',
            '[aria-haspopup="true"]',
        ]:
            try:
                el = page.locator(more_sel).first
                if await el.is_visible(timeout=1000):
                    await el.click()
                    self.log(f"  ✅ กด ⋯: {more_sel}")
                    three_dot_clicked = True
                    await page.wait_for_timeout(800)
                    break
            except Exception:
                continue

        # Approach B: JS click บน button สุดท้ายใน card แรก (⋯ มักเป็น btn สุดท้าย)
        if not three_dot_clicked:
            self.log("  ลอง JS click ⋯ (btn สุดท้ายใน card)")
            try:
                result = await page.evaluate("""
                    () => {
                        // หา element ที่มี class ชื่อ "Component" หรือ grid/list container
                        const containers = Array.from(document.querySelectorAll('[class*="grid"],[class*="list"],[class*="videos"]'));
                        for (const c of containers) {
                            const btns = c.querySelectorAll('button');
                            if (btns.length > 0) {
                                const lastBtn = btns[btns.length - 1];
                                lastBtn.click();
                                return 'clicked last btn in: ' + c.className.substring(0, 40);
                            }
                        }
                        // fallback: click ⋯ หรือ ... ที่ไหนก็ได้
                        const all = document.querySelectorAll('button');
                        for (const b of all) {
                            const t = b.textContent.trim();
                            if (t === '...' || t === '⋯' || t === '···') {
                                b.click();
                                return 'clicked: ' + t;
                            }
                        }
                        return null;
                    }
                """)
                if result:
                    self.log(f"  ✅ JS ⋯: {result}")
                    three_dot_clicked = True
                    await page.wait_for_timeout(800)
            except Exception as e:
                self.log(f"  ⚠️ JS ⋯: {e}")

        await _snap("debug_after_threedots")

        # ===== Phase 3: คลิก ดาวน์โหลด ใน dropdown menu =====
        self.log("  [Phase 3] หา ดาวน์โหลด ใน menu...")
        DL_MENU_SELS = [
            'li:has-text("ดาวน์โหลด")',
            '[role="menuitem"]:has-text("ดาวน์โหลด")',
            '[class*="menu"]:has-text("ดาวน์โหลด")',
            'button:has-text("ดาวน์โหลด")',
            'a:has-text("ดาวน์โหลด")',
            ':has-text("ดาวน์โหลด")',
            'button:has-text("Download")',
            'a[download]',
            'a[href*=".mp4"]',
        ]
        for sel in DL_MENU_SELS:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=3000):
                    self.log(f"  ✅ พบ Download: {sel}")
                    result = await _try_download(el)
                    if result:
                        return result
                    break
            except Exception:
                continue

        # ===== Fallback: คลิก card เพื่อเปิด detail view แล้วหา download =====
        self.log("  [Fallback] คลิก card เพื่อเปิด detail view...")
        await page.keyboard.press("Escape")  # ปิด menu เก่า
        await page.wait_for_timeout(500)

        # JS: หา card แรกที่มี "เสร็จสิ้น" แล้วคลิก thumbnail area
        try:
            await page.evaluate("""
                () => {
                    // หา element ที่มี เสร็จสิ้น แล้ว traverse ขึ้นไปหา card container
                    const all = Array.from(document.querySelectorAll('*'));
                    for (const el of all) {
                        if (el.childElementCount === 0 && el.textContent.trim() === 'เสร็จสิ้น') {
                            let p = el.parentElement;
                            for (let i = 0; i < 8; i++) {
                                if (p && p.offsetWidth > 150 && p.offsetHeight > 150) {
                                    // หา img หรือ video area ใน card
                                    const img = p.querySelector('img, video, [class*="thumb"], [class*="preview"]');
                                    if (img) { img.click(); return 'clicked thumb in card'; }
                                    p.click();
                                    return 'clicked card';
                                }
                                p = p?.parentElement;
                            }
                            break;
                        }
                    }
                    return null;
                }
            """)
            await page.wait_for_timeout(3000)
        except Exception as e:
            self.log(f"  ⚠️ card click: {e}")

        await _snap("debug_detail_view")

        # ลอง download ใน detail view
        for sel in DL_MENU_SELS:
            try:
                el = page.locator(sel).first
                if await el.is_visible(timeout=3000):
                    self.log(f"  ✅ Detail view download: {sel}")
                    result = await _try_download(el)
                    if result:
                        return result
                    break
            except Exception:
                continue

        self.log("⚠️ ไม่พบปุ่ม ดาวน์โหลด — ดู screenshot debug_detail_view")
        return None
