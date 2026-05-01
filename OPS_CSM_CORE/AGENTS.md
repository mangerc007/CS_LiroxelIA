# AGENTS.md — OPS_CSM_CORE
> Grupo: OPS · Hereda de: ~/AGENTS.md (maestro v3.0)
> MCPs requeridos: pipedrive, n8n, google-calendar, gmail, supabase
> Dashboards: Health Score Board, Churn Risk Radar, Renewal Pipeline
> Repo: github.com/mangerc007/OPS_csm_core
> Deploy: csm-dashboard.tudominio.com

## Propósito

Agente central de Customer Success para emBlue LATAM.  
Gestiona ~130 cuentas QBR/Autogestión y ~16 en Renegociación.

## Responsabilidades

- Monitoreo continuo de health scores por cuenta
- Detección temprana de señales de churn
- Preparación automatizada de QBRs
- Seguimiento de pipeline de renovaciones
- Activación de la etapa Business Kickoff (prioridad crítica)

## Señales de churn a monitorear

| Señal | Umbral | Acción |
|-------|--------|--------|
| Último login | >30 días | Alerta inmediata |
| Engagement rate | <10% | Review proactivo |
| NRR | <90% | Escalar a renegociación |
| Sin actividad n8n | >14 días | Check-in CSM |

## Playbooks disponibles

- `churn_prevention.md` — ejecutar antes de tocar cuentas en Renegociación
- `qbr_template.md` — base para preparar revisiones trimestrales
- `onboarding_checklist.md` — validar con cuentas en etapa Onboarding

## Pipeline Pipedrive

```
Technical Kickoff
  → Business Kickoff  [⚠️ ACTIVAR — actualmente vacío]
  → Onboarding
  → Adopción
  → QBR/Autogestión   (~130 cuentas)
  → Renegociación     (~16 cuentas — FOCO CRÍTICO)
  → Churn/Suspensión
  → Completado
```

## Variables de entorno requeridas

Ver `.env.example` en esta carpeta.
