"""
Super-agente CSM — Entry point único.

Uso:
  python orchestrator/main.py scan
  python orchestrator/main.py analyze --deal 1234
  python orchestrator/main.py qbr --deal 1234 --date 2026-05-15
  python orchestrator/main.py kickoff --deal 1234
  python orchestrator/main.py diagnostic --lead '{"name":"Ana","email":"a@b.com","company":"PyME SA","diagnostic_score":38}'
  python orchestrator/main.py post --platform linkedin --pillar cs_ia --idea "cómo detecto churn antes de que el cliente lo diga"
  python orchestrator/main.py calendar --week 2026-05-05
  python orchestrator/main.py task "prepara el QBR de Falabella deal 1234"
  python orchestrator/main.py chat
"""

import sys
import json
import argparse
from pathlib import Path

# Asegurar que virtual-office/ esté en el path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from virtual_office.orchestrator.router import route
from virtual_office.zones.cs_health_analyst.agent import HealthAnalystZone
from virtual_office.zones.cs_renewals.agent import RenewalsZone
from virtual_office.zones.cs_onboarding.agent import OnboardingZone
from virtual_office.zones.agency.agent import AgencyZone
from virtual_office.zones.content.agent import ContentZone


# ── Registro de zonas ─────────────────────────────────────────────────────────

ZONES = {
    "cs-health-analyst": HealthAnalystZone,
    "cs-renewals":       RenewalsZone,
    "cs-onboarding":     OnboardingZone,
    "agency":            AgencyZone,
    "content":           ContentZone,
}


def get_zone(name: str):
    cls = ZONES.get(name)
    if not cls:
        print(f"[info] Zona '{name}' no reconocida — usando cs-health-analyst.")
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
    result = zone.prepare_qbr(deal_id, date)
    print(result)
    zone.save_result(result)


def cmd_kickoff(deal_id: int):
    """Prepara el Business Kickoff de una cuenta nueva."""
    print(f"🚀 Preparando Business Kickoff — deal #{deal_id}...\n")
    zone = OnboardingZone()
    result = zone.prepare_business_kickoff(deal_id)
    print(result)
    zone.save_result(result)


def cmd_onboarding_scan():
    """Revisión de todas las cuentas en onboarding."""
    print("🔍 Escaneando cuentas en onboarding...\n")
    zone = OnboardingZone()
    result = zone.run_weekly_onboarding_scan()
    print(result)


def cmd_diagnostic(lead_json: str):
    """Interpreta el diagnóstico digital de un lead de agencia."""
    try:
        lead_data = json.loads(lead_json)
    except json.JSONDecodeError:
        print("[error] El argumento debe ser un JSON válido.")
        return
    print(f"🔬 Interpretando diagnóstico de {lead_data.get('company', 'lead')}...\n")
    zone = AgencyZone()
    result = zone.interpret_diagnostic(lead_data)
    print(result)


def cmd_post(platform: str, pillar: str, idea: str, format_type: str = "texto"):
    """Genera un post de contenido listo para publicar."""
    print(f"✍️  Generando post para {platform.upper()}...\n")
    zone = ContentZone()
    result = zone.generate_post(platform, pillar, idea, format_type)
    print(result)


def cmd_calendar(week_start: str = "", ideas_raw: str = ""):
    """Genera el calendario editorial semanal."""
    print(f"📅 Generando calendario editorial{' — semana ' + week_start if week_start else ''}...\n")
    ideas = [i.strip() for i in ideas_raw.split(",") if i.strip()] if ideas_raw else []
    zone = ContentZone()
    result = zone.generate_weekly_calendar(week_start, ideas or None)
    print(result)


def cmd_renewals_review():
    """Revisión semanal de las 16 cuentas en Renegociación."""
    print("📊 Revisión de cuentas en Renegociación...\n")
    zone = RenewalsZone()
    result = zone.run_renewals_review()
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
        description="Super-agente CSM emBlue · Manger Canterac",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Comandos disponibles:
  scan              Escaneo diario de churn
  analyze           Análisis profundo de una cuenta
  qbr               Preparar materiales QBR
  kickoff           Preparar Business Kickoff
  onboarding-scan   Revisar cuentas en onboarding
  renewals          Revisión semanal de Renegociación
  diagnostic        Interpretar diagnóstico de lead de agencia
  post              Generar post de contenido
  calendar          Generar calendario editorial semanal
  task              Cualquier tarea en lenguaje natural
  chat              Modo interactivo
        """
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("scan",     help="Escaneo diario de churn")
    subparsers.add_parser("renewals", help="Revisión semanal de Renegociación")
    subparsers.add_parser("onboarding-scan", help="Revisar cuentas en onboarding")

    p_analyze = subparsers.add_parser("analyze", help="Analizar una cuenta")
    p_analyze.add_argument("--deal", type=int, required=True)
    p_analyze.add_argument("--message", default="")

    p_qbr = subparsers.add_parser("qbr", help="Preparar QBR")
    p_qbr.add_argument("--deal", type=int, required=True)
    p_qbr.add_argument("--date", default="")

    p_kickoff = subparsers.add_parser("kickoff", help="Preparar Business Kickoff")
    p_kickoff.add_argument("--deal", type=int, required=True)

    p_diag = subparsers.add_parser("diagnostic", help="Interpretar diagnóstico de lead")
    p_diag.add_argument("--lead", required=True, help='JSON del lead: \'{"name":"...","email":"...","company":"...","diagnostic_score":38}\'')

    p_post = subparsers.add_parser("post", help="Generar post de contenido")
    p_post.add_argument("--platform", choices=["linkedin", "instagram"], required=True)
    p_post.add_argument("--pillar",   choices=["cs_ia","casos","tacticas","detras","latam"], required=True)
    p_post.add_argument("--idea",     required=True)
    p_post.add_argument("--format",   default="texto", dest="format_type")

    p_cal = subparsers.add_parser("calendar", help="Generar calendario editorial semanal")
    p_cal.add_argument("--week",  default="", help="Fecha de inicio (YYYY-MM-DD)")
    p_cal.add_argument("--ideas", default="", help="Ideas separadas por comas")

    p_task = subparsers.add_parser("task", help="Tarea en lenguaje natural")
    p_task.add_argument("text", nargs="+")

    subparsers.add_parser("chat", help="Modo interactivo")

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan()
    elif args.command == "renewals":
        cmd_renewals_review()
    elif args.command == "onboarding-scan":
        cmd_onboarding_scan()
    elif args.command == "analyze":
        cmd_analyze(args.deal, args.message)
    elif args.command == "qbr":
        cmd_qbr(args.deal, args.date)
    elif args.command == "kickoff":
        cmd_kickoff(args.deal)
    elif args.command == "diagnostic":
        cmd_diagnostic(args.lead)
    elif args.command == "post":
        cmd_post(args.platform, args.pillar, args.idea, args.format_type)
    elif args.command == "calendar":
        cmd_calendar(args.week, args.ideas)
    elif args.command == "task":
        cmd_task(" ".join(args.text))
    elif args.command == "chat":
        cmd_chat()


if __name__ == "__main__":
    main()
