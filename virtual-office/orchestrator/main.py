"""
Super-agente CSM — Entry point único.

Uso:
  python orchestrator/main.py scan
  python orchestrator/main.py analyze --deal 1234
  python orchestrator/main.py qbr --deal 1234 --date 2026-05-15
  python orchestrator/main.py task "prepara el QBR de Falabella deal 1234"
  python orchestrator/main.py chat
"""

import sys
import argparse
from pathlib import Path

# Asegurar que virtual-office/ esté en el path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from virtual_office.orchestrator.router import route
from virtual_office.zones.cs_health_analyst.agent import HealthAnalystZone
from virtual_office.zones.cs_renewals.agent import RenewalsZone


# ── Registro de zonas ─────────────────────────────────────────────────────────

ZONES = {
    "cs-health-analyst": HealthAnalystZone,
    "cs-renewals":       RenewalsZone,
}


def get_zone(name: str):
    cls = ZONES.get(name)
    if not cls:
        # Zonas aún no implementadas: fallback a health analyst
        print(f"[info] Zona '{name}' no implementada aún — usando cs-health-analyst.")
        cls = HealthAnalystZone
    return cls()


# ── Comandos ──────────────────────────────────────────────────────────────────

def cmd_scan():
    """Escaneo diario de churn — todas las cuentas en riesgo."""
    print("🔍 Iniciando churn scan...\n")
    zone = HealthAnalystZone()
    result = zone.execute("Escanea todas las cuentas en riesgo y genera resumen ejecutivo.")
    print(result)
    zone.save_result(result)


def cmd_analyze(deal_id: int, message: str = ""):
    """Análisis profundo de una cuenta específica."""
    print(f"🔎 Analizando deal #{deal_id}...\n")
    task = message or f"Analiza la cuenta deal #{deal_id} y recomienda la próxima acción."
    routing = route(task)
    print(f"[router] → {routing['zone']} (confianza {routing['confidence']:.0%})\n")
    zone = get_zone(routing["zone"])
    result = zone.execute(task, deal_id=deal_id)
    print(result)
    zone.save_result(result)


def cmd_qbr(deal_id: int, date: str = ""):
    """Prepara materiales para un QBR."""
    task = f"Prepara el QBR del deal #{deal_id}" + (f" para el {date}" if date else "")
    print(f"📋 {task}\n")
    zone = HealthAnalystZone()
    result = zone.execute(task, deal_id=deal_id)
    print(result)
    zone.save_result(result)


def cmd_task(task: str):
    """Ejecuta cualquier tarea en lenguaje natural."""
    print(f"⚡ Tarea: {task}\n")
    routing = route(task)
    print(
        f"[router] → {routing['zone']} "
        f"(confianza {routing['confidence']:.0%}, urgencia {routing['urgency']})\n"
        f"[razón]  {routing['reasoning']}\n"
    )
    zone = get_zone(routing["zone"])
    result = zone.execute(task)
    print(result)
    zone.save_result(result)


def cmd_chat():
    """Modo interactivo — conversación continua con el agente."""
    print("💬 Modo interactivo — escribe 'salir' para terminar.\n")
    while True:
        try:
            task = input("Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if task.lower() in ("salir", "exit", "quit"):
            break
        if not task:
            continue
        cmd_task(task)
        print()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Super-agente CSM emBlue · Manger Canterac"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("scan", help="Escaneo diario de churn")

    p_analyze = subparsers.add_parser("analyze", help="Analizar una cuenta")
    p_analyze.add_argument("--deal", type=int, required=True)
    p_analyze.add_argument("--message", default="")

    p_qbr = subparsers.add_parser("qbr", help="Preparar QBR")
    p_qbr.add_argument("--deal", type=int, required=True)
    p_qbr.add_argument("--date", default="")

    p_task = subparsers.add_parser("task", help="Tarea en lenguaje natural")
    p_task.add_argument("text", nargs="+")

    subparsers.add_parser("chat", help="Modo interactivo")

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan()
    elif args.command == "analyze":
        cmd_analyze(args.deal, args.message)
    elif args.command == "qbr":
        cmd_qbr(args.deal, args.date)
    elif args.command == "task":
        cmd_task(" ".join(args.text))
    elif args.command == "chat":
        cmd_chat()


if __name__ == "__main__":
    main()
