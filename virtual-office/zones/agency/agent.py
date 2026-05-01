"""
Zona agency — Sub-agente de Agencia de Consultoría.
Gestiona leads, diagnósticos, propuestas y onboarding de clientes de agencia.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from virtual_office.zones._base.zone import Zone, TaskResult
from virtual_office.integrations import supabase as db


class AgencyZone(Zone):
    name = "agency"
    max_tokens = 2000

    def execute(self, task: str, deal_id: Optional[int] = None,
                extra_context: dict = None) -> TaskResult:
        context = extra_context or {}
        context_block = self._build_agency_context(context)
        user_message = f"{context_block}\n\n## Tarea\n{task}".strip()

        output = self._call_claude(user_message)
        _, next_steps = self._extract_actions(output)

        result = TaskResult(
            zone=self.name,
            task_type=self._classify_task(task),
            success=True,
            output=output,
            next_steps=next_steps,
        )
        return result

    # ── Lead management ────────────────────────────────────────────────────────

    def interpret_diagnostic(self, lead_data: dict) -> TaskResult:
        """
        Interpreta los resultados del formulario Tally y genera:
        - Análisis personalizado del diagnóstico
        - Top 3 problemas urgentes
        - Quick win recomendado
        - Email de resultado para enviar al lead
        """
        score = lead_data.get("diagnostic_score", 0)
        company = lead_data.get("company", "tu empresa")
        answers = lead_data.get("answers", {})

        answers_text = "\n".join(
            f"- {k}: {v}" for k, v in answers.items()
        ) if answers else "Sin respuestas detalladas."

        task = (
            f"Interpreta el diagnóstico digital de {company}.\n"
            f"Score total: {score}/100\n"
            f"Respuestas del formulario:\n{answers_text}\n\n"
            "Genera: análisis personalizado, top 3 problemas urgentes, "
            "quick win recomendado, y el cuerpo del email de resultado (tono cercano, no corporativo)."
        )
        result = self.execute(task, extra_context={"lead": lead_data})

        # Guardar lead en Supabase
        try:
            db.insert("agency_leads", {
                "name":             lead_data.get("name", ""),
                "email":            lead_data.get("email", ""),
                "company":          lead_data.get("company", ""),
                "diagnostic_score": score,
                "source":           lead_data.get("source", "diagnostico_express"),
                "status":           "new",
                "notes":            result.output[:400],
            })
            result.actions_taken.append("Lead guardado en Supabase")
        except Exception as e:
            result.actions_taken.append(f"Supabase error: {e}")

        return result

    def prepare_discovery_call(self, lead_id: str) -> TaskResult:
        """Brief para la discovery call con un lead calificado."""
        leads = db.select("agency_leads", f"id=eq.{lead_id}")
        lead = leads[0] if leads else {}

        task = (
            f"Prepara el brief para la discovery call con {lead.get('company', 'el lead')}.\n"
            f"Score diagnóstico: {lead.get('diagnostic_score', '—')}/100\n"
            f"Email: {lead.get('email', '—')}\n"
            f"Notas previas: {lead.get('notes', 'Sin notas')}\n\n"
            "Incluye: perfil del lead, preguntas BANT adaptadas, "
            "hipótesis de necesidad principal, y servicios más relevantes para proponer."
        )
        return self.execute(task, extra_context={"lead": lead})

    def generate_proposal(self, lead_id: str, service: str,
                           discovery_notes: str = "") -> TaskResult:
        """Genera una propuesta comercial personalizada."""
        leads = db.select("agency_leads", f"id=eq.{lead_id}")
        lead = leads[0] if leads else {}

        task = (
            f"Genera la propuesta comercial para {lead.get('company', 'el cliente')}.\n"
            f"Servicio: {service}\n"
            f"Score diagnóstico: {lead.get('diagnostic_score', '—')}/100\n"
            f"Notas de la discovery call: {discovery_notes or 'Sin notas'}\n\n"
            "La propuesta debe ser específica para su negocio, "
            "mostrar ROI esperado con números, incluir garantía y CTA claro."
        )
        result = self.execute(task, extra_context={"lead": lead})

        # Actualizar estado del lead
        try:
            db.update("agency_leads", f"id=eq.{lead_id}", {"status": "proposal"})
            result.actions_taken.append("Lead actualizado a estado 'proposal'")
        except Exception as e:
            result.actions_taken.append(f"Supabase: {e}")

        return result

    def qualify_lead(self, lead_id: str) -> dict:
        """
        Califica un lead usando criterios BANT adaptados.
        Retorna score de calificación y recomendación de acción.
        """
        leads = db.select("agency_leads", f"id=eq.{lead_id}")
        if not leads:
            return {"qualified": False, "reason": "Lead no encontrado"}

        lead = leads[0]
        score = lead.get("diagnostic_score", 0)
        qualification_score = 0
        signals = []

        # Score del diagnóstico como proxy de necesidad
        if score < 55:
            qualification_score += 30
            signals.append(f"Alta necesidad (score {score}/100)")
        elif score < 75:
            qualification_score += 15
            signals.append(f"Necesidad moderada (score {score}/100)")

        # Fuente del lead
        if lead.get("source") == "referral":
            qualification_score += 25
            signals.append("Referido — intención alta")
        elif lead.get("source") == "diagnostico_express":
            qualification_score += 15
            signals.append("Diagnóstico completado — intención media")

        # Empresa con nombre real (proxy de tamaño)
        if lead.get("company") and len(lead.get("company", "")) > 3:
            qualification_score += 20
            signals.append("Empresa identificada")

        qualified = qualification_score >= 40
        next_action = (
            "Agendar discovery call en las próximas 24h"
            if qualified else
            "Nurturing automático — agregar a secuencia de emails"
        )

        return {
            "lead_id": lead_id,
            "qualified": qualified,
            "qualification_score": qualification_score,
            "signals": signals,
            "next_action": next_action,
        }

    def get_funnel_summary(self) -> dict:
        """Resumen del embudo de leads de agencia."""
        rows = db.select("v_agency_funnel")
        total = sum(r.get("leads", 0) for r in rows)
        won = next((r for r in rows if r["status"] == "won"), {})
        return {
            "total_leads": total,
            "won": won.get("leads", 0),
            "conversion_rate": round(won.get("leads", 0) / total * 100, 1) if total else 0,
            "by_status": {r["status"]: r["leads"] for r in rows},
        }

    # ── Private helpers ────────────────────────────────────────────────────────

    def _build_agency_context(self, context: dict) -> str:
        if not context:
            return ""
        lines = ["## Contexto de agencia"]
        if context.get("lead"):
            lead = context["lead"]
            lines.append(
                f"\n### Lead\n"
                f"- Empresa: {lead.get('company', '—')}\n"
                f"- Contacto: {lead.get('name', '—')} · {lead.get('email', '—')}\n"
                f"- Score diagnóstico: {lead.get('diagnostic_score', '—')}/100\n"
                f"- Estado: {lead.get('status', '—')}\n"
                f"- Fuente: {lead.get('source', '—')}"
            )
        return "\n".join(lines)

    def _classify_task(self, task: str) -> str:
        t = task.lower()
        if "diagnós" in t:
            return "diagnostic_interpretation"
        if "discovery" in t or "call" in t:
            return "discovery_prep"
        if "propuesta" in t:
            return "proposal"
        if "lead" in t:
            return "lead_qualification"
        return "agency_general"

    def _extract_actions(self, output: str) -> tuple[list[str], list[str]]:
        next_steps = []
        for line in output.split("\n"):
            s = line.strip()
            if s.startswith("→") or s.startswith("**Próximo paso"):
                next_steps.append(s.lstrip("→ *").strip())
        return [], next_steps[:3]
