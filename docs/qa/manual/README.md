# Batería de QA manual

Guiones ejecutables por un humano o por un agente con navegador (Chrome MCP / Browser). Complementan la suite pytest (`tests/`): cubren lo que solo se ve con la app corriendo (UI real, flujos completos, estados visuales).

## Cómo ejecutar

1. Levantar entorno local: backend (`python backend/api.py`, conda `rgenerator`), frontend (`npm run dev`), Docker PG.
2. Ejecutar cada guion en orden. Anotar resultado por paso: ✅ OK / ❌ FALLA / ⚠️ PARCIAL, con evidencia (screenshot o texto del error).
3. Registrar la corrida en `docs/qa/manual/corridas/AAAA-MM-DD.md` (copiar plantilla de abajo).
4. Todo ❌ se convierte en issue o entrada en `docs/qa/QA_MAESTRO.md`.

## Guiones

| # | Guion | Cubre | Origen |
|---|---|---|---|
| G1 | [Autenticación y sesión](g1_auth_sesion.md) | login, token expirado, logout, roles | QA frontend A4 |
| G2 | [Pipeline de punta a punta](g2_pipeline_e2e.md) | ejecutar pipeline, pausa interactiva, error legible, descarga | P0-3, P0-4 |
| G3 | [Dashboard y filtros](g3_dashboard_filtros.md) | /results, filtros multi-valor, cascada, consistencia con PDF | P0-1, P0-2 |
| G4 | [Generación de informes](g4_informes.md) | los 3 botones (v1, v2, Word), branding, filtros aplicados | informes H1-H9 |
| G5 | [Organización nueva / estados vacíos](g5_org_nueva.md) | onboarding, páginas vacías, mensajes | ux #1, #6 |
| G6 | [Multi-tenancy](g6_multitenancy.md) | aislamiento entre orgs con 2 usuarios | backend H-02 |

## Plantilla de corrida

```markdown
# Corrida QA manual — AAAA-MM-DD
Entorno: local | prod · Rama/commit: … · Ejecutor: humano | agente

| Guion | Resultado | Notas |
|---|---|---|
| G1 | ✅/❌/⚠️ | … |
...

## Fallas detectadas
- [Guion·paso] descripción, evidencia, severidad
```
