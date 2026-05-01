# AGENTS.md — OPS_ONBOARDING_AGENT
> Grupo: OPS · Hereda de: ~/AGENTS.md (maestro v3.0)
> MCPs requeridos: pipedrive, n8n, google-calendar, resend
> Dashboards: Onboarding Tracker
> Repo: github.com/mangerc007/OPS_csm_core
> Deploy: n/a (planificado)

## Propósito

Automatizar y orquestar el proceso de onboarding para nuevas cuentas emBlue,
desde Technical Kickoff hasta la etapa de Adopción.

## Estado

🔄 Planificado — pendiente de activar etapa Business Kickoff en Pipedrive (prioridad #1).

## Flujo esperado

```
1. Deal entra en "Technical Kickoff" → crear evento Google Calendar
2. Deal avanza a "Business Kickoff"  → enviar email de bienvenida (Resend)
3. Deal en "Onboarding"              → secuencia de 3 emails + tarea CSM
4. Deal en "Adopción"                → check-in a los 30 días
5. Sin actividad en 14 días          → alerta automática al CSM
```

## Variables de entorno requeridas

Ver `.env.example` en esta carpeta.
