"""
Variety Config v2 — TikTok Compliance Hardened (2026-04-30)
Format: ดอลอ้วนมีอาการ → ลุงพันสอน (ไม่ดุเกินไป) → ทานทุกวัน → ดีขึ้นค่อยเป็นค่อยไป → CTA
"""

# ============================================================
# 0. STYLE LOCK
# ============================================================

STYLE_PREFIX = (
    "3D Pixar Disney cartoon animation style, anthropomorphic animal characters only, "
    "NO real humans, NO photorealistic style, NO live action footage. "
)

STYLE_SUFFIX = (
    " RENDER STYLE: 3D animated cartoon ONLY. All characters MUST be cute anthropomorphic "
    "animals (red pandas, etc.) — NEVER real human beings, NEVER realistic people, "
    "NEVER live-action. Disney Pixar quality animation throughout."
)


# ============================================================
# 1. CHARACTERS
# ============================================================

MAIN_CHARACTER = (
    "Dolla (ดอลอ้วน): an extremely cute chubby round red panda character with fluffy "
    "reddish-brown fur, big round sparkling eyes, small white eyebrows, "
    "and a tiny pink nose, very chubby round tummy, kawaii adorable expression, "
    "in 3D Pixar Disney cartoon style"
)

# v2.1: Uncle Pan — strict comedy uncle vibe (ดุน่ารัก ไม่ bully)
EDUCATOR_CHARACTER = (
    "Uncle Pan (ลุงพัน): an older chubby red panda character with one thick eyebrow "
    "raised in stern disapproval behind small round eyeglasses pushed down his nose, "
    "wearing a brown teacher's vest, holds a clipboard or scroll (NOT a stick or weapon), "
    "stands with hands-on-hips or arms-crossed posture, exasperated sigh expression "
    "like a frustrated but loving uncle who has seen this mistake before, "
    "slightly grumpy comedy face but eyes still warm. "
    "Tone: stern scolding like a comedy school teacher — strict but caring, "
    "NEVER yelling in face, NEVER pointing aggressive stick, NEVER threatening. "
    "Voice firm and no-nonsense but not screaming. Body language: shake head, "
    "facepalm, or 'ฮ่าๆๆ' exasperated chuckle. NEVER wears doctor coat or medical uniform. "
    "In matching 3D Pixar Disney cartoon style."
)


# ============================================================
# 2. CAMEO CHARACTERS (random 0-2)
# ============================================================

CAMEO_CHARACTERS = [
    {
        "name_th": "น้องเบลล์",
        "name_en": "Bluebell",
        "species": "British Shorthair cat",
        "description": (
            "Bluebell (น้องเบลล์): an elegant chubby British Shorthair cat with soft "
            "blue-grey fur, big round amber-yellow eyes, plump cheeks, wearing a tiny "
            "pearl bow on her ear, refined and dainty, slightly snobby but secretly "
            "soft-hearted, in 3D Pixar Disney cartoon style"
        ),
        "personality": "elegant, refined, easily offended in a cute way",
        "typical_role": "the fancy friend who watches Dolla's drama and gasps",
    },
    {
        "name_th": "พี่หม่ำ",
        "name_en": "Mam",
        "species": "Giant Panda",
        "description": (
            "Mam (พี่หม่ำ): a huge round fluffy giant panda character with classic "
            "black and white fur, gentle big black-circled eyes, eternal smile, "
            "always carrying or eating bamboo, super chubby, kind and goofy big brother, "
            "in matching 3D Pixar Disney cartoon style"
        ),
        "personality": "gentle giant, food-obsessed, loyal big brother",
        "typical_role": "the big brother who tries to help",
    },
    {
        "name_th": "เจ้ามอจิ",
        "name_en": "Mochi",
        "species": "Shiba Inu dog",
        "description": (
            "Mochi (เจ้ามอจิ): an energetic chubby Shiba Inu puppy with cream-orange fur, "
            "perky triangular ears, curly fluffy tail, classic Shiba smug smile, big "
            "playful round eyes, always bouncing with excitement, "
            "in matching 3D Pixar Disney cartoon style"
        ),
        "personality": "hyperactive, mischievous, loyal sidekick",
        "typical_role": "the energetic chaos friend",
    },
]


# ============================================================
# 3. SUPPLEMENT CATEGORIES (v2 — TikTok compliant)
# ============================================================
#
# v2 changes:
# - solution_visual: time-skip narrative ("ทานทุกวัน 7 วัน") ไม่ instant
# - scolding_th: ลด aggression (no ตะคอก no ไม้เรียว)
# - explanation_th: คำว่า "บำรุง" "ดูแล" "เสริม" แทน "พัง"
# - cta_th: nurturing language, ห้าม scare tactics
# - duration: ทุกฉากต้องระบุ "passage of time" ในฉากที่ 2

SUPPLEMENT_CATEGORIES = [
    {
        "name_th": "เจลลี่ไฟเบอร์ดีท็อกซ์",
        "name_en": "Fiber Detox Jelly",
        "product_image": "fiber_jelly.jpg",
        "shop_link": "",
        "target_th": "คนต้องการดูแลระบบย่อยอาหาร",
        "symptom_th": "พุงป่อง อึดอัด ขับถ่ายไม่สม่ำเสมอ",
        "scene1_idea": (
            "Dolla the chubby red panda has eaten too much, looking uncomfortable "
            "while sitting on a chair holding his round belly with a slightly "
            "pained but cute expression"
        ),
        "scolding_th": "อ้าว ดอลกินไผ่เยอะอีกแล้วเหรอ ลุงเตือนแล้วนะว่าต้องทานไฟเบอร์ด้วย",
        "explanation_th": "ลำไส้ต้องการไฟเบอร์เพื่อทำงานสมดุลนะ ไม่งั้นการขับถ่ายไม่ลงตัว",
        "solution_visual": (
            "Time-skip montage: Dolla takes one fiber jelly sachet daily for 7 days "
            "(show calendar pages flipping or 'Day 1, Day 7' text). Gradually his "
            "tummy feels lighter, he walks around comfortably with happy smile. "
            "Small disclaimer text appears in corner: '*ผลลัพธ์ขึ้นอยู่กับแต่ละบุคคล'"
        ),
        "cta_th": "อยากให้การขับถ่ายลงตัว ลองสั่งไฟเบอร์เจลลี่ในตะกร้าได้เลยจ้า",
    },
    {
        "name_th": "ซิงค์ ดูแลผิว",
        "name_en": "Zinc",
        "product_image": "zinc.jpg",
        "shop_link": "",
        "target_th": "วัยรุ่น คนต้องการเสริมผิวสุขภาพดี",
        "symptom_th": "ผิวมัน ผิวไม่สดใส อยากดูแลผิวจากภายใน",
        "scene1_idea": (
            "Dolla the chubby red panda is dressed up for a date, looking in a mirror, "
            "noticing his skin is dull and oily, looks slightly disappointed and "
            "wishes his skin was healthier"
        ),
        "scolding_th": "เห้อ! ดอล ลุงบอกกี่ทีแล้ว! ทำไมไม่ดูแลตัวเองล่ะ! ผิวต้องบำรุงด้วยซิงค์นะ ฟังลุงบ้างสิ!",
        "explanation_th": "เนี่ย! ซิงค์เป็นแร่ธาตุสำคัญ ช่วยเสริมการดูแลผิว ผม เล็บ ต้องทานเสริมประจำสิแก!",
        "solution_visual": (
            "Time-skip narrative: Dolla takes one Zinc capsule daily. Calendar shows "
            "'Day 1, Day 14, Day 30' progression. Gradually his fur looks healthier "
            "and shinier, eyes bright. He looks confident in mirror. "
            "Small disclaimer text in corner: '*ผลลัพธ์ขึ้นอยู่กับแต่ละบุคคล'"
        ),
        "cta_th": "อยากเสริมการดูแลผิว ลองทานซิงค์เป็นประจำดูนะ กดในตะกร้าได้เลยจ้า",
    },
    {
        "name_th": "คอลลาเจนชง",
        "name_en": "Collagen Drink",
        "product_image": "collagen.jpg",
        "shop_link": "",
        "target_th": "คนต้องการบำรุงผิว",
        "symptom_th": "ผิวแห้ง อยากเสริมความชุ่มชื้น",
        "scene1_idea": (
            "Dolla the chubby red panda just came back from being outdoors in the sun, "
            "his fur looks dry and tired, looks at himself wishing his skin had more "
            "glow"
        ),
        "scolding_th": "ดอล ตากแดดทั้งวันแบบนี้ ผิวต้องการบำรุงเพิ่มนะ",
        "explanation_th": "คอลลาเจนช่วยเสริมความชุ่มชื้นจากภายใน ทานเป็นประจำผิวจะดูดีขึ้น",
        "solution_visual": (
            "Time-skip: Dolla drinks collagen drink every morning. Show 'Week 1, "
            "Week 4' progression. Gradually his fur becomes softer, looks more glowing "
            "and healthy. Confident smile. "
            "Disclaimer: '*ผลลัพธ์ขึ้นอยู่กับแต่ละบุคคล'"
        ),
        "cta_th": "อยากดูแลผิวจากภายใน ลองคอลลาเจนชงดูนะ กดในตะกร้าได้เลยจ้า",
    },
    {
        "name_th": "กาแฟคุมหิว",
        "name_en": "Diet Coffee",
        "product_image": "diet_coffee.jpg",
        "shop_link": "",
        "target_th": "คนต้องการดูแลน้ำหนัก",
        "symptom_th": "หิวจุบจิบบ่อย อยากคุมการกินจุบจิบ",
        "scene1_idea": (
            "Dolla and friends having afternoon snacks, Dolla looks tempted by sweets "
            "but wants to manage his cravings"
        ),
        "scolding_th": "ดอล กินขนมระหว่างมื้อบ่อยๆ ลุงห่วงสุขภาพแกนะ",
        "explanation_th": "กาแฟคุมหิวมีสารช่วยให้อิ่มนาน ดื่มก่อนอาหารช่วยควบคุมพลังงาน",
        "solution_visual": (
            "Time-skip: Dolla drinks diet coffee before each meal. 'Day 1, Week 2, "
            "Week 4' progression. He naturally feels less hungry between meals, "
            "looks healthier and more energetic. "
            "Disclaimer: '*ผลลัพธ์ขึ้นอยู่กับแต่ละบุคคล'"
        ),
        "cta_th": "อยากดูแลการกินจุบจิบ ลองกาแฟคุมหิวดูนะ กดในตะกร้าได้เลยจ้า",
    },
    {
        "name_th": "ลูทีนบำรุงสายตา",
        "name_en": "Lutein",
        "product_image": "lutein.jpg",
        "shop_link": "",
        "target_th": "คนใช้สายตาเยอะ จ้องจอนาน",
        "symptom_th": "ตาล้า ตาแห้งจากการจ้องจอ",
        "scene1_idea": (
            "Dolla the chubby red panda wearing thick eyeglasses, rubbing tired eyes "
            "after staring at gaming screen for long hours, looks fatigued"
        ),
        "scolding_th": "ดอล จ้องจอนานๆ แบบนี้ ดวงตาต้องการการบำรุงนะ",
        "explanation_th": "ลูทีนเป็นสารอาหารสำหรับดวงตา ทานเสริมเป็นประจำช่วยดูแลสายตา",
        "solution_visual": (
            "Time-skip: Dolla takes lutein capsule daily. 'Day 1, Day 14, Day 30'. "
            "Gradually his eyes look brighter, less tired, he can enjoy gaming and "
            "work without strain. "
            "Disclaimer: '*ผลลัพธ์ขึ้นอยู่กับแต่ละบุคคล'"
        ),
        "cta_th": "อยากดูแลดวงตาจากการใช้งาน ลองลูทีนดูนะ กดในตะกร้าได้เลยจ้า",
    },
    {
        "name_th": "เวย์โปรตีนพืช",
        "name_en": "Plant Protein",
        "product_image": "plant_protein.jpg",
        "shop_link": "",
        "target_th": "คนออกกำลังกาย ดูแลสุขภาพ",
        "symptom_th": "ต้องการเสริมโปรตีนเพื่อสุขภาพ",
        "scene1_idea": (
            "Dolla tries to exercise with small dumbbells but lacks energy, looks "
            "tired after a short workout"
        ),
        "scolding_th": "ดอล ออกกำลังกายต้องบำรุงด้วยโปรตีนนะ ร่างกายต้องการ",
        "explanation_th": "เวย์โปรตีนพืชช่วยเสริมโปรตีนสำหรับการออกกำลังกาย ทานหลังเล่นกีฬา",
        "solution_visual": (
            "Time-skip: Dolla drinks protein shake after each workout. 'Week 1, "
            "Week 4, Week 8'. Gradually he has more energy, can lift heavier weights "
            "comfortably, looks fit and confident. "
            "Disclaimer: '*ผลลัพธ์ขึ้นอยู่กับแต่ละบุคคล'"
        ),
        "cta_th": "อยากเสริมโปรตีนสำหรับออกกำลังกาย ลองเวย์พืชดูนะ กดในตะกร้าได้",
    },
    {
        "name_th": "วิตามินซี",
        "name_en": "Vitamin C",
        "product_image": "vitamin_c.jpg",
        "shop_link": "",
        "target_th": "คนต้องการเสริมภูมิคุ้มกัน",
        "symptom_th": "อยากดูแลสุขภาพช่วงอากาศเปลี่ยน",
        "scene1_idea": (
            "Dolla walking outside in cool weather, looking like he wants to take "
            "better care of his health, sneezes once cutely"
        ),
        "scolding_th": "ดอล อากาศเปลี่ยนแบบนี้ต้องดูแลตัวเองนะ ทานวิตซีบ้างไหม",
        "explanation_th": "วิตามินซีช่วยเสริมการดูแลสุขภาพ ทานเป็นประจำเสริมภูมิคุ้มกันได้",
        "solution_visual": (
            "Time-skip: Dolla takes vitamin C tablet daily. 'Day 1, Week 2, Month 1'. "
            "Gradually he feels more energetic, healthy fur, walks confidently in any "
            "weather. "
            "Disclaimer: '*ผลลัพธ์ขึ้นอยู่กับแต่ละบุคคล'"
        ),
        "cta_th": "อยากเสริมการดูแลสุขภาพ ลองวิตซีเป็นประจำดูนะ กดในตะกร้าได้เลย",
    },
    {
        "name_th": "โพรไบโอติก",
        "name_en": "Probiotic",
        "product_image": "probiotic.jpg",
        "shop_link": "",
        "target_th": "คนต้องการดูแลระบบลำไส้",
        "symptom_th": "อยากดูแลสุขภาพลำไส้และระบบย่อย",
        "scene1_idea": (
            "Dolla the chubby red panda holding his belly looking slightly uncomfortable "
            "after eating, expression of mild bloating"
        ),
        "scolding_th": "ดอล รู้สึกอึดอัดท้องบ่อยๆ ลองทานโพรไบโอติกบำรุงดูสิ",
        "explanation_th": "โพรไบโอติกเป็นจุลินทรีย์ดี ช่วยดูแลสมดุลของระบบย่อยอาหาร",
        "solution_visual": (
            "Time-skip: Dolla drinks probiotic mix daily. 'Day 1, Week 2, Week 4'. "
            "Gradually feels comfortable, energetic, healthy glow. "
            "Disclaimer: '*ผลลัพธ์ขึ้นอยู่กับแต่ละบุคคล'"
        ),
        "cta_th": "อยากดูแลระบบลำไส้ ลองโพรไบโอติกดูนะ กดในตะกร้าได้เลยจ้า",
    },
]


# ============================================================
# 4. SETTINGS
# ============================================================

SETTINGS = [
    "cozy bamboo forest cottage with warm sunset lighting",
    "modern bright kitchen with marble counters and houseplants",
    "magical glowing fairy garden with floating sparkles",
    "cozy living room with bookshelves and soft lamps",
    "Japanese-style tea room with sliding paper doors",
    "outdoor cafe with cherry blossom trees and bokeh lights",
    "enchanted forest clearing with mushroom houses",
    "sunny meadow with rolling hills and butterflies",
]


# ============================================================
# 5. MOODS — softer
# ============================================================

MOODS = [
    "cute kawaii cheerful and uplifting",
    "warm storytelling like a children's book",
    "educational explainer with friendly tone",
    "cozy warm vibe",
    "soft pastel dreamy aesthetic",
    "vibrant bright colors with fun animation",
]


# ============================================================
# 6. CAMERA ANGLES
# ============================================================

CAMERA_ANGLES = [
    "wide cinematic establishing shot revealing the entire scene with both characters",
    "full body medium-wide shot showing both characters interacting",
    "warm natural angle for friendly conversation feel",
    "dolly out reveal shot starting close on Dolla then pulling back to show Uncle Pan",
    "cinematic wide angle 24mm lens with depth of field",
    "over-the-shoulder shot from Uncle Pan toward Dolla",
    "sweeping cinematic crane shot",
    "split-screen wide shot with Dolla on left, Uncle Pan on right",
    "tracking shot following Dolla",
    "establishing wide shot of the location with both characters",
]
