# AGENTS.md — virtual-office
> Grupo: OPS · Hereda de: ~/AGENTS.md (maestro v3.0)
> MCPs requeridos: pipedrive, supabase, n8n, google-calendar, gmail
> Dashboards: health-score-board, churn-radar
> Repo: github.com/mangerc007/CS_LiroxelIA
> Deploy: csm-dashboard.tudominio.com

## Qué es esto

`virtual-office/` es el núcleo operativo del super-agente CSM. Implementa el patrón **Orchestrator → Zone → Integration → Memory**:

```
Usuario / n8n / cron
        ↓
  orchestrator/        ← recibe la tarea, decide qué zona la maneja
        ↓
  zones/[zona]/        ← sub-agente especializado con contexto propio
        ↓
  integrations/        ← wrappers de API sin lógica de negocio
        ↓
  memory/              ← contexto persistente (Supabase + archivos .md)
```

## Zonas activas

| Zona | Responsabilidad | Prioridad |
|------|----------------|-----------|
| `cs-renewals` | Renegociación — 16 cuentas críticas | 🔴 Activa |
| `cs-health-analyst` | Scoring, detección de churn, alertas | 🔴 Activa |
| `cs-onboarding` | Nuevas cuentas: kickoff → adopción | 🟡 En construcción |
| `agency` | Leads, diagnóstico, propuestas agencia | 🟡 En construcción |
| `content` | Marca personal, calendario editorial | 🟢 Planificada |

## Cómo correr el agente

```bash
# Instalar dependencias
pip install -r requirements.txt

# Escaneo diario de churn (también lo dispara n8n)
python orchestrator/main.py scan

# Analizar una cuenta específica
python orchestrator/main.py analyze --deal 1234

# Preparar QBR
python orchestrator/main.py qbr --deal 1234 --date 2026-05-15

# Modo interactivo
python orchestrator/main.py chat
```

## Variables de entorno requeridas

Ver `.env.example` en raíz del repo.
