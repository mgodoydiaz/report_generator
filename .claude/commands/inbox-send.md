---
description: Envía un nuevo mensaje al otro lado del bridge WSL↔Windows
argument-hint: <descripción del pedido>
allowed-tools: Read, Edit, Bash
---

El usuario quiere enviar un nuevo mensaje al otro lado del bridge `agents/wsl_bridge/`.
Ver protocolo en `agents/wsl_bridge/README.md`.

**Pedido del usuario**: $ARGUMENTS

## Paso 1 — Detectar tu lado

Ejecuta `uname -s`:
- `Linux` → eres **`wsl-claude`**, escribes en `agents/wsl_bridge/inbox_windows.md`
- otro (MSYS, MINGW, etc.) → eres **`windows-claude`**, escribes en
  `agents/wsl_bridge/inbox_wsl.md`

## Paso 2 — Leer el archivo destino

Lee el inbox del otro lado para tener contexto previo (qué se pidió antes, qué
respondió el otro agente, evitar duplicar pedidos).

## Paso 3 — Componer el mensaje

Convierte `$ARGUMENTS` en un mensaje útil y completo para el otro agente. Buena
respuesta = el otro agente puede ejecutar sin tener que volver a preguntar.

Incluye según corresponda:
- **Action** (1 línea): qué se le pide
- **Contexto** (2-4 líneas): por qué, qué se intentó antes
- **Comandos exactos** que esperas que corra (en bloque ```bash)
- **Qué esperas de respuesta**: outputs específicos, archivos generados, etc.

## Paso 4 — Escribir al final del archivo

Agrega al final del inbox destino:

```markdown

## [YYYY-MM-DD HH:MM:SS] FROM: <tu nombre> TO: <otro nombre>
**Status**: PENDING
**Action**: <una línea>

<contexto + comandos + qué esperas>

```bash
comando1
comando2
```

<expectativa de respuesta>

--- END ---
```

Usa `date '+%Y-%m-%d %H:%M:%S'` para el timestamp. Append-only: NO borres nada.

## Paso 5 — Confirmar al usuario

Resume en 2 líneas qué pediste y a quién: "Enviado a wsl-claude: <action>. Esperando
respuesta en inbox_windows.md."

Sugiere al usuario que la otra sesión Claude Code (en el otro lado) ejecute `/inbox`
para procesar el mensaje.
