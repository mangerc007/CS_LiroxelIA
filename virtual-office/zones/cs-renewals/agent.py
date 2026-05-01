"""
Zona cs-renewals — Sub-agente de Renegociación.
Gestiona las 16 cuentas en etapa Renegociación con máxima prioridad.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from virtual_office.zones._base.zone import Zone, TaskResult
from virtual_office.integrations import pipedrive, supabase as db, gmail


class RenewalsZone(Zone):
    name = "cs-renewals"
    max_tokens = 2000

    # ── Public API ────────────────────────────────────────────────────────────

    def execute(self, task: str, deal_id: Optional[int] = None,
                extra_context: dict = None) -> TaskResult:

        context = self.load_context(deal_id) if deal_id else {}
        context.update(extra_context or {})

        # Si hay deal_id, enriquecer con datos de Pipedrive
        if deal_id:
            context["pipedrive"] = self._fetch_pipedrive_context(deal_id)

        context_block = self.build_context_block(context) if deal_id else ""
        user_message = f"{context_block}\n\n## Tarea\n{task}".strip()

        output = self._call_claude(user_message)
        actions, next_steps = self._extract_actions(output)

        result = TaskResult(
            zone=self.name,
            task_type=self._classify_task(task),
            success=True,
            output=output,
            actions_taken=actions,
            next_steps=next_steps,
            deal_id=deal_id,
        )
        return result

    def run_renewals_review(self) -> TaskResult:
        """
        Revisión semanal de todas las cuentas en Renegociación.
        Carga health scores y genera plan de acción priorizado.
        """
        accounts = db.select("v_churn_radar", order="score.asc", limit=20)

        if not accounts:
            return TaskResult(
                zone=self.name,
                task_type="renewals_review",
                success=True,
                output="Sin cuentas en radar de churn actualmente.",
                next_steps=["Verificar que las migraciones SQL estén aplicadas."],
            )

        accounts_text = "\n".join(
            f"- Deal #{a['pipedrive_deal_id']}"
            f" | Score: {a['score']}/100"
            f" | NRR: {a.get('nrr') or '—'}%"
            f" | Engagement: {a.get('engagement_rate') or '—'}%"
            f" | Sin login: {a.get('days_since_login') or '—'}d"
            f" | Acción: {a.get('action_label', '')}"
            for a in accounts
        )

        task = (
            f"Tengo {len(accounts)} cuentas en riesgo. "
            f"Genera el plan de acción para la semana:\n\n{accounts_text}"
        )
        return self.execute(task)

    def prepare_negotiation_brief(self, deal_id: int) -> TaskResult:
        """Brief completo para una llamada de renegociación."""
        task = (
            f"Prepara un brief completo para la llamada de renegociación "
            f"del deal #{deal_id}. Incluye: diagnóstico de causa raíz probable, "
            f"argumentos de retención personalizados, script de apertura y "
            f"preguntas clave para la llamada."
        )
        return self.execute(task, deal_id=deal_id)

    def log_call_outcome(self, deal_id: int, outcome: str,
                          next_action: str, next_date: str) -> None:
        """Registra el resultado de una llamada de renegociación."""
        db.insert("csm_interactions", {
            "deal_id": deal_id,
            "type": "call",
            "summary": outcome[:500],
            "outcome": outcome[:200],
            "next_action": next_action,
            "next_date": next_date,
        })

        # Crear actividad de seguimiento en Pipedrive
        due = datetime.fromisoformat(next_date) if next_date else \
              datetime.now(timezone.utc) + timedelta(days=3)
        pipedrive.create_activity(
            deal_id=deal_id,
            subject=f"Seguimiento renegociación — {due.strftime('%d/%m')}",
            note=next_action,
            due_date=due.strftime("%Y-%m-%d"),
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _fetch_pipedrive_context(self, deal_id: int) -> dict:
        try:
            deal = pipedrive.get_deal(deal_id)
            activities = pipedrive.get_deal_activities(deal_id, limit=5)
            return {
                "title": deal.get("title"),
                "value": deal.get("value"),
                "currency": deal.get("currency"),
                "stage": deal.get("stage_id"),
                "owner": deal.get("owner_name"),
                "last_activity": deal.get("last_activity_date"),
                "recent_activities": [
                    {"subject": a.get("subject"), "done": a.get("done"),
                     "date": a.get("due_date")}
                    for a in (activities or [])
                ],
            }
        except Exception as e:
            return {"error": str(e)}

    def build_context_block(self, context: dict) -> str:
        base = super().build_context_block(context)

        if context.get("pipedrive"):
            p = context["pipedrive"]
            if "error" not in p:
                extra = (
                    f"\n### Datos Pipedrive\n"
                    f"- Cuenta: {p.get('title') or '—'}\n"
                    f"- Valor: {p.get('value') or '—'} {p.get('currency') or ''}\n"
                    f"- Owner: {p.get('owner') or '—'}\n"
                    f"- Última actividad: {p.get('last_activity') or '—'}"
                )
                if p.get("recent_activities"):
                    extra += "\n- Actividades recientes:"
                    for a in p["recent_activities"]:
                        done = "✓" if a.get("done") else "○"
                        extra += f"\n  {done} [{a.get('date', '')}] {a.get('subject', '')}"
                base += extra

        return base

    def _classify_task(self, task: str) -> str:
        task_lower = task.lower()
        if "brief" in task_lower or "llamada" in task_lower:
            return "negotiation_brief"
        if "review" in task_lower or "revisión" in task_lower:
            return "renewals_review"
        if "propuesta" in task_lower:
            return "proposal"
        return "churn_risk"

    def _extract_actions(self, output: str) -> tuple[list[str], list[str]]:
        """Extrae acciones tomadas y próximos pasos del output de Claude."""
        actions, next_steps = [], []
        lines = output.split("\n")
        in_next = False

        for line in lines:
            stripped = line.strip()
            if "próximo" in stripped.lower() or "next step" in stripped.lower():
                in_next = True
            if stripped.startswith(("→", "- →", "* →")):
                next_steps.append(stripped.lstrip("→ -*").strip())
            elif in_next and stripped.startswith(("-", "*", "•")):
                next_steps.append(stripped.lstrip("-*• ").strip())

        return actions, next_steps[:3]
