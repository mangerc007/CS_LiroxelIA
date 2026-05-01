# Flow: health-alert

**Trigger:** Diario a las 08:00 (ScheduleTrigger)
**Descripción:** Evalúa deals en etapa Renegociación, calcula health scores, guarda en Supabase y crea actividades urgentes en Pipedrive para cuentas críticas.

## Variables requeridas en n8n

```
PIPEDRIVE_API_TOKEN
PIPEDRIVE_STAGE_RENEGOCIACION   ← ID numérico de la etapa en Pipedrive
SUPABASE_URL
SUPABASE_SERVICE_KEY
```

## Versiones

| Versión | Descripción |
|---------|-------------|
| v1.json | Implementación inicial: Pipedrive → score → Supabase → alerta Pipedrive |

## Para importar en n8n

1. Ir a n8n → Workflows → Import from File
2. Seleccionar `v1.json`
3. Configurar las variables de entorno en Settings → Environment
4. Activar el workflow
