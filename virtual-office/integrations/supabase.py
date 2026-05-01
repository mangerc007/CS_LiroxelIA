"""
Wrapper de la API REST de Supabase.
Solo llamadas HTTP — sin lógica de negocio.
"""

import os
from typing import Any, Optional
import httpx

_URL     = os.environ.get("SUPABASE_URL", "")
_SVC_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
_ANON    = os.environ.get("SUPABASE_ANON_KEY", "")
_TIMEOUT = 12


def _headers(use_service_key: bool = True) -> dict:
    key = _SVC_KEY if use_service_key else _ANON
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def select(table: str, filters: str = "", order: str = "",
           limit: Optional[int] = None) -> list[dict]:
    """
    Selecciona filas de una tabla o vista.
    filters: string de filtros PostgREST, ej. "risk_level=eq.critical"
    order:   ej. "score.asc"
    """
    url = f"{_URL}/rest/v1/{table}"
    params = {}
    if filters:
        for f in filters.split("&"):
            k, v = f.split("=", 1)
            params[k] = v
    if order:
        params["order"] = order
    if limit:
        params["limit"] = limit

    res = httpx.get(url, headers=_headers(), params=params, timeout=_TIMEOUT)
    res.raise_for_status()
    return res.json()


def insert(table: str, payload: dict | list[dict],
           return_repr: bool = False) -> Any:
    prefer = "return=representation" if return_repr else "return=minimal"
    res = httpx.post(
        f"{_URL}/rest/v1/{table}",
        headers={**_headers(), "Prefer": prefer},
        json=payload,
        timeout=_TIMEOUT,
    )
    res.raise_for_status()
    return res.json() if return_repr else None


def update(table: str, filters: str, payload: dict) -> None:
    params = {}
    for f in filters.split("&"):
        k, v = f.split("=", 1)
        params[k] = v
    res = httpx.patch(
        f"{_URL}/rest/v1/{table}",
        headers={**_headers(), "Prefer": "return=minimal"},
        params=params,
        json=payload,
        timeout=_TIMEOUT,
    )
    res.raise_for_status()


def upsert(table: str, payload: dict | list[dict],
           on_conflict: str = "id") -> None:
    res = httpx.post(
        f"{_URL}/rest/v1/{table}",
        headers={**_headers(), "Prefer": f"resolution=merge-duplicates,return=minimal"},
        params={"on_conflict": on_conflict},
        json=payload,
        timeout=_TIMEOUT,
    )
    res.raise_for_status()


def delete(table: str, filters: str) -> None:
    params = {}
    for f in filters.split("&"):
        k, v = f.split("=", 1)
        params[k] = v
    res = httpx.delete(
        f"{_URL}/rest/v1/{table}",
        headers=_headers(),
        params=params,
        timeout=_TIMEOUT,
    )
    res.raise_for_status()


def rpc(function_name: str, params: dict = None) -> Any:
    res = httpx.post(
        f"{_URL}/rest/v1/rpc/{function_name}",
        headers=_headers(),
        json=params or {},
        timeout=_TIMEOUT,
    )
    res.raise_for_status()
    return res.json()
