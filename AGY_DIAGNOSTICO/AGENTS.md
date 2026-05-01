# AGENTS.md — AGY_DIAGNOSTICO
> Grupo: AGY · Hereda de: ~/AGENTS.md (maestro v3.0)
> MCPs requeridos: n8n, supabase, tally (webhook via n8n)
> Dashboards: Lead Funnel Tracker
> Repo: github.com/mangerc007/AGY_diagnostico
> Deploy: diagnostico.tudominio.com

## Propósito

Widget de diagnóstico digital gratuito como lead magnet de la agencia.
Captura leads calificados de PyMEs en Perú/LATAM, los puntúa y los registra
en Supabase para seguimiento por el CSM de agencia.

## Flujo

```
1. PyME llena formulario Tally (diagnóstico digital)
2. Webhook n8n recibe respuestas
3. n8n calcula diagnostic_score (0-100)
4. Lead se registra en Supabase (tabla agency_leads)
5. Email automático con resultado + CTA discovery call (Resend)
6. Lead aparece en Lead Funnel Tracker dashboard
```

## Servicios relacionados

1. **Diagnóstico Digital Express** (gratuito — este formulario)
2. **Estrategia Presencia Digital 90 días** (pagado — upsell desde diagnóstico)
3. **Workshop Marketing + IA** (live/grabado)

## Estado

🔄 En desarrollo — formulario Tally pendiente de publicar.

## Variables de entorno requeridas

Ver `.env.example` en esta carpeta.
