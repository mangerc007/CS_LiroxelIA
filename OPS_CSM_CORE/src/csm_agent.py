"""
OPS_CSM_CORE — Agente CSM emBlue
Orquesta análisis de salud de cuentas, detección de churn y preparación de QBRs.
"""

import os
import json
from datetime import datetime, timedelta, timezone
from typing import Optional
import anthropic
import httpx

# ── Config ────────────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY    = os.environ["ANTHROPIC_API_KEY"]
CLAUDE_MODEL         = os.environ.get("CLAUDE_MODEL_QUALITY", "claude-sonnet-4-6")
SUPABASE_URL         = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
PIPEDRIVE_TOKEN      = os.environ["PIPEDRIVE_API_TOKEN"]
PIPEDRIVE_DOMAIN     = os.environ.get("PIPEDRIVE_DOMAIN", "emblue2.pipedrive.com")

SYSTEM_PROMPT_PATH = os.path.join(
    os.path.dirname(__file__), "../prompts/csm_agent_system_prompt_v1.md"
)

# ── Supabase helpers ──────────────────────────────────────────────────────────

def _sb_headers() -> dict:
    return {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }


def fetch_churn_radar() -> list[dict]:
    """Retorna cuentas en riesgo alto/crítico desde la vista v_churn_radar."""
    res = httpx.get(
        f"{SUPABASE_URL}/rest/v1/v_churn_radar?order=score.asc",
        headers=_sb_headers(),
        timeout=10,
    )
    res.raise_for_status()
    return res.json()


def fetch_account_health(deal_id: int) -> Optional[dict]:
    """Retorna el último health score de una cuenta."""
    res = httpx.get(
        f"{SUPABASE_URL}/rest/v1/v_latest_health?pipedrive_deal_id=eq.{deal_id}",
        headers=_sb_headers(),
        timeout=10,
    )
    res.raise_for_status()
    rows = res.json()
    return rows[0] if rows else None


def save_health_score(deal_id: int, score: int, risk_level: str,
                      engagement_rate: Optional[float] = None,
                      last_login: Optional[str] = None,
                      nrr: Optional[float] = None,
                      notes: str = "") -> None:
    payload = {
        "pipedrive_deal_id": deal_id,
        "score": score,
        "risk_level": risk_level,
        "engagement_rate": engagement_rate,
        "last_login": last_login,
        "nrr": nrr,
        "notes": notes,
    }
    res = httpx.post(
        f"{SUPABASE_URL}/rest/v1/account_health",
        headers={**_sb_headers(), "Prefer": "return=minimal"},
        json=payload,
        timeout=10,
    )
    res.raise_for_status()


def save_interaction(deal_id: int, interaction_type: str, summary: str,
                     outcome: str = "", next_action: str = "",
                     next_date: Optional[str] = None) -> None:
    payload = {
        "deal_id": deal_id,
        "type": interaction_type,
        "summary": summary,
        "outcome": outcome,
        "next_action": next_action,
        "next_date": next_date,
    }
    res = httpx.post(
        f"{SUPABASE_URL}/rest/v1/csm_interactions",
        headers={**_sb_headers(), "Prefer": "return=minimal"},
        json=payload,
        timeout=10,
    )
    res.raise_for_status()


# ── Pipedrive helpers ─────────────────────────────────────────────────────────

def fetch_deal(deal_id: int) -> dict:
    res = httpx.get(
        f"https://{PIPEDRIVE_DOMAIN}/api/v1/deals/{deal_id}",
        params={"api_token": PIPEDRIVE_TOKEN},
        timeout=10,
    )
    res.raise_for_status()
    return res.json().get("data", {})


def create_pipedrive_activity(deal_id: int, subject: str, note: str,
                               due_date: Optional[str] = None) -> dict:
    payload = {
        "subject": subject,
        "note": note,
        "deal_id": deal_id,
        "type": "call",
        "due_date": due_date or (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d"),
        "due_time": "09:00",
    }
    res = httpx.post(
        f"https://{PIPEDRIVE_DOMAIN}/api/v1/activities",
        params={"api_token": PIPEDRIVE_TOKEN},
        json=payload,
        timeout=10,
    )
    res.raise_for_status()
    return res.json().get("data", {})


# ── Score calculator ──────────────────────────────────────────────────────────

def calculate_health_score(deal: dict, engagement_rate: float = None,
                            last_login_date: str = None, nrr: float = None) -> dict:
    """
    Calcula health score (0-100) desde señales de Pipedrive + métricas emBlue.
    Retorna dict con score, risk_level y señales detectadas.
    """
    score = 100
    signals = []

    # Actividad en el deal
    if deal.get("last_activity_date"):
        days = (datetime.now(timezone.utc) -
                datetime.fromisoformat(deal["last_activity_date"].replace("Z", "+00:00"))
                ).days
        if days > 30:
            score -= 30
            signals.append(f"sin_actividad_{days}d")
        elif days > 14:
            score -= 15
            signals.append(f"baja_actividad_{days}d")
    else:
        score -= 25
        signals.append("sin_actividad_registrada")

    # Engagement rate (desde plataforma emBlue)
    if engagement_rate is not None:
        if engagement_rate < 5:
            score -= 25
            signals.append(f"engagement_critico_{engagement_rate}%")
        elif engagement_rate < 10:
            score -= 15
            signals.append(f"engagement_bajo_{engagement_rate}%")
        elif engagement_rate < 20:
            score -= 5

    # NRR
    if nrr is not None:
        if nrr < 85:
            score -= 20
            signals.append(f"nrr_critico_{nrr}%")
        elif nrr < 95:
            score -= 10
            signals.append(f"nrr_bajo_{nrr}%")

    # Último login en plataforma
    if last_login_date:
        days_login = (datetime.now(timezone.utc) -
                      datetime.fromisoformat(last_login_date.replace("Z", "+00:00"))
                      ).days
        if days_login > 30:
            score -= 20
            signals.append(f"sin_login_{days_login}d")

    score = max(0, min(100, score))

    risk_level = (
        "critical" if score < 30 else
        "high"     if score < 50 else
        "medium"   if score < 70 else
        "low"
    )

    return {"score": score, "risk_level": risk_level, "signals": signals}


# ── Claude agent ──────────────────────────────────────────────────────────────

def load_system_prompt() -> str:
    try:
        with open(SYSTEM_PROMPT_PATH) as f:
            return f.read()
    except FileNotFoundError:
        return "Eres el Agente CSM de emBlue LATAM. Analiza cuentas y recomienda acciones de retención."


def analyze_account(deal_id: int, user_message: str = "") -> str:
    """
    Usa Claude para analizar una cuenta y recomendar acciones.
    Inyecta contexto real desde Pipedrive + Supabase.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    deal = fetch_deal(deal_id)
    health = fetch_account_health(deal_id)

    context = f"""
## Datos de la cuenta
- Deal ID: {deal_id}
- Nombre: {deal.get('title', '—')}
- Valor: {deal.get('value', '—')} {deal.get('currency', '')}
- Etapa: {deal.get('stage_id', '—')}
- Owner: {deal.get('owner_name', '—')}
- Última actividad: {deal.get('last_activity_date', '—')}

## Health Score (Supabase)
{json.dumps(health, indent=2, ensure_ascii=False) if health else 'Sin datos de health score aún.'}

## Pregunta del CSM
{user_message or 'Analiza esta cuenta y recomienda la próxima acción.'}
"""

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=load_system_prompt(),
        messages=[{"role": "user", "content": context}],
    )

    return response.content[0].text


def run_daily_churn_scan() -> dict:
    """
    Escanea todas las cuentas en riesgo y genera un resumen ejecutivo.
    Usa claude-haiku para volumen (más barato).
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    churn_accounts = fetch_churn_radar()

    if not churn_accounts:
        return {"summary": "Sin cuentas en riesgo detectadas.", "accounts": []}

    accounts_text = "\n".join(
        f"- {a.get('account_name') or f'Deal #{a[\"pipedrive_deal_id\"]}'}: "
        f"score {a['score']}, riesgo {a['risk_level']}, "
        f"NRR {a.get('nrr') or '—'}%, "
        f"engagement {a.get('engagement_rate') or '—'}%"
        for a in churn_accounts
    )

    prompt = f"""Analiza estas cuentas en riesgo de churn y genera:
1. Resumen ejecutivo (3 líneas)
2. Top 3 cuentas que requieren acción HOY
3. Patrón común entre las cuentas críticas (si existe)

Cuentas:
{accounts_text}"""

    response = client.messages.create(
        model=os.environ.get("CLAUDE_MODEL_VOLUME", "claude-haiku-4-5-20251001"),
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    return {
        "summary": response.content[0].text,
        "accounts": churn_accounts,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python csm_agent.py [scan | analyze <deal_id> [mensaje]]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "scan":
        result = run_daily_churn_scan()
        print("\n=== CHURN SCAN ===")
        print(result["summary"])
        print(f"\n{len(result['accounts'])} cuentas en radar.")

    elif command == "analyze" and len(sys.argv) >= 3:
        deal_id = int(sys.argv[2])
        msg = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
        analysis = analyze_account(deal_id, msg)
        print(f"\n=== ANÁLISIS DEAL #{deal_id} ===")
        print(analysis)

    else:
        print("Comando no reconocido.")
        sys.exit(1)
