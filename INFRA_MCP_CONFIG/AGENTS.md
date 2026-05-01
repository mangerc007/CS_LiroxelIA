# AGENTS.md — INFRA_MCP_CONFIG
> Grupo: INFRA · Hereda de: ~/AGENTS.md (maestro v3.0)
> MCPs requeridos: todos
> Dashboards: n/a
> Repo: github.com/mangerc007/CLAUDE_MCP
> Deploy: n/a

## Propósito

Fuente de verdad de la configuración de todos los MCP servers del workspace.
Contiene `claude_desktop_config.json` y documentación de cada conector.

## Conectores activos

Ver sección 4.1 del AGENTS.md maestro.

## Pasos para activar un nuevo conector

```
1. Agregar entrada en src/claude_desktop_config.json
2. Actualizar sección 4.1 del AGENTS.md maestro
3. Crear nota en /docs/mcps/[conector].md
4. Agregar variables a .env.example raíz
5. Probar con: claude mcp list
```

## Próximos conectores a activar (prioridad)

- [ ] gmail — seguimiento de comunicaciones
- [ ] google-sheets — health scores tabulares
- [ ] supabase — base de datos persistente
- [ ] linear — task manager del agente
