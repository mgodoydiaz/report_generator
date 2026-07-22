# G5 — Organización nueva / estados vacíos

**Precondiciones**: crear una org limpia con un usuario (vía CLI o /superadmin).

| # | Acción | Esperado |
|---|---|---|
| 1 | Login con el usuario de la org vacía → Home | Mensaje de "aún no hay nada configurado" con siguiente paso claro — NO un home genérico que aparenta estar roto |
| 2 | /execution sin pipelines | Copy de "tu organización no tiene procesos configurados" — NO "sin resultados de búsqueda" (QA ux #6) |
| 3 | /results sin indicadores | Selector vacío con explicación, no página en blanco |
| 4 | /metrics, /dimensions, /specs vacíos | Estados vacíos con CTA o explicación |
| 5 | /help | ¿Un usuario final entiende qué hacer? (hoy se espera ⚠️: es doc técnica) |
| 6 | Con la API caída (matar backend), abrir /pipelines | Error visible de conexión — NO página idéntica a "sin pipelines" (QA frontend A2) |
