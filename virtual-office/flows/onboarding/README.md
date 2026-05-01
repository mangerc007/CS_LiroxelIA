# Flow: onboarding

**Estado:** 🔄 Pendiente de implementación

**Descripción:** Automatiza la secuencia de onboarding desde Technical Kickoff hasta Adopción.

## Flujo esperado

```
Deal entra en "Business Kickoff"
  → Email de bienvenida (Resend) al contacto principal
  → Crear evento Google Calendar para kickoff (D+2)
  → Tarea en Pipedrive: "Confirmar kickoff con cliente"

Deal avanza a "Onboarding"
  → Secuencia de 3 emails en 7/14/21 días
  → Check: ¿primera campaña enviada en 14d? Si no → alerta CSM
  → Check: ¿primera automatización en 21d? Si no → sesión de ayuda

Deal avanza a "Adopción"
  → Email de bienvenida a Adopción
  → Programar primer QBR en 90 días
```

## Variables requeridas

```
PIPEDRIVE_API_TOKEN
PIPEDRIVE_STAGE_BUSINESS_KICKOFF
PIPEDRIVE_STAGE_ONBOARDING
PIPEDRIVE_STAGE_ADOPCION
RESEND_API_KEY
GOOGLE_CALENDAR_ID
```
