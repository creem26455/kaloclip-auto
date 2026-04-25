"""
Kaloclip Bot — Playwright automation สำหรับ Kalodata
วน Top 7 สินค้า ทีละ 1 ตัวต่อวัน
"""

import json
import os
import re
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

                # โพส TikTok (ถ้ามี token)
                tiktok_url = ""
                if filepath:
                    tiktok_url = await self._post_to_tiktok(filepath, product.get("name", ""))

                # แจ้ง Telegram
                from notify import send_message, send_video
                msg = (f"🎬 <b>Kaloclip Auto</b>\n"
                       f"✅ สร้างคลิปเสร็จแล้ว!\n\n"
                       f"📦 สินค้า: {product['name'][:50]}\n"
                       f"📋 รอบนี้: {state['index']}/{TOP_N}\n"
                       f"🕐 {state['last_run']}")
                if tiktok_url:
                    msg += f"\n🎵 TikTok: {tiktok_url}"
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

        # ===== ตรวจว่าหน้าโหลดจริงๆ (ไม่ใช่แค่ spinner) =====
        try:
            body_check = await page.evaluate("document.body.innerText")
            if not body_check or len(body_check.strip()) < 20:
                # รอเพิ่มอีก 15s แล้วเช็คอีกรอบ
                self.log("  ⚠️ หน้าดูเหมือนยังโหลดไม่เสร็จ (body ว่าง) — รอเพิ่ม 15s...")
                await page.wait_for_timeout(15000)
                body_check2 = await page.evaluate("document.body.innerText")
                if not body_check2 or len(body_check2.strip()) < 20:
                    raise Exception("❌ หน้า kalowave.com ไม่โหลด (spinner ค้าง) — อาจเป็นปัญหา auth/session")
        except Exception as e:
            self.log(f"  {e}")
            raise

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
        self.log("  [Step 3] รอ script generate เสร็จ (สูงสุด 90 วินาที)...")
        try:
            await page.wait_for_function(
                # ปุ่ม generate จริงๆ คือ "สร้าง" (+ credit cost) ไม่ใช่ "สร้างวิดีโอ"
                """() => Array.from(document.querySelectorAll('button'))
                    .some(b => b.textContent.trim().startsWith('สร้าง') && !b.disabled)""",
                timeout=90_000
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
        Strategies (ลองตามลำดับ):
          E1a — flushSync + fiber onChange (force sync React update)
          E1b — direct useState hook queue.dispatch(20) ข้าม UI ทั้งหมด
          E1c — class component setState
          E3  — pointerdown event (Ant Design 5 ฟัง pointerdown ไม่ใช่ click)
          E4  — rc-select onSelect API
          F   — Keyboard Enter/Space + ArrowDown
        """
        self.log("  ⏱ ตั้ง duration = 20S...")

        # Helper: ตรวจว่าเปลี่ยนสำเร็จ
        async def _check_ok():
            try:
                body = await page.evaluate("document.body.innerText")
                return "20 S" in body
            except Exception:
                return False

        # Helper: หา duration .param-select (text pattern \d+S)
        async def _find_duration_param():
            els = await page.locator('.param-select').all()
            for el in els:
                try:
                    t = await el.inner_text()
                    if t.strip() in ['8 S', '12 S', '15 S', '20 S'] or \
                       (any(c.isdigit() for c in t) and 'S' in t and ':' not in t and 'P' not in t):
                        return el
                except Exception:
                    continue
            return None

        # JS helper: หา duration .param-select element
        FIND_DURATION_JS = """
            const allParams = document.querySelectorAll('.param-select');
            let paramSel = null;
            for (const el of allParams) {
                const t = el.textContent.trim();
                if (/^\\d{1,2}\\s*S$/.test(t)) { paramSel = el; break; }
            }
        """

        # ===== E1a: flushSync + fiber onChange (force sync React update) =====
        self.log("  [E1a] flushSync + fiber onChange...")
        js_e1a = await page.evaluate(f"""
            () => {{
                {FIND_DURATION_JS}
                if (!paramSel) return {{err: 'no duration param', found: Array.from(allParams).map(e=>e.textContent.trim().substring(0,12)).join('|')}};

                const fiberKey = Object.keys(paramSel).find(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance'));
                if (!fiberKey) return {{err: 'no fiber'}};

                let fiber = paramSel[fiberKey];
                let attempts = 0;
                const log = [];
                while (fiber && attempts < 40) {{
                    attempts++;
                    const props = fiber.memoizedProps || fiber.pendingProps;
                    if (props && typeof props.onChange === 'function' && props.options) {{
                        try {{
                            // ลอง flushSync ก่อน (force sync re-render ใน React 18)
                            const ReactDOM = window.ReactDOM || window.__ReactDOM;
                            if (ReactDOM && ReactDOM.flushSync) {{
                                ReactDOM.flushSync(() => props.onChange(20, {{value:20, label:'20 S'}}));
                                log.push('flushSync+onChange@' + (fiber.type?.displayName||fiber.type?.name||fiber.tag));
                            }} else {{
                                props.onChange(20, {{value:20, label:'20 S'}});
                                log.push('onChange@' + (fiber.type?.displayName||fiber.type?.name||fiber.tag));
                            }}
                        }} catch(e) {{ log.push('err:'+e.message); }}
                    }}
                    fiber = fiber.return;
                }}
                return {{log, attempts}};
            }}
        """)
        self.log(f"  [E1a]: {str(js_e1a)[:300]}")
        await page.wait_for_timeout(800)
        if await _check_ok():
            self.log("  ✅ [E1a] Duration = 20S ✓")
            return True

        # ===== E1b: direct useState hook queue.dispatch(20) =====
        # Traverse hook chain หา node ที่เก็บ number ใน [8,12,15,20] → dispatch(20)
        self.log("  [E1b] useState hook dispatch...")
        js_e1b = await page.evaluate(f"""
            () => {{
                {FIND_DURATION_JS}
                if (!paramSel) return {{err: 'no duration param'}};

                const fiberKey = Object.keys(paramSel).find(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance'));
                if (!fiberKey) return {{err: 'no fiber'}};

                const log = [];
                let fiber = paramSel[fiberKey];
                let fiberAttempts = 0;
                while (fiber && fiberAttempts < 60) {{
                    fiberAttempts++;
                    const fName = fiber.type?.displayName || fiber.type?.name || String(fiber.tag);

                    // --- E1b: scan hook chain ---
                    let hookNode = fiber.memoizedState;
                    let hookIdx = 0;
                    while (hookNode && hookIdx < 20) {{
                        hookIdx++;
                        const val = hookNode.memoizedState;
                        const dispatch = hookNode.queue?.dispatch;
                        // hook ที่เก็บ duration value (integer: 8, 12, 15, 20)
                        if (dispatch && typeof val === 'number' && [8,12,15,20].includes(val)) {{
                            try {{
                                dispatch(20);
                                log.push('hook dispatch(' + val + '→20)@' + fName + '[h' + hookIdx + ']');
                            }} catch(e) {{ log.push('dispatch-err:'+e.message); }}
                        }}
                        // hook ที่เก็บ object ที่มี duration/value field
                        if (dispatch && val && typeof val === 'object') {{
                            for (const k of ['duration','value','val','selected','current']) {{
                                if ([8,12,15,20].includes(val[k])) {{
                                    try {{
                                        dispatch({{...val, [k]:20}});
                                        log.push('hook dispatch obj('+k+'='+val[k]+'→20)@'+fName);
                                    }} catch(e) {{}}
                                }}
                            }}
                        }}
                        hookNode = hookNode.next;
                    }}

                    // --- E1c: class component setState ---
                    const inst = fiber.stateNode;
                    if (inst && typeof inst === 'object' && inst.updater && inst.state) {{
                        for (const k of Object.keys(inst.state)) {{
                            if ([8,12,15,20].includes(inst.state[k])) {{
                                try {{
                                    inst.setState({{[k]:20}});
                                    log.push('class setState('+k+'→20)@'+fName);
                                }} catch(e) {{}}
                            }}
                        }}
                    }}

                    fiber = fiber.return;
                }}
                return {{log, fiberAttempts}};
            }}
        """)
        self.log(f"  [E1b]: {str(js_e1b)[:400]}")
        await page.wait_for_timeout(800)
        if await _check_ok():
            self.log("  ✅ [E1b] Duration = 20S ✓")
            return True

        # ===== E3: pointerdown event (Ant Design 5 ฟัง pointerdown ไม่ใช่ click) =====
        self.log("  [E3] pointerdown → click duration dropdown...")
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(200)
        try:
            duration_param_e3 = await _find_duration_param()
            if duration_param_e3:
                inner_e3 = duration_param_e3.locator('.ant-select-content').first
                if await inner_e3.is_visible(timeout=1000):
                    await inner_e3.scroll_into_view_if_needed()
                    await page.wait_for_timeout(200)
                    # Dispatch pointerdown → mousedown → mouseup → click ตามลำดับ
                    for evt in ['pointerdown', 'mousedown', 'mouseup', 'click']:
                        await inner_e3.dispatch_event(evt, {'bubbles': True, 'cancelable': True, 'button': 0})
                        await page.wait_for_timeout(50)
                    self.log("  🖱 [E3] dispatched pointerdown→click")
                    await page.wait_for_timeout(1200)

                    # ตรวจ dropdown portal ที่ body
                    dd_info = await page.evaluate("""
                        () => {
                            const dd = document.querySelector('.ant-select-dropdown:not(.ant-select-dropdown-hidden)');
                            if (dd) return {open:true, items: Array.from(dd.querySelectorAll('.ant-select-item')).map(e=>e.textContent.trim()).join('|')};
                            return {open:false};
                        }
                    """)
                    self.log(f"  [E3] dropdown: {dd_info}")

                    if dd_info.get('open'):
                        for opt in ['20 S', '20S']:
                            try:
                                opt_el = page.locator(f'.ant-select-dropdown:visible .ant-select-item:has-text("{opt}")').first
                                if await opt_el.is_visible(timeout=500):
                                    await opt_el.click()
                                    self.log(f"  ✅ [E3] selected '{opt}'")
                                    await page.wait_for_timeout(500)
                                    if await _check_ok():
                                        return True
                            except Exception:
                                continue
        except Exception as e:
            self.log(f"  ⚠️ [E3]: {e}")

        # ===== E4: rc-select onSelect API =====
        self.log("  [E4] rc-select onSelect...")
        js_e4 = await page.evaluate(f"""
            () => {{
                {FIND_DURATION_JS}
                if (!paramSel) return {{err: 'no param'}};

                const fiberKey = Object.keys(paramSel).find(k => k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance'));
                if (!fiberKey) return {{err:'no fiber'}};
                let fiber = paramSel[fiberKey];
                const names = [];
                for (let i = 0; i < 50 && fiber; i++) {{
                    const n = fiber.type?.displayName || fiber.type?.name;
                    if (n) names.push(n);
                    const props = fiber.memoizedProps;
                    if (props && typeof props.onSelect === 'function') {{
                        try {{
                            props.onSelect(20, {{value:20, label:'20 S'}});
                            return {{result:'onSelect@'+n}};
                        }} catch(e) {{ return {{err:'onSelect err:'+e.message}}; }}
                    }}
                    // ลอง __reactProps on content element
                    const content = paramSel.querySelector('.ant-select-content');
                    if (content) {{
                        const pk = Object.keys(content).find(k => k.startsWith('__reactProps'));
                        if (pk) {{
                            const cp = content[pk];
                            if (cp && cp.onClick) {{
                                try {{
                                    cp.onClick({{preventDefault:()=>{{}}, stopPropagation:()=>{{}}, target:content, currentTarget:content}});
                                    return {{result:'content onClick via __reactProps'}};
                                }} catch(e) {{}}
                            }}
                        }}
                    }}
                    fiber = fiber.return;
                }}
                return {{names: names.join(','), tried: 'onSelect not found'}};
            }}
        """)
        self.log(f"  [E4]: {str(js_e4)[:300]}")
        await page.wait_for_timeout(500)
        if await _check_ok():
            self.log("  ✅ [E4] Duration = 20S ✓")
            return True

        # ===== F: Keyboard — Enter + Space + ArrowDown =====
        self.log("  [F] Keyboard navigation...")
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(200)
        try:
            duration_param_f = await _find_duration_param()
            if duration_param_f:
                inner_f = duration_param_f.locator('.ant-select-content').first
                if await inner_f.is_visible(timeout=1000):
                    await inner_f.scroll_into_view_if_needed()
                    await inner_f.focus()
                    await page.wait_for_timeout(300)
                    for open_key in ['Enter', 'Space', 'ArrowDown']:
                        await page.keyboard.press(open_key)
                        await page.wait_for_timeout(600)
                        dd_open = await page.evaluate("""
                            () => !!document.querySelector('.ant-select-dropdown:not(.ant-select-dropdown-hidden)')
                        """)
                        if dd_open:
                            self.log(f"  🔓 [F] dropdown opened via {open_key}")
                            for _ in range(8):
                                await page.keyboard.press('ArrowDown')
                                await page.wait_for_timeout(150)
                                focused_text = await page.evaluate("() => document.activeElement?.textContent?.trim() || ''")
                                if '20' in focused_text:
                                    await page.keyboard.press('Enter')
                                    await page.wait_for_timeout(500)
                                    if await _check_ok():
                                        self.log("  ✅ [F] Duration = 20S via keyboard")
                                        return True
                                    break
                            await page.keyboard.press('Escape')
                            break
        except Exception as e:
            self.log(f"  ⚠️ [F]: {e}")

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
        # กลไก download ของ Kalowave = window.open(url) → new tab
        # ต้องดัก popup page ไม่ใช่ browser download event
        async def _try_download(btn):
            import urllib.request as _urlreq
            import asyncio as _asyncio
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(c for c in product["name"][:20] if c.isalnum() or c in "- _")
            save_path = os.path.join(self.output_dir, f"{timestamp}_{safe_name}.mp4")

            # Network capture
            captured_video_urls = []
            async def _on_resp(resp):
                try:
                    url = resp.url
                    ct = (resp.headers.get("content-type") or "").lower()
                    cd = (resp.headers.get("content-disposition") or "").lower()
                    if "video" in ct or ".mp4" in url.lower() or "attachment" in cd:
                        captured_video_urls.append(url)
                        return
                    if "json" in ct and resp.status == 200:
                        try:
                            body_text = await resp.text()
                            matches = re.findall(r'https?://[^"\'<>\s]+\.mp4[^"\'<>\s]*', body_text)
                            captured_video_urls.extend(matches)
                        except Exception:
                            pass
                except Exception:
                    pass

            page.on("response", _on_resp)

            async def _save_from_url(url):
                try:
                    self.log(f"  ⬇️ ดาวน์โหลด: {url[:100]}")
                    req = _urlreq.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
                    with _urlreq.urlopen(req, timeout=120) as r, open(save_path, 'wb') as f:
                        f.write(r.read())
                    sz = os.path.getsize(save_path) if os.path.exists(save_path) else 0
                    if sz > 100_000:
                        self.log(f"  ✅ บันทึก ({sz // 1024}KB): {os.path.basename(save_path)}")
                        return save_path
                    self.log(f"  ⚠️ ไฟล์เล็กเกินไป: {sz} bytes")
                except Exception as eu:
                    self.log(f"  ⚠️ urllib: {eu}")
                return None

            # Intercept window.open ผ่าน JS (ก่อนคลิกใดๆ)
            async def _inject_open_intercept():
                try:
                    await page.evaluate("""
                        () => {
                            if (!window.__kalo_opened) {
                                window.__kalo_opened = [];
                                const orig = window.open;
                                window.open = function(url, ...a) {
                                    if (url) window.__kalo_opened.push(String(url));
                                    return orig.apply(this, [url, ...a]);
                                };
                            }
                        }
                    """)
                except Exception:
                    pass

            async def _get_opened_urls():
                try:
                    return await page.evaluate("() => window.__kalo_opened || []")
                except Exception:
                    return []

            # ── helper: คลิก el แล้วรอ popup/download/window.open (timeout วิ) ──
            async def _click_and_capture(el, label="btn", timeout_s=15):
                await _inject_open_intercept()
                # reset window.open list
                try:
                    await page.evaluate("() => { window.__kalo_opened = []; }")
                except Exception:
                    pass

                # ตั้ง popup listener ก่อนคลิก
                popup_fut = None
                try:
                    popup_fut = page.context.wait_for_event("page", timeout=timeout_s * 1000)
                except Exception:
                    pass

                # ลองรอ browser download ด้วย (fast path)
                dl_result = None
                try:
                    async with page.expect_download(timeout=8_000) as dl_info:
                        await el.click()
                        self.log(f"  🖱 คลิก {label}")
                    dl = await dl_info.value
                    await dl.save_as(save_path)
                    sz = os.path.getsize(save_path) if os.path.exists(save_path) else 0
                    if sz > 10_000:
                        self.log(f"  ✅ browser download ({sz//1024}KB)")
                        return save_path
                except Exception:
                    # ไม่มี browser download ภายใน 8s → เช็ค popup
                    pass

                await page.wait_for_timeout(2_000)

                # เช็ค window.open
                opened = await _get_opened_urls()
                self.log(f"  🪟 window.open: {opened}")
                for url in opened:
                    if url and url.startswith('http'):
                        r = await _save_from_url(url)
                        if r:
                            return r

                # เช็ค popup (new tab)
                if popup_fut:
                    try:
                        new_page = await _asyncio.wait_for(
                            _asyncio.ensure_future(popup_fut), timeout=timeout_s
                        )
                        popup_url = new_page.url
                        self.log(f"  🔗 popup URL: {popup_url[:120]}")
                        try:
                            await new_page.close()
                        except Exception:
                            pass
                        if popup_url and popup_url not in ('about:blank', ''):
                            r = await _save_from_url(popup_url)
                            if r:
                                return r
                    except Exception:
                        pass

                # เช็ค network capture
                unique = list(dict.fromkeys(captured_video_urls))
                self.log(f"  📡 network: {len(unique)} URLs → {unique[:2]}")
                for url in reversed(unique):
                    r = await _save_from_url(url)
                    if r:
                        return r

                return None

            try:
                # ── PHASE A: คลิก "ดาวน์โหลด" ครั้งแรก ──────────────────────────
                self.log("  🖱 Phase A: คลิก ดาวน์โหลด ครั้งแรก...")
                result = await _click_and_capture(btn, "ดาวน์โหลด(1)")
                if result:
                    return result

                # ── Screenshot หลัง click ──────────────────────────────────────
                await page.wait_for_timeout(1_000)
                try:
                    await page.screenshot(path=os.path.join(self.output_dir, "debug_dl_click.png"))
                    # Log ทุก element ที่ visible พร้อม class (เพื่อ debug)
                    items_info = await page.evaluate("""
                        () => Array.from(document.querySelectorAll(
                            'button,a,li,[role="menuitem"],[role="option"]'
                        ))
                        .filter(e => e.offsetParent !== null && e.textContent.trim())
                        .map(e => {
                            const cls = (e.className || '').substring(0, 30);
                            const txt = e.textContent.trim().substring(0, 30);
                            return txt + '(' + cls + ')';
                        })
                        .join(' | ')
                    """)
                    self.log(f"  📸 after_dl1 | {items_info[:600]}")
                except Exception:
                    pass

                # ── PHASE B: คลิก element ที่ปรากฏใหม่หลัง phase A ──────────────
                # ลำดับลอง: exact "ดาวน์โหลด" text (ครั้งที่ 2), quality 1080/720 ใน menu
                phase_b_sels = [
                    ('button:has-text("ดาวน์โหลด")', 'ดาวน์โหลด(2nd btn)'),
                    ('a:has-text("ดาวน์โหลด")', 'ดาวน์โหลด(2nd link)'),
                    ('[role="menuitem"]:has-text("ดาวน์โหลด")', 'ดาวน์โหลด(menuitem)'),
                    ('[role="menuitem"]:has-text("1080")', '1080(menuitem)'),
                    ('[role="menuitem"]:has-text("720")', '720(menuitem)'),
                    ('li:has-text("1080")', '1080(li)'),
                    ('li:has-text("720")', '720(li)'),
                    ('button:has-text("1080")', '1080(btn)'),
                    ('button:has-text("720")', '720(btn)'),
                    ('a[download]', 'a[download]'),
                    ('a[href*=".mp4"]', 'a[href*.mp4]'),
                    # Ant Design dropdown items (exact class)
                    ('.ant-dropdown-menu-item:has-text("ดาวน์โหลด")', 'ant-dl'),
                    ('.ant-dropdown-menu-item:has-text("1080")', 'ant-1080'),
                    ('.ant-dropdown-menu-item:has-text("720")', 'ant-720'),
                    ('.ant-dropdown-menu-item', 'ant-menu-item(any)'),
                ]
                for sel, label in phase_b_sels:
                    try:
                        els = page.locator(sel)
                        cnt = await els.count()
                        if cnt == 0:
                            continue

                        # ถ้า "ดาวน์โหลด" มีหลายตัว → ใช้ตัวสุดท้าย (ใหม่ที่สุด)
                        el = els.last if cnt > 1 else els.first
                        if not await el.is_visible(timeout=500):
                            continue

                        # check href ก่อน
                        href = None
                        try:
                            href = await el.get_attribute('href')
                        except Exception:
                            pass
                        if href and href.startswith('http'):
                            self.log(f"  🔗 href: {href[:100]}")
                            r = await _save_from_url(href)
                            if r:
                                return r

                        result = await _click_and_capture(el, label)
                        if result:
                            return result
                        # ถ้าคลิกแล้วไม่ได้ → break ออกจาก loop (ไม่ลอง selector อื่น)
                        break
                    except Exception:
                        continue

                # ── PHASE C: scan DOM หา video URL ───────────────────────────────
                dom_url = await page.evaluate("""
                    () => {
                        for (const a of document.querySelectorAll('a[href],[data-url],[data-src],source[src],video[src]')) {
                            const url = a.href || a.src || a.getAttribute('data-url') || a.getAttribute('data-src') || a.getAttribute('src') || '';
                            if (url.startsWith('http') && (url.includes('.mp4') || url.includes('/video/') || url.includes('download'))) return url;
                        }
                        return null;
                    }
                """)
                if dom_url:
                    self.log(f"  🔍 DOM URL: {dom_url[:120]}")
                    r = await _save_from_url(dom_url)
                    if r:
                        return r

                self.log("  ❌ ดาวน์โหลดไม่สำเร็จ — ดู debug_dl_click.png")
                return None

            except Exception as e:
                self.log(f"  ⚠️ download error: {e}")
                return None
            finally:
                try:
                    page.remove_listener("response", _on_resp)
                except Exception:
                    pass

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

    # ===== TikTok Auto-Post =====

    async def _post_to_tiktok(self, video_path: str, product_name: str) -> str:
        """Upload วิดีโอไปยัง TikTok Inbox (ผู้ใช้ edit & post เอง)
        คืนค่า publish_id ถ้าสำเร็จ, "" ถ้าข้าม
        """
        import httpx

        # โหลด token file
        token_file = os.path.join(os.path.dirname(self.state_file), "tiktok_token.json")
        if not os.path.exists(token_file):
            self.log("⏭ TikTok: ยังไม่ได้ connect — ข้าม (ไปที่ /tiktok-auth เพื่อเชื่อมต่อ)")
            return ""

        with open(token_file) as f:
            token_data = json.load(f)

        access_token = token_data.get("access_token", "")
        if not access_token:
            self.log("⚠️ TikTok token ว่าง — ข้าม")
            return ""

        if not video_path or not os.path.exists(video_path):
            self.log(f"⚠️ TikTok: ไม่พบไฟล์ {video_path} — ข้าม")
            return ""

        file_size = os.path.getsize(video_path)
        title = f"สินค้าน่าซื้อ! {product_name[:80]} 🛍️ #TikTokShop #affiliate"

        self.log(f"📤 TikTok: กำลัง upload {os.path.basename(video_path)} ({file_size//1024}KB)...")

        try:
            # Step 1: Init upload (inbox = draft ให้ user publish เอง)
            init_resp = httpx.post(
                "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json; charset=UTF-8",
                },
                json={
                    "source_info": {
                        "source": "FILE_UPLOAD",
                        "video_size": file_size,
                        "chunk_size": file_size,
                        "total_chunk_count": 1,
                    }
                },
                timeout=30,
            )
            init_data = init_resp.json()
            self.log(f"  TikTok init: {str(init_data)[:200]}")

            err = init_data.get("error", {})
            if err.get("code", "ok") != "ok":
                self.log(f"❌ TikTok init error: {err}")
                return ""

            publish_id = init_data["data"]["publish_id"]
            upload_url = init_data["data"]["upload_url"]

            # Step 2: Upload file chunk
            with open(video_path, "rb") as f:
                video_bytes = f.read()

            upload_resp = httpx.put(
                upload_url,
                content=video_bytes,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
                    "Content-Length": str(file_size),
                },
                timeout=180,
            )
            self.log(f"  TikTok upload status: {upload_resp.status_code}")

            if upload_resp.status_code not in [200, 201, 204, 206]:
                self.log(f"❌ TikTok upload failed: {upload_resp.status_code} {upload_resp.text[:200]}")
                return ""

            self.log(f"✅ TikTok: upload สำเร็จ! publish_id={publish_id} (บันทึกเป็น draft)")
            return publish_id

        except Exception as e:
            self.log(f"❌ TikTok post error: {e}")
            return ""
