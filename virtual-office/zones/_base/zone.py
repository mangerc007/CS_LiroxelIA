"""
Clase base para todas las zonas del virtual-office.
Cada zona hereda de Zone e implementa execute().
"""

from __future__ import annotations

import os
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import anthropic

from virtual_office.integrations import supabase as db


@dataclass
class TaskResult:
    zone: str
    task_type: str
    success: bool
    output: str
    actions_taken: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    deal_id: Optional[int] = None
    executed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "zone": self.zone,
            "task_type": self.task_type,
            "success": self.success,
            "output": self.output,
            "actions_taken": self.actions_taken,
            "next_steps": self.next_steps,
            "deal_id": self.deal_id,
            "executed_at": self.executed_at,
        }

    def __str__(self) -> str:
        status = "✓" if self.success else "✗"
        lines = [f"[{status}] {self.zone} · {self.task_type}"]
        lines.append(self.output)
        if self.actions_taken:
            lines.append("\nAcciones tomadas:")
            lines.extend(f"  • {a}" for a in self.actions_taken)
        if self.next_steps:
            lines.append("\nPróximos pasos:")
            lines.extend(f"  → {s}" for s in self.next_steps)
        return "\n".join(lines)


class Zone(ABC):
    """
    Contrato base para todos los sub-agentes del virtual-office.

    Flujo de ejecución:
        1. load_context(deal_id)   ← carga Supabase + archivo memory/accounts/
        2. execute(task, context)  ← llama a Claude con contexto enriquecido
        3. save_result(result)     ← persiste interacción en Supabase
    """

    name: str = "base"
    model_env: str = "CLAUDE_MODEL_QUALITY"
    max_tokens: int = 1500

    def __init__(self):
        self._client = anthropic.Anthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"]
        )
        self._model = os.environ.get(self.model_env, "claude-sonnet-4-6")
        self._prompt_path = Path(__file__).parent.parent / self.name / "prompts" / "v1.md"
        self._system_prompt: Optional[str] = None

    # ── System prompt ─────────────────────────────────────────────────────────

    def get_system_prompt(self) -> str:
        if self._system_prompt:
            return self._system_prompt
        if self._prompt_path.exists():
            self._system_prompt = self._prompt_path.read_text()
        else:
            self._system_prompt = f"Eres el agente de la zona {self.name} del CSM de emBlue LATAM."
        return self._system_prompt

    # ── Context loading ───────────────────────────────────────────────────────

    def load_health(self, deal_id: int) -> Optional[dict]:
        rows = db.select("v_latest_health", f"pipedrive_deal_id=eq.{deal_id}")
        return rows[0] if rows else None

    def load_interactions(self, deal_id: int, limit: int = 5) -> list[dict]:
        return db.select(
            "csm_interactions",
            f"deal_id=eq.{deal_id}",
            order="created_at.desc",
            limit=limit,
        )

    def load_account_file(self, deal_id: int) -> str:
        """Lee el archivo .md de memoria por cuenta si existe."""
        p = Path(__file__).parent.parent.parent / "memory" / "accounts" / f"{deal_id}.md"
        return p.read_text() if p.exists() else ""

    def load_context(self, deal_id: int) -> dict:
        return {
            "deal_id": deal_id,
            "health": self.load_health(deal_id),
            "recent_interactions": self.load_interactions(deal_id),
            "account_notes": self.load_account_file(deal_id),
        }

    def build_context_block(self, context: dict) -> str:
        """Formatea el contexto como bloque de texto para Claude."""
        lines = [f"## Contexto — Deal #{context['deal_id']}"]

        if context.get("health"):
            h = context["health"]
            lines.append(
                f"\n### Health Score\n"
                f"- Score: {h['score']}/100 · Riesgo: {h['risk_level'].upper()}\n"
                f"- Engagement: {h.get('engagement_rate') or '—'}%"
                f" · NRR: {h.get('nrr') or '—'}%\n"
                f"- Último login: {h.get('last_login') or '—'}"
            )
        else:
            lines.append("\n### Health Score\nSin datos previos.")

        if context.get("recent_interactions"):
            lines.append("\n### Últimas interacciones")
            for i in context["recent_interactions"]:
                lines.append(f"- [{i['type']}] {i['created_at'][:10]}: {i['summary']}")

        if context.get("account_notes"):
            lines.append(f"\n### Notas de cuenta\n{context['account_notes']}")

        return "\n".join(lines)

    # ── Core execution ────────────────────────────────────────────────────────

    @abstractmethod
    def execute(self, task: str, deal_id: Optional[int] = None,
                extra_context: dict = None) -> TaskResult:
        """Implementar en cada zona."""
        ...

    def _call_claude(self, user_message: str) -> str:
        """Llamada base a Claude con system prompt de la zona."""
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self.max_tokens,
            system=self.get_system_prompt(),
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text

    # ── Persistence ───────────────────────────────────────────────────────────

    def save_result(self, result: TaskResult) -> None:
        if not result.deal_id:
            return
        try:
            db.insert("csm_interactions", {
                "deal_id": result.deal_id,
                "type": result.task_type,
                "summary": result.output[:500],
                "outcome": "completed" if result.success else "failed",
                "next_action": result.next_steps[0] if result.next_steps else "",
            })
        except Exception as e:
            print(f"[warn] No se pudo guardar interacción en Supabase: {e}")
