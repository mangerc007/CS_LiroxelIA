"""
Zona content — Sub-agente de Marca Personal y Contenido.
Genera posts, calendarios editoriales y trackea métricas de contenido.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from virtual_office.zones._base.zone import Zone, TaskResult
from virtual_office.integrations import supabase as db


# Pilares de contenido
PILLARS = {
    "cs_ia":      "CS + IA: cómo la IA cambia el trabajo de Customer Success",
    "casos":      "Casos reales (anonimizados) del trabajo semanal",
    "tacticas":   "Frameworks y templates accionables",
    "detras":     "Detrás de escena: construir en público",
    "latam":      "Tendencias globales con perspectiva LATAM",
}


class ContentZone(Zone):
    name = "content"
    max_tokens = 2000

    def execute(self, task: str, deal_id: Optional[int] = None,
                extra_context: dict = None) -> TaskResult:
        context = extra_context or {}
        context_block = self._build_content_context(context)
        user_message = f"{context_block}\n\n## Tarea\n{task}".strip()

        output = self._call_claude(user_message)

        return TaskResult(
            zone=self.name,
            task_type=self._classify_task(task),
            success=True,
            output=output,
        )

    # ── Content generation ─────────────────────────────────────────────────────

    def generate_post(self, platform: str, pillar: str, idea: str,
                       format_type: str = "texto") -> TaskResult:
        """
        Genera un post completo listo para publicar.
        platform: linkedin | instagram
        pillar: cs_ia | casos | tacticas | detras | latam
        format_type: texto | carrusel | reel_script
        """
        pillar_desc = PILLARS.get(pillar, pillar)

        task = (
            f"Genera un post para {platform.upper()} en formato {format_type}.\n"
            f"Pilar de contenido: {pillar_desc}\n"
            f"Idea o tema: {idea}\n\n"
            "Recuerda: viene de una experiencia real, tono directo y conversacional, "
            "sin jargon corporativo, con datos cuando sea posible."
        )
        result = self.execute(task, extra_context={"platform": platform, "pillar": pillar})

        # Guardar en Supabase para tracking
        try:
            db.insert("content_metrics", {
                "platform":    platform,
                "title":       idea[:100],
                "published_at": datetime.now(timezone.utc).isoformat(),
            })
            result.actions_taken.append("Registrado en content_metrics")
        except Exception:
            pass

        return result

    def generate_weekly_calendar(self, week_start: str = "",
                                  ideas: list[str] = None) -> TaskResult:
        """
        Genera el calendario editorial de una semana completa.
        Incluye posts listos para LinkedIn (2) e Instagram (3).
        """
        if not week_start:
            week_start = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        ideas_text = ""
        if ideas:
            ideas_text = "Ideas/temas para esta semana:\n" + "\n".join(f"- {i}" for i in ideas)

        task = (
            f"Genera el calendario editorial completo para la semana del {week_start}.\n"
            f"{ideas_text}\n\n"
            "Crea 5 posts listos para publicar: 2 LinkedIn (mar/jue) + 3 Instagram (lun/mié/sáb). "
            "Variedad de pilares, formatos distintos, y todos basados en experiencias reales de CSM o agencia."
        )
        return self.execute(task, extra_context={"week_start": week_start})

    def extract_content_from_csm_week(self, csm_insights: list[str]) -> TaskResult:
        """
        Transforma insights del trabajo CSM en ideas de contenido.
        La fuente más auténtica: lo que pasó esta semana con los clientes.
        """
        insights_text = "\n".join(f"- {i}" for i in csm_insights)

        task = (
            f"Estos son los insights reales de la semana de trabajo CSM:\n{insights_text}\n\n"
            "Convierte estos insights en 5 ideas de contenido concretas para LinkedIn/Instagram. "
            "Para cada idea: plataforma, formato, ángulo editorial, y el hook de apertura."
        )
        return self.execute(task)

    def generate_linkedin_thread(self, topic: str, data_points: list[str] = None) -> TaskResult:
        """Genera un hilo de LinkedIn (formato de alto engagement)."""
        data_text = ""
        if data_points:
            data_text = "Datos/evidencia disponible:\n" + "\n".join(f"- {d}" for d in data_points)

        task = (
            f"Genera un hilo de LinkedIn sobre: {topic}\n"
            f"{data_text}\n\n"
            "Formato: tweet 1 (hook fuerte) + 4-6 tweets de desarrollo + tweet final (CTA). "
            "Cada tweet separado con '---'. Máx 280 caracteres por tweet."
        )
        return self.execute(task)

    def log_post_performance(self, platform: str, post_title: str,
                              impressions: int, engagement_rate: float,
                              leads_generated: int = 0) -> None:
        """Registra el rendimiento de un post publicado."""
        db.insert("content_metrics", {
            "platform":         platform,
            "title":            post_title[:100],
            "impressions":      impressions,
            "engagement_rate":  engagement_rate,
            "leads_generated":  leads_generated,
            "published_at":     datetime.now(timezone.utc).isoformat(),
        })

    def get_performance_summary(self, platform: str = None) -> dict:
        """Resumen de métricas de contenido."""
        filters = f"platform=eq.{platform}" if platform else ""
        rows = db.select("content_metrics", filters, order="published_at.desc", limit=30)

        if not rows:
            return {"posts": 0, "avg_engagement": 0, "total_leads": 0}

        avg_eng = sum(r.get("engagement_rate", 0) for r in rows) / len(rows)
        total_leads = sum(r.get("leads_generated", 0) for r in rows)

        return {
            "posts":          len(rows),
            "avg_engagement": round(avg_eng, 2),
            "total_leads":    total_leads,
            "best_post":      max(rows, key=lambda r: r.get("engagement_rate", 0)).get("title"),
        }

    # ── Private helpers ────────────────────────────────────────────────────────

    def _build_content_context(self, context: dict) -> str:
        if not context:
            return ""
        lines = ["## Contexto editorial"]
        if context.get("platform"):
            lines.append(f"- Plataforma: {context['platform'].upper()}")
        if context.get("pillar"):
            lines.append(f"- Pilar: {PILLARS.get(context['pillar'], context['pillar'])}")
        if context.get("week_start"):
            lines.append(f"- Semana: {context['week_start']}")
        return "\n".join(lines)

    def _classify_task(self, task: str) -> str:
        t = task.lower()
        if "calendario" in t or "semana" in t:
            return "weekly_calendar"
        if "hilo" in t or "thread" in t:
            return "linkedin_thread"
        if "insight" in t or "csm" in t:
            return "content_from_csm"
        return "post_generation"
