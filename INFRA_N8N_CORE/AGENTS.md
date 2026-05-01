# AGENTS.md — INFRA_N8N_CORE
> Grupo: INFRA · Hereda de: ~/AGENTS.md (maestro v3.0)
> MCPs requeridos: n8n
> Dashboards: Workflow Monitor (n8n built-in)
> Repo: github.com/mangerc007/INFRA_n8n_flows
> Deploy: http://76.13.160.237:5678

## Propósito

Repositorio central de todos los workflows n8n exportados como JSON.
Permite versionar, documentar y restaurar automatizaciones desde GitHub.

## Convención de nombrado

```
[GRUPO]_[accion]_[objeto]_v[N].json
Ejemplos:
  OPS_detect_churn_accounts_v2.json
  OPS_prepare_qbr_summary_v1.json
  AGY_route_tally_leads_v1.json
  INFRA_health_check_vps_v1.json
```

## Workflows activos

> Documentar aquí cada workflow al exportarlo.

| Nombre | Descripción | Estado | Última versión |
|--------|-------------|--------|----------------|
| — | — | — | — |

## Procedimiento de exportación

```
1. En n8n: Workflow → Export → Download JSON
2. Renombrar según convención
3. Mover a /workflows/ con descripción en este AGENTS.md
4. Commit: [INFRA] docs: exportar workflow [nombre]
```

## Variables de entorno requeridas

Ver `.env.example` en esta carpeta.
