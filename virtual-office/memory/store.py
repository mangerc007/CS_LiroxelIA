"""
Memory store — abstracción de contexto persistente.

Dos niveles:
  1. Supabase (estructurado) → health scores, interacciones, métricas
  2. Archivos .md (lenguaje natural) → notas por cuenta y playbooks globales

Las zonas solo usan este módulo, nunca llaman a Supabase o archivos directamente.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from virtual_office.integrations import supabase as db

_ACCOUNTS_DIR = Path(__file__).parent / "accounts"
_GLOBAL_DIR   = Path(__file__).parent / "global"


# ── Account memory ────────────────────────────────────────────────────────────

def get_account_context(deal_id: int) -> dict:
    """
    Retorna todo el contexto disponible de una cuenta:
    - Último health score
    - Últimas 5 interacciones
    - Notas en lenguaje natural (archivo .md)
    """
    return {
        "deal_id":            deal_id,
        "health":             get_latest_health(deal_id),
        "interactions":       get_interactions(deal_id, limit=5),
        "notes":              get_account_notes(deal_id),
    }


def get_latest_health(deal_id: int) -> Optional[dict]:
    rows = db.select("v_latest_health", f"pipedrive_deal_id=eq.{deal_id}")
    return rows[0] if rows else None


def get_interactions(deal_id: int, limit: int = 10) -> list[dict]:
    return db.select(
        "csm_interactions",
        f"deal_id=eq.{deal_id}",
        order="created_at.desc",
        limit=limit,
    )


def get_account_notes(deal_id: int) -> str:
    path = _ACCOUNTS_DIR / f"{deal_id}.md"
    return path.read_text() if path.exists() else ""


def save_account_notes(deal_id: int, notes: str) -> None:
    _ACCOUNTS_DIR.mkdir(exist_ok=True)
    (_ACCOUNTS_DIR / f"{deal_id}.md").write_text(notes)


def append_account_note(deal_id: int, note: str) -> None:
    path = _ACCOUNTS_DIR / f"{deal_id}.md"
    _ACCOUNTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    entry = f"\n## {ts}\n{note.strip()}\n"
    with path.open("a") as f:
        f.write(entry)


def save_health_score(deal_id: int, score: int, risk_level: str,
                       engagement_rate: Optional[float] = None,
                       last_login: Optional[str] = None,
                       nrr: Optional[float] = None,
                       notes: str = "") -> None:
    db.insert("account_health", {
        "pipedrive_deal_id": deal_id,
        "score":             score,
        "risk_level":        risk_level,
        "engagement_rate":   engagement_rate,
        "last_login":        last_login,
        "nrr":               nrr,
        "notes":             notes,
    })


def save_interaction(deal_id: int, interaction_type: str, summary: str,
                      outcome: str = "", next_action: str = "",
                      next_date: Optional[str] = None) -> None:
    db.insert("csm_interactions", {
        "deal_id":     deal_id,
        "type":        interaction_type,
        "summary":     summary[:500],
        "outcome":     outcome[:200],
        "next_action": next_action,
        "next_date":   next_date,
    })


# ── Global knowledge ──────────────────────────────────────────────────────────

def get_playbooks() -> str:
    path = _GLOBAL_DIR / "playbooks.md"
    return path.read_text() if path.exists() else ""


def get_churn_patterns() -> str:
    path = _GLOBAL_DIR / "churn-patterns.md"
    return path.read_text() if path.exists() else ""


def update_churn_patterns(new_pattern: str) -> None:
    """Agrega un patrón detectado por IA al archivo global."""
    path = _GLOBAL_DIR / "churn-patterns.md"
    _GLOBAL_DIR.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entry = f"\n## Patrón detectado — {ts}\n{new_pattern.strip()}\n"
    with path.open("a") as f:
        f.write(entry)


# ── Churn radar ───────────────────────────────────────────────────────────────

def get_churn_radar(limit: int = 30) -> list[dict]:
    return db.select("v_churn_radar", order="score.asc", limit=limit)


def get_renewal_summary() -> list[dict]:
    return db.select("v_renewal_summary")
