"""
Wrapper de la API de emBlue.
Métricas de plataforma: engagement, últimos envíos, logins.

⚠️ Las credenciales de emBlue son por cuenta — se pasan en cada llamada.
Configurar EMBLUE_API_BASE y EMBLUE_API_KEY en .env cuando la API esté disponible.
"""

import os
from typing import Optional
import httpx

_BASE    = os.environ.get("EMBLUE_API_BASE", "https://api.embluemail.com/v1")
_API_KEY = os.environ.get("EMBLUE_API_KEY", "")
_TIMEOUT = 15


def _headers(account_token: Optional[str] = None) -> dict:
    token = account_token or _API_KEY
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


# ── Métricas de cuenta ────────────────────────────────────────────────────────

def get_account_metrics(account_id: str,
                         account_token: Optional[str] = None) -> dict:
    """
    Retorna métricas agregadas de la cuenta:
    opens, clicks, engagement_rate, last_send, active_contacts.
    """
    res = httpx.get(
        f"{_BASE}/accounts/{account_id}/metrics",
        headers=_headers(account_token),
        timeout=_TIMEOUT,
    )
    res.raise_for_status()
    return res.json()


def get_last_login(account_id: str,
                    account_token: Optional[str] = None) -> Optional[str]:
    """Retorna ISO string del último login en la plataforma."""
    res = httpx.get(
        f"{_BASE}/accounts/{account_id}/last-login",
        headers=_headers(account_token),
        timeout=_TIMEOUT,
    )
    res.raise_for_status()
    data = res.json()
    return data.get("last_login")


def get_campaigns(account_id: str, limit: int = 10,
                   account_token: Optional[str] = None) -> list[dict]:
    """Últimas campañas enviadas por la cuenta."""
    res = httpx.get(
        f"{_BASE}/accounts/{account_id}/campaigns",
        headers=_headers(account_token),
        params={"limit": limit, "order": "sent_at.desc"},
        timeout=_TIMEOUT,
    )
    res.raise_for_status()
    return res.json().get("data") or []


def get_automation_usage(account_id: str,
                          account_token: Optional[str] = None) -> dict:
    """Uso de automatizaciones: activas, disparadas, conversiones."""
    res = httpx.get(
        f"{_BASE}/accounts/{account_id}/automations/usage",
        headers=_headers(account_token),
        timeout=_TIMEOUT,
    )
    res.raise_for_status()
    return res.json()


# ── Stub para desarrollo sin API real ─────────────────────────────────────────

def get_mock_metrics(account_id: str) -> dict:
    """
    Datos simulados para desarrollo/testing sin acceso a API emBlue.
    Reemplazar con get_account_metrics() en producción.
    """
    import random
    random.seed(int(account_id) if account_id.isdigit() else hash(account_id))
    return {
        "account_id": account_id,
        "engagement_rate": round(random.uniform(2, 45), 2),
        "open_rate":       round(random.uniform(5, 35), 2),
        "click_rate":      round(random.uniform(1, 12), 2),
        "last_send":       "2026-04-15T10:30:00Z",
        "active_contacts": random.randint(500, 50000),
        "automations_active": random.randint(0, 8),
        "mock": True,
    }
