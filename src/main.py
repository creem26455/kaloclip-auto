"""
Main orchestrator — Phase 1 (Proof of Concept)
Hardcoded prompts → Grok gen → FFmpeg merge → save mp4

ใช้รัน: python src/main.py
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"), override=True)

sys.path.insert(0, os.path.dirname(__file__))
from grok_client import generate_video, download_video
from ffmpeg_merge import merge_clips, get_video_duration

OUTPUT_DIR = Path("data/downloads")
TEMP_DIR = Path("data/temp")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)


# Phase 1: Hardcoded test prompts
TEST_SCRIPT = {
    "title": "Cute Puppy Adventure",
    "scene1_prompt": (
        "A fluffy golden retriever puppy with big curious eyes "
        "discovers a butterfly in a sunny garden, soft cinematic lighting, "
        "shallow depth of field, vibrant colors"
    ),
    "scene2_prompt": (
        "The same golden retriever puppy chases the butterfly playfully "
        "through tall green grass, slow motion, golden hour, "
        "joyful music in background"
    ),
}


def run_phase1():
    print("=" * 60)
    print("🎬 TikTok Automation — Phase 1 PoC")
    print("=" * 60)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    title = TEST_SCRIPT["title"].replace(" ", "_")

    scene1_path = TEMP_DIR / f"{timestamp}_scene1.mp4"
    scene2_path = TEMP_DIR / f"{timestamp}_scene2.mp4"
    output_path = OUTPUT_DIR / f"{timestamp}_{title}.mp4"

    # Scene 1 (15 วินาที, 480p — ถูกพอ + คุณภาพ TikTok ดี)
    print(f"\n📹 [1/3] Generating Scene 1...")
    print(f"   Prompt: {TEST_SCRIPT['scene1_prompt'][:80]}...")
    s1 = generate_video(prompt=TEST_SCRIPT["scene1_prompt"], duration=15)
    download_video(s1["video_url"], str(scene1_path))
    print(f"   💰 Cost: ${s1['cost_usd']:.2f}")

    # Scene 2
    print(f"\n📹 [2/3] Generating Scene 2...")
    print(f"   Prompt: {TEST_SCRIPT['scene2_prompt'][:80]}...")
    s2 = generate_video(prompt=TEST_SCRIPT["scene2_prompt"], duration=15)
    download_video(s2["video_url"], str(scene2_path))
    print(f"   💰 Cost: ${s2['cost_usd']:.2f}")

    # Merge
    print(f"\n🎞️ [3/3] Merging clips...")
    merge_clips(str(scene1_path), str(scene2_path), str(output_path))

    duration = get_video_duration(str(output_path))
    size_mb = os.path.getsize(output_path) / 1024 / 1024

    print("\n" + "=" * 60)
    print(f"✅ DONE: {output_path}")
    print(f"   Duration: {duration:.1f}s")
    print(f"   Size: {size_mb:.1f} MB")
    print("=" * 60)

    # Cleanup temp
    scene1_path.unlink(missing_ok=True)
    scene2_path.unlink(missing_ok=True)


if __name__ == "__main__":
    run_phase1()
