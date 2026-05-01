# CS_LiroxelIA — Agente CSM Maestro

Workspace raíz del sistema IA de Manger Canterac.  
Combina Customer Success (emBlue) + Agencia Digital LATAM + Marca Personal.

## Estructura

```
CS_LiroxelIA/
  AGENTS.md              ← contexto maestro del agente (leer primero)
  .env.example           ← variables de entorno requeridas
  OPS_CSM_CORE/          ← agente CSM emBlue (~130 cuentas)
  OPS_ONBOARDING_AGENT/  ← automatización onboarding
  INFRA_N8N_CORE/        ← workflows n8n documentados
  INFRA_MCP_CONFIG/      ← configuración de MCP servers
  AGY_DIAGNOSTICO/       ← widget diagnóstico + landing agencia
  AGY_SERVICIOS/         ← cobros y agenda agencia
  BRAND_CONTENIDO/       ← plantillas y calendario editorial
```

## Inicio rápido

1. Clonar el repo y crear `.env` desde `.env.example`
2. Leer `AGENTS.md` para entender el contexto completo
3. Navegar al proyecto específico según la tarea (OPS / INFRA / AGY / BRAND)
4. Cada sub-proyecto tiene su propio `AGENTS.md` y `README.md`

## Stack principal

| Capa | Herramienta |
|------|-------------|
| Cerebro | Claude Code (claude-sonnet-4-6) |
| CRM | Pipedrive |
| Automatización | n8n (VPS Hostinger) |
| Base de datos | Supabase |
| Deployment | Vercel + Cloudflare Workers |
| Email | Resend |
| Cobros | Stripe |
| Agenda | Cal.com + Google Calendar |

## Convención de commits

```
[GRUPO] acción: descripción breve
```

Grupos: `OPS` · `INFRA` · `AGY` · `BRAND`
