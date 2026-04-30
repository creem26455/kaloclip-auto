"""
FFmpeg merge — รวม 2 คลิปเป็น 1 คลิปแบบ seamless
"""

import os
import subprocess
from pathlib import Path


def merge_clips(clip1: str, clip2: str, output_path: str) -> str:
    """
    รวมคลิปด้วย concat demuxer (เร็ว, ไม่ต้อง re-encode ถ้า codec เหมือน)

    หมายเหตุ: ถ้า codec/resolution ต่าง จะ fallback ไปใช้ filter_complex (re-encode)
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # สร้าง concat list
    concat_list = Path(output_path).parent / "concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        f.write(f"file '{os.path.abspath(clip1)}'\n")
        f.write(f"file '{os.path.abspath(clip2)}'\n")

    # Method 1: concat demuxer (เร็ว — ใช้ได้ถ้าทั้ง 2 คลิป encode เหมือนกัน)
    cmd_fast = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        output_path,
    ]
    result = subprocess.run(cmd_fast, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"⚠️ Fast concat ล้มเหลว — ลอง re-encode")
        # Method 2: filter_complex (ช้ากว่าแต่ทำงานได้แน่นอน)
        cmd_safe = [
            "ffmpeg", "-y",
            "-i", clip1,
            "-i", clip2,
            "-filter_complex",
            "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]",
            "-map", "[v]",
            "-map", "[a]",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-preset", "fast",
            output_path,
        ]
        result = subprocess.run(cmd_safe, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg merge failed: {result.stderr}")

    # Cleanup
    if concat_list.exists():
        concat_list.unlink()

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"✅ Merged: {output_path} ({size_mb:.1f} MB)")
    return output_path


def get_video_duration(video_path: str) -> float:
    """อ่านความยาวคลิป (วินาที)"""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 4:
        merge_clips(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("Usage: python ffmpeg_merge.py <clip1> <clip2> <output>")
