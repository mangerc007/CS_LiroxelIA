"""
Router del super-agente.
Recibe una tarea en lenguaje natural y decide qué zona la ejecuta.
"""

import json
import os
from pathlib import Path
from typing import Optional
import anthropic

_PROMPT_PATH = Path(__file__).parent / "prompts" / "router_v1.md"
_MODEL = os.environ.get("CLAUDE_MODEL_QUALITY", "claude-sonnet-4-6")


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text()


def route(task: str) -> dict:
    """
    Analiza la tarea y retorna un dict con:
      zone, confidence, task_type, urgency, context_needed, reasoning, subtasks
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    response = client.messages.create(
        model=_MODEL,
        max_tokens=512,
        system=_load_prompt(),
        messages=[{"role": "user", "content": f"Tarea: {task}"}],
    )

    raw = response.content[0].text.strip()

    # Extraer JSON aunque Claude agregue texto alrededor
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    if start == -1 or end == 0:
        return _fallback_route(task)

    try:
        return json.loads(raw[start:end])
    except json.JSONDecodeError:
        return _fallback_route(task)


def _fallback_route(task: str) -> dict:
    """
    Routing determinístico por palabras clave cuando Claude falla.
    Garantiza que siempre haya una zona asignada.
    """
    task_lower = task.lower()

    if any(w in task_lower for w in ["renegoci", "churn", "cancel", "no renov", "baja"]):
        zone = "cs-renewals"
    elif any(w in task_lower for w in ["onboarding", "kickoff", "nuevo cliente", "activaci"]):
        zone = "cs-onboarding"
    elif any(w in task_lower for w in ["agencia", "lead", "diagn", "propuesta", "cobro"]):
        zone = "agency"
    elif any(w in task_lower for w in ["post", "linkedin", "contenido", "editorial"]):
        zone = "content"
    else:
        zone = "cs-health-analyst"

    return {
        "zone": zone,
        "confidence": 0.6,
        "task_type": "general",
        "urgency": "medium",
        "context_needed": ["deal_id"],
        "reasoning": "Routing por palabras clave (fallback).",
        "subtasks": [],
    }
