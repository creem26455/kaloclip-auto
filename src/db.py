"""
Supabase client — script queue (httpx REST, compat with sb_publishable_ key)
Table: video_scripts (สร้างจาก supabase_schema.sql)
"""

import os
import httpx
from datetime import datetime


def _url() -> str:
    return os.environ.get("SUPABASE_URL", "").rstrip("/")


def _headers() -> dict:
    key = os.environ.get("SUPABASE_KEY", "")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _get(path: str, params: dict = None) -> dict:
    r = httpx.get(f"{_url()}/rest/v1/{path}", headers=_headers(), params=params, timeout=15)
    r.raise_for_status()
    return r


def _patch(path: str, data: dict) -> None:
    r = httpx.patch(f"{_url()}/rest/v1/{path}", headers=_headers(), json=data, timeout=15)
    r.raise_for_status()


def _post(path: str, data) -> dict:
    r = httpx.post(f"{_url()}/rest/v1/{path}", headers={**_headers(), "Prefer": "return=representation"}, json=data, timeout=15)
    r.raise_for_status()
    return r.json()


def fetch_next_script() -> dict | None:
    """ดึง script ที่ status='pending' มา 1 ตัว (เก่าสุดก่อน)"""
    r = _get("video_scripts", {
        "select": "*",
        "status": "eq.pending",
        "order": "created_at.asc",
        "limit": 1,
    })
    data = r.json()
    return data[0] if data else None


def mark_processing(script_id: int):
    _patch(f"video_scripts?id=eq.{script_id}", {
        "status": "processing",
        "started_at": datetime.utcnow().isoformat(),
    })


def mark_done(script_id: int, publish_id: str, video_path: str, cost_usd: float):
    _patch(f"video_scripts?id=eq.{script_id}", {
        "status": "done",
        "publish_id": publish_id,
        "video_path": video_path,
        "cost_usd": cost_usd,
        "completed_at": datetime.utcnow().isoformat(),
    })


def mark_failed(script_id: int, error: str):
    _patch(f"video_scripts?id=eq.{script_id}", {
        "status": "failed",
        "error": error[:500],
        "completed_at": datetime.utcnow().isoformat(),
    })


def insert_scripts(scripts: list[dict]) -> int:
    """Insert script ใหม่หลายตัว (จาก script_gen.py)"""
    rows = [
        {
            "title": s["title"],
            "scene1_prompt": s["scene1_prompt"],
            "scene2_prompt": s["scene2_prompt"],
            "category": s.get("category", ""),
            "status": "pending",
        }
        for s in scripts
    ]
    resp = _post("video_scripts", rows)
    return len(resp) if isinstance(resp, list) else 1


def count_pending() -> int:
    r = httpx.get(
        f"{_url()}/rest/v1/video_scripts",
        headers={**_headers(), "Prefer": "count=exact"},
        params={"select": "id", "status": "eq.pending"},
        timeout=15,
    )
    r.raise_for_status()
    # Content-Range: 0-N/TOTAL or */TOTAL
    content_range = r.headers.get("content-range", "0/0")
    try:
        return int(content_range.split("/")[-1])
    except Exception:
        data = r.json()
        return len(data) if isinstance(data, list) else 0
