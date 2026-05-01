"""
Zona cs-health-analyst — Sub-agente de análisis de salud.
Calcula scores, detecta churn y genera alertas para ~130 cuentas.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from virtual_office.zones._base.zone import Zone, TaskResult
from virtual_office.integrations import pipedrive, supabase as db, emblue


class HealthAnalystZone(Zone):
    name = "cs-health-analyst"
    # Escaneos masivos usan haiku (costo), análisis individual usa sonnet
    model_env = "CLAUDE_MODEL_QUALITY"

    # ── Public API ────────────────────────────────────────────────────────────

    def execute(self, task: str, deal_id: Optional[int] = None,
                extra_context: dict = None) -> TaskResult:

        context = self.load_context(deal_id) if deal_id else {}
        context.update(extra_context or {})
        context_block = self.build_context_block(context) if deal_id else ""
        user_message = f"{context_block}\n\n## Tarea\n{task}".strip()

        output = self._call_claude(user_message)

        return TaskResult(
            zone=self.name,
            task_type="analysis" if deal_id else "scan",
            success=True,
            output=output,
            deal_id=deal_id,
        )

    def run_daily_scan(self) -> TaskResult:
        """
        Escaneo diario: lee v_churn_radar, genera resumen ejecutivo.
        Usa haiku para volumen.
        """
        import anthropic as _anthropic

        accounts = db.select("v_churn_radar", order="score.asc", limit=50)

        if not accounts:
            return TaskResult(
                zone=self.name,
                task_type="scan",
                success=True,
                output="Sin cuentas en riesgo detectadas en la base de datos.\n"
                       "Verificar que account_health tenga datos cargados.",
            )

        accounts_text = "\n".join(
            f"- Deal #{a['pipedrive_deal_id']}"
            f" | Score {a['score']}/100"
            f" | {a['risk_level'].upper()}"
            f" | NRR {a.get('nrr') or '—'}%"
            f" | Engagement {a.get('engagement_rate') or '—'}%"
            f" | Sin login: {a.get('days_since_login') or '—'}d"
            for a in accounts
        )

        # Haiku para escaneo masivo — más barato
        client = _anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        haiku = os.environ.get("CLAUDE_MODEL_VOLUME", "claude-haiku-4-5-20251001")

        prompt = (
            f"Analiza estas {len(accounts)} cuentas en riesgo y genera el "
            f"resumen ejecutivo en el formato de escaneo masivo definido en tu rol.\n\n"
            f"{accounts_text}"
        )

        response = client.messages.create(
            model=haiku,
            max_tokens=800,
            system=self.get_system_prompt(),
            messages=[{"role": "user", "content": prompt}],
        )
        output = response.content[0].text

        return TaskResult(
            zone=self.name,
            task_type="scan",
            success=True,
            output=output,
        )

    def calculate_and_save_score(
        self,
        deal_id: int,
        engagement_rate: Optional[float] = None,
        last_login: Optional[str] = None,
        nrr: Optional[float] = None,
    ) -> dict:
        """
        Calcula el health score de una cuenta y lo persiste en Supabase.
        Retorna el dict con score, risk_level y señales.
        """
        try:
            deal = pipedrive.get_deal(deal_id)
        except Exception:
            deal = {}

        result = _compute_score(deal, engagement_rate, last_login, nrr)

        db.insert("account_health", {
            "pipedrive_deal_id": deal_id,
            "score":             result["score"],
            "risk_level":        result["risk_level"],
            "engagement_rate":   engagement_rate,
            "last_login":        last_login,
            "nrr":               nrr,
            "notes":             str(result["signals"]),
        })

        return result

    def batch_score_from_pipedrive(self, stage_id: int) -> list[dict]:
        """
        Calcula y guarda health scores para todos los deals de un stage.
        Usa mock de emBlue si la API no está configurada.
        """
        deals = pipedrive.list_deals_by_stage(stage_id)
        results = []

        for deal in deals:
            deal_id = deal["id"]
            metrics = emblue.get_mock_metrics(str(deal_id))  # → get_account_metrics en prod

            scored = self.calculate_and_save_score(
                deal_id=deal_id,
                engagement_rate=metrics.get("engagement_rate"),
                nrr=None,
            )
            results.append({"deal_id": deal_id, **scored})

        return results

    def prepare_qbr(self, deal_id: int, qbr_date: str = "") -> TaskResult:
        """Genera materiales de preparación para un QBR."""
        task = (
            f"Prepara los materiales para el QBR del deal #{deal_id}"
            + (f" programado para el {qbr_date}" if qbr_date else "")
            + ". Incluye: resumen de métricas, logros del trimestre, "
              "áreas de mejora, agenda propuesta y preguntas que el cliente podría hacer."
        )
        return self.execute(task, deal_id=deal_id)


# ── Score engine ──────────────────────────────────────────────────────────────

def _compute_score(
    deal: dict,
    engagement_rate: Optional[float],
    last_login: Optional[str],
    nrr: Optional[float],
) -> dict:
    score = 100
    signals = []

    # Actividad en Pipedrive
    last_act = deal.get("last_activity_date")
    if last_act:
        days = (datetime.now(timezone.utc) -
                datetime.fromisoformat(last_act.replace("Z", "+00:00"))).days
        if days > 30:
            score -= 30; signals.append(f"inactivo_pipedrive_{days}d")
        elif days > 14:
            score -= 12; signals.append(f"baja_actividad_{days}d")
    else:
        score -= 20; signals.append("sin_actividad_pipedrive")

    # Engagement
    if engagement_rate is not None:
        if engagement_rate < 5:
            score -= 25; signals.append(f"engagement_critico_{engagement_rate}%")
        elif engagement_rate < 10:
            score -= 15; signals.append(f"engagement_bajo_{engagement_rate}%")
        elif engagement_rate < 20:
            score -= 5

    # NRR
    if nrr is not None:
        if nrr < 85:
            score -= 20; signals.append(f"nrr_critico_{nrr}%")
        elif nrr < 95:
            score -= 8; signals.append(f"nrr_bajo_{nrr}%")

    # Último login
    if last_login:
        days_l = (datetime.now(timezone.utc) -
                  datetime.fromisoformat(last_login.replace("Z", "+00:00"))).days
        if days_l > 30:
            score -= 20; signals.append(f"sin_login_{days_l}d")
        elif days_l > 14:
            score -= 8

    score = max(0, min(100, score))
    risk = ("critical" if score < 30 else
            "high"     if score < 50 else
            "medium"   if score < 70 else "low")

    return {"score": score, "risk_level": risk, "signals": signals}
