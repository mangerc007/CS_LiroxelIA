"""
Wrapper de la API de Pipedrive.
Solo llamadas HTTP — sin lógica de negocio.
"""

import os
from typing import Optional
import httpx

_BASE = f"https://{os.environ.get('PIPEDRIVE_DOMAIN', 'emblue2.pipedrive.com')}/api/v1"
_TOKEN = os.environ.get("PIPEDRIVE_API_TOKEN", "")
_TIMEOUT = 12


def _get(path: str, params: dict = None) -> dict:
    res = httpx.get(
        f"{_BASE}{path}",
        params={"api_token": _TOKEN, **(params or {})},
        timeout=_TIMEOUT,
    )
    res.raise_for_status()
    return res.json()


def _post(path: str, payload: dict) -> dict:
    res = httpx.post(
        f"{_BASE}{path}",
        params={"api_token": _TOKEN},
        json=payload,
        timeout=_TIMEOUT,
    )
    res.raise_for_status()
    return res.json()


def _put(path: str, payload: dict) -> dict:
    res = httpx.put(
        f"{_BASE}{path}",
        params={"api_token": _TOKEN},
        json=payload,
        timeout=_TIMEOUT,
    )
    res.raise_for_status()
    return res.json()


# ── Deals ─────────────────────────────────────────────────────────────────────

def get_deal(deal_id: int) -> dict:
    return _get(f"/deals/{deal_id}").get("data", {})


def list_deals_by_stage(stage_id: int, limit: int = 100) -> list[dict]:
    data = _get("/deals", {"stage_id": stage_id, "status": "open", "limit": limit})
    return data.get("data") or []


def update_deal(deal_id: int, fields: dict) -> dict:
    return _put(f"/deals/{deal_id}", fields).get("data", {})


def get_deal_activities(deal_id: int, limit: int = 20) -> list[dict]:
    data = _get("/activities", {"deal_id": deal_id, "limit": limit})
    return data.get("data") or []


# ── Activities ────────────────────────────────────────────────────────────────

def create_activity(deal_id: int, subject: str, note: str = "",
                    due_date: Optional[str] = None, due_time: str = "09:00",
                    activity_type: str = "call") -> dict:
    return _post("/activities", {
        "subject": subject,
        "note": note,
        "deal_id": deal_id,
        "type": activity_type,
        "due_date": due_date,
        "due_time": due_time,
    }).get("data", {})


def mark_activity_done(activity_id: int) -> dict:
    return _put(f"/activities/{activity_id}", {"done": 1}).get("data", {})


# ── Notes ─────────────────────────────────────────────────────────────────────

def add_note(deal_id: int, content: str) -> dict:
    return _post("/notes", {"deal_id": deal_id, "content": content}).get("data", {})


# ── Persons / Orgs ────────────────────────────────────────────────────────────

def get_person(person_id: int) -> dict:
    return _get(f"/persons/{person_id}").get("data", {})


def get_organization(org_id: int) -> dict:
    return _get(f"/organizations/{org_id}").get("data", {})


# ── Pipeline stages ───────────────────────────────────────────────────────────

def list_stages(pipeline_id: Optional[int] = None) -> list[dict]:
    params = {"pipeline_id": pipeline_id} if pipeline_id else {}
    return _get("/stages", params).get("data") or []
