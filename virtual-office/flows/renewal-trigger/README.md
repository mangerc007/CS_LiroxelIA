# Flow: renewal-trigger

**Estado:** 🔄 Pendiente de implementación

**Descripción:** Dispara el proceso de renovación 60 días antes del vencimiento del contrato.

## Flujo esperado

```
Cron: diario a las 09:00
  → Buscar deals con expected_close_date en los próximos 60 días
  → Para cada deal:
      - Calcular health score actual
      - Si score > 70: enviar email de renovación automática
      - Si score 50-70: crear tarea CSM "Iniciar conversación de renovación"
      - Si score < 50: mover a Renegociación + alerta urgente al CSM
```

## Variables requeridas

```
PIPEDRIVE_API_TOKEN
SUPABASE_URL
SUPABASE_SERVICE_KEY
RESEND_API_KEY
```
