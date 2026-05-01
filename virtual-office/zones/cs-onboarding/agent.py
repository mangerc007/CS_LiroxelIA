"""
Zona cs-onboarding — Sub-agente de Onboarding.
Convierte contratos nuevos en clientes activados antes del día 30.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from virtual_office.zones._base.zone import Zone, TaskResult
from virtual_office.integrations import pipedrive, supabase as db
from virtual_office.memory import store


class OnboardingZone(Zone):
    name = "cs-onboarding"
    max_tokens = 1800

    # Criterios de activación
    FIRST_CAMPAIGN_DEADLINE_DAYS = 14
    FIRST_AUTOMATION_DEADLINE_DAYS = 21
    MIN_LOGINS_FIRST_MONTH = 3

    def execute(self, task: str, deal_id: Optional[int] = None,
                extra_context: dict = None) -> TaskResult:
        context = self.load_context(deal_id) if deal_id else {}
        context.update(extra_context or {})

        if deal_id:
            context["onboarding_status"] = self._get_onboarding_status(deal_id)
            context["days_in_platform"] = self._days_since_kickoff(deal_id)

        context_block = self._build_onboarding_context(context) if deal_id else ""
        user_message = f"{context_block}\n\n## Tarea\n{task}".strip()

        output = self._call_claude(user_message)
        _, next_steps = self._extract_actions(output)

        result = TaskResult(
            zone=self.name,
            task_type=self._classify_task(task),
            success=True,
            output=output,
            next_steps=next_steps,
            deal_id=deal_id,
        )
        return result

    # ── Specific operations ────────────────────────────────────────────────────

    def prepare_business_kickoff(self, deal_id: int) -> TaskResult:
        """
        Genera la agenda y materiales para el Business Kickoff.
        Prioridad crítica — la etapa estaba vacía.
        """
        task = (
            f"Prepara todos los materiales para el Business Kickoff del deal #{deal_id}. "
            "Incluye: agenda detallada, KPIs a acordar con el cliente, preguntas clave "
            "para descubrir sus objetivos, y los próximos pasos con fechas exactas."
        )
        result = self.execute(task, deal_id=deal_id)

        # Crear actividad en Pipedrive automáticamente
        if deal_id:
            try:
                due = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
                pipedrive.create_activity(
                    deal_id=deal_id,
                    subject="Business Kickoff — preparar agenda",
                    note=result.output[:300],
                    due_date=due,
                    activity_type="task",
                )
                result.actions_taken.append("Actividad creada en Pipedrive")
            except Exception as e:
                result.actions_taken.append(f"Pipedrive: {e}")

        return result

    def diagnose_stuck_onboarding(self, deal_id: int) -> TaskResult:
        """Diagnostica por qué un onboarding está estancado y propone intervención."""
        status = self._get_onboarding_status(deal_id)
        days = self._days_since_kickoff(deal_id)

        blockers = []
        if not status.get("first_campaign_sent") and days > self.FIRST_CAMPAIGN_DEADLINE_DAYS:
            blockers.append(
                f"Sin primera campaña (llevan {days}d, límite era {self.FIRST_CAMPAIGN_DEADLINE_DAYS}d)"
            )
        if not status.get("first_automation_active") and days > self.FIRST_AUTOMATION_DEADLINE_DAYS:
            blockers.append(
                f"Sin automatización activa (llevan {days}d, límite era {self.FIRST_AUTOMATION_DEADLINE_DAYS}d)"
            )
        if status.get("logins_this_month", 0) < self.MIN_LOGINS_FIRST_MONTH:
            blockers.append(
                f"Solo {status.get('logins_this_month', 0)} logins este mes (mínimo {self.MIN_LOGINS_FIRST_MONTH})"
            )

        blockers_text = "\n".join(f"- {b}" for b in blockers) if blockers else "Sin bloqueos detectados"
        task = (
            f"Diagnostica el onboarding estancado del deal #{deal_id}.\n"
            f"Días en plataforma: {days}\n"
            f"Bloqueos detectados:\n{blockers_text}\n\n"
            "Identifica la causa raíz y propone la intervención más efectiva."
        )
        return self.execute(task, deal_id=deal_id)

    def check_activation_progress(self, deal_id: int) -> dict:
        """
        Retorna el estado de activación de una cuenta.
        Usado por n8n para decidir si disparar alertas.
        """
        status = self._get_onboarding_status(deal_id)
        days = self._days_since_kickoff(deal_id)

        checks = {
            "first_campaign": {
                "done": status.get("first_campaign_sent", False),
                "overdue": days > self.FIRST_CAMPAIGN_DEADLINE_DAYS and not status.get("first_campaign_sent"),
                "deadline_days": self.FIRST_CAMPAIGN_DEADLINE_DAYS,
            },
            "first_automation": {
                "done": status.get("first_automation_active", False),
                "overdue": days > self.FIRST_AUTOMATION_DEADLINE_DAYS and not status.get("first_automation_active"),
                "deadline_days": self.FIRST_AUTOMATION_DEADLINE_DAYS,
            },
            "login_frequency": {
                "done": status.get("logins_this_month", 0) >= self.MIN_LOGINS_FIRST_MONTH,
                "count": status.get("logins_this_month", 0),
                "required": self.MIN_LOGINS_FIRST_MONTH,
            },
        }

        activated = all(c["done"] for c in checks.values())
        return {
            "deal_id": deal_id,
            "days_in_platform": days,
            "activated": activated,
            "checks": checks,
            "risk": "high" if any(c.get("overdue") for c in checks.values()) else "ok",
        }

    def run_weekly_onboarding_scan(self) -> TaskResult:
        """Revisa todas las cuentas en onboarding y genera alertas."""
        # Cuentas en etapas onboarding de Supabase (health scores recientes)
        at_risk = db.select(
            "csm_interactions",
            "type=eq.churn_risk",
            order="created_at.desc",
            limit=20,
        )

        task = (
            "Revisa el estado de todas las cuentas en onboarding. "
            "Identifica cuáles están en riesgo de no activarse antes del día 30 "
            "y genera el plan de intervención priorizado para esta semana."
        )
        return self.execute(task, extra_context={"at_risk_interactions": at_risk})

    # ── Private helpers ────────────────────────────────────────────────────────

    def _get_onboarding_status(self, deal_id: int) -> dict:
        """
        Lee el estado de activación desde Supabase.
        En producción esto se enriquece con métricas reales de emBlue.
        """
        health = store.get_latest_health(deal_id)
        interactions = store.get_interactions(deal_id, limit=10)

        first_campaign = any(
            i.get("type") == "note" and "primera campaña" in (i.get("summary") or "").lower()
            for i in interactions
        )
        first_automation = any(
            "automatización" in (i.get("summary") or "").lower()
            for i in interactions
        )

        return {
            "first_campaign_sent": first_campaign,
            "first_automation_active": first_automation,
            "logins_this_month": 0,  # → poblar desde emblue.get_account_metrics()
            "health_score": health.get("score") if health else None,
        }

    def _days_since_kickoff(self, deal_id: int) -> int:
        """Días desde la primera interacción registrada (proxy del kickoff)."""
        interactions = store.get_interactions(deal_id, limit=50)
        if not interactions:
            return 0
        oldest = min(interactions, key=lambda i: i.get("created_at", ""))
        try:
            dt = datetime.fromisoformat(oldest["created_at"].replace("Z", "+00:00"))
            return (datetime.now(timezone.utc) - dt).days
        except Exception:
            return 0

    def _build_onboarding_context(self, context: dict) -> str:
        base = self.build_context_block(context)

        if context.get("onboarding_status"):
            s = context["onboarding_status"]
            days = context.get("days_in_platform", "—")
            base += (
                f"\n### Estado de activación (día {days})\n"
                f"- Primera campaña enviada: {'✅' if s.get('first_campaign_sent') else '❌'}\n"
                f"- Primera automatización activa: {'✅' if s.get('first_automation_active') else '❌'}\n"
                f"- Logins este mes: {s.get('logins_this_month', 0)}/{self.MIN_LOGINS_FIRST_MONTH}\n"
            )
        return base

    def _classify_task(self, task: str) -> str:
        t = task.lower()
        if "kickoff" in t:
            return "kickoff_prep"
        if "diagnos" in t or "estancad" in t:
            return "stuck_onboarding"
        if "scan" in t or "revisión" in t:
            return "onboarding_scan"
        return "onboarding"

    def _extract_actions(self, output: str) -> tuple[list[str], list[str]]:
        actions, next_steps = [], []
        for line in output.split("\n"):
            s = line.strip()
            if s.startswith("→") or (s.startswith("-") and "próximo" in output.lower()):
                next_steps.append(s.lstrip("→ -").strip())
        return actions, next_steps[:4]
