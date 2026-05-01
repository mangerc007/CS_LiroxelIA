"""
Wrapper de Gmail vía MCP google-gmail o API directa.
Usado para: leer hilos de clientes, detectar emails sin respuesta,
registrar comunicaciones en Supabase.
"""

import os
import base64
from datetime import datetime, timezone
from typing import Optional
import httpx

_GMAIL_MCP_URL = os.environ.get("GMAIL_MCP_URL", "")
_TIMEOUT = 15


# ── Via MCP (preferido cuando está activo) ────────────────────────────────────

def list_threads_from_client(email: str, max_results: int = 10) -> list[dict]:
    """
    Lista hilos recientes de un cliente específico.
    Requiere MCP gmail activo.
    """
    if not _GMAIL_MCP_URL:
        return _mock_threads(email)

    res = httpx.post(
        f"{_GMAIL_MCP_URL}/list_threads",
        json={"query": f"from:{email} OR to:{email}", "maxResults": max_results},
        timeout=_TIMEOUT,
    )
    res.raise_for_status()
    return res.json().get("threads") or []


def get_thread(thread_id: str) -> dict:
    if not _GMAIL_MCP_URL:
        return {}
    res = httpx.post(
        f"{_GMAIL_MCP_URL}/get_thread",
        json={"threadId": thread_id},
        timeout=_TIMEOUT,
    )
    res.raise_for_status()
    return res.json()


def send_email(to: str, subject: str, body_html: str,
               reply_to_thread: Optional[str] = None) -> dict:
    if not _GMAIL_MCP_URL:
        raise RuntimeError("GMAIL_MCP_URL no configurado — no se puede enviar email.")
    payload = {"to": to, "subject": subject, "bodyHtml": body_html}
    if reply_to_thread:
        payload["threadId"] = reply_to_thread
    res = httpx.post(
        f"{_GMAIL_MCP_URL}/send_message",
        json=payload,
        timeout=_TIMEOUT,
    )
    res.raise_for_status()
    return res.json()


def get_unanswered_threads(days: int = 7) -> list[dict]:
    """Hilos de clientes sin respuesta en los últimos N días."""
    if not _GMAIL_MCP_URL:
        return []
    query = f"is:inbox -is:replied newer_than:{days}d label:clientes"
    res = httpx.post(
        f"{_GMAIL_MCP_URL}/list_threads",
        json={"query": query, "maxResults": 50},
        timeout=_TIMEOUT,
    )
    res.raise_for_status()
    return res.json().get("threads") or []


# ── Stub para desarrollo ──────────────────────────────────────────────────────

def _mock_threads(email: str) -> list[dict]:
    return [
        {
            "id": "mock_thread_001",
            "subject": f"Re: Seguimiento renovación — {email}",
            "from": email,
            "date": "2026-04-20T14:30:00Z",
            "snippet": "Estamos evaluando las opciones, te escribo la próxima semana...",
            "answered": False,
            "mock": True,
        }
    ]
