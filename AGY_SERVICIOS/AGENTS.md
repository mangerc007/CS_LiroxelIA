# AGENTS.md — AGY_SERVICIOS
> Grupo: AGY · Hereda de: ~/AGENTS.md (maestro v3.0)
> MCPs requeridos: stripe, cal-com, resend
> Dashboards: Reporte de cliente (URL por cliente)
> Repo: github.com/mangerc007/AGY_diagnostico
> Deploy: n/a (planificado)

## Propósito

Infraestructura de cobros, agenda y entrega de servicios de la agencia.

## Servicios

| Servicio | Precio | Stripe Product | Estado |
|----------|--------|---------------|--------|
| Diagnóstico Digital Express | Gratuito | — | 🔄 Pendiente |
| Estrategia Presencia Digital 90d | A definir | — | 🔄 Pendiente |
| Workshop Marketing + IA | A definir | — | 🔄 Pendiente |

## Flujo de cobro

```
Lead calificado desde AGY_DIAGNOSTICO
  → Discovery call via Cal.com
  → Propuesta enviada
  → Link de pago Stripe
  → Onboarding de cliente agencia
  → Reporte mensual (dashboard Vercel por cliente)
```

## Próximos pasos

- [ ] Crear productos en Stripe
- [ ] Configurar Cal.com con routing por servicio
- [ ] Template de reporte de cliente en Vercel

## Variables de entorno requeridas

Ver `.env.example` en esta carpeta.
