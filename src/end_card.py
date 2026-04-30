"""
End-card Generator — Hybrid mode

สร้าง 5 วินาที end-card จาก:
- รูปสินค้าจริง (data/products/{name}.jpg)
- Pink gradient background
- Text overlay: CTA Thai + arrow
- ไม่มี zoom (รูปนิ่ง 100% ไม่ crop)

แล้ว concat ต่อท้ายคลิป cartoon
"""

import os
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCTS_DIR = os.path.join(PROJECT_ROOT, "data", "products")


def has_product_image(supplement: dict) -> bool:
    img = supplement.get("product_image", "")
    if not img:
        return False
    return os.path.exists(os.path.join(PRODUCTS_DIR, img))


def get_product_image_path(supplement: dict) -> str:
    return os.path.join(PRODUCTS_DIR, supplement["product_image"])


def _compose_end_card_image(
    product_path: str,
    cta_th: str,
    output_png: str,
    canvas_w: int = 848,
    canvas_h: int = 480,
):
    """ใช้ PIL ทำ static end-card image ที่มี gradient bg + product + Thai text"""
    # 1. Pink gradient background
    bg = Image.new("RGB", (canvas_w, canvas_h), "#FFE5EC")
    draw = ImageDraw.Draw(bg)
    for y in range(canvas_h):
        ratio = y / canvas_h
        r = int(255 - ratio * 20)
        g = int(228 - ratio * 30)
        b = int(236 - ratio * 20)
        draw.rectangle([(0, y), (canvas_w, y + 1)], fill=(r, g, b))

    # 2. Product image — fit ใน canvas โดยไม่ crop
    product = Image.open(product_path).convert("RGB")
    # คำนวณขนาดให้รูปสินค้าสูงสุด 70% ของ canvas height
    target_h = int(canvas_h * 0.75)
    aspect = product.width / product.height
    target_w = int(target_h * aspect)
    if target_w > canvas_w * 0.5:
        target_w = int(canvas_w * 0.5)
        target_h = int(target_w / aspect)
    product = product.resize((target_w, target_h), Image.LANCZOS)

    # วางขวดด้านซ้าย ตรงกลางแนวตั้ง
    px = int(canvas_w * 0.1)
    py = (canvas_h - target_h) // 2
    bg.paste(product, (px, py))

    # 3. Text ด้านขวา (Thai CTA)
    try:
        # หา Thai font จาก Windows
        font_paths = [
            "C:/Windows/Fonts/leelawui.ttf",  # Leelawadee UI
            "C:/Windows/Fonts/tahoma.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]
        font_big = None
        font_med = None
        for fp in font_paths:
            if os.path.exists(fp):
                font_big = ImageFont.truetype(fp, 38)
                font_med = ImageFont.truetype(fp, 28)
                break
        if not font_big:
            font_big = font_med = ImageFont.load_default()
    except Exception:
        font_big = font_med = ImageFont.load_default()

    # Right side text area
    text_x = int(canvas_w * 0.55)
    text_y = int(canvas_h * 0.25)

    # CTA bubble background (white rounded rect)
    bubble = Image.new("RGBA", (canvas_w - text_x - 30, 220), (255, 255, 255, 230))
    bubble_draw = ImageDraw.Draw(bubble)
    bubble_draw.rounded_rectangle(
        [(0, 0), bubble.size], radius=20, fill=(255, 255, 255, 240),
        outline=(255, 107, 157, 255), width=3,
    )
    bg.paste(bubble, (text_x, text_y), bubble)

    # Title
    draw = ImageDraw.Draw(bg)
    draw.text((text_x + 20, text_y + 25), "🛒 ตะกร้า", fill="#FF6B9D", font=font_big)

    # CTA text — wrap if too long
    cta_lines = []
    words = cta_th.split()
    line = ""
    max_chars = 18
    for w in words:
        if len(line) + len(w) + 1 > max_chars:
            cta_lines.append(line.strip())
            line = w + " "
        else:
            line += w + " "
    if line:
        cta_lines.append(line.strip())

    for i, l in enumerate(cta_lines[:3]):
        draw.text((text_x + 20, text_y + 80 + i * 38), l, fill="#333333", font=font_med)

    # Arrow ↓
    draw.text((text_x + 20, text_y + 200), "↓ ↓ ↓", fill="#FF6B9D", font=font_big)

    bg.save(output_png, quality=95)


def make_end_card(
    product_image_path: str,
    cta_text_th: str,
    output_path: str,
    duration: float = 5.0,
    width: int = 848,
    height: int = 480,
) -> str:
    """
    สร้าง 5s end-card mp4 จากรูปนิ่ง + text + gradient bg
    """
    if not os.path.exists(product_image_path):
        raise FileNotFoundError(f"ไม่เจอรูป: {product_image_path}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Step 1: composite static image with PIL
    composed_png = os.path.splitext(output_path)[0] + "_composed.png"
    _compose_end_card_image(product_image_path, cta_text_th, composed_png, width, height)

    # Step 2: convert to 5s video with subtle pulse
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", composed_png,
        "-f", "lavfi",
        "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-vf", f"scale={width}:{height}",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        "-t", str(duration),
        "-shortest",
        "-r", "25",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg end-card failed: {result.stderr[-500:]}")

    # cleanup
    if os.path.exists(composed_png):
        os.remove(composed_png)

    print(f"✅ End-card created: {output_path}")
    return output_path


def append_end_card(main_video: str, end_card: str, output_path: str) -> str:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", main_video,
        "-i", end_card,
        "-filter_complex",
        "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-c:a", "aac",
        "-preset", "fast",
        output_path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Append failed: {r.stderr[-500:]}")
    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"✅ Final: {output_path} ({size_mb:.1f} MB)")
    return output_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 4:
        make_end_card(sys.argv[1], sys.argv[2], sys.argv[3])
