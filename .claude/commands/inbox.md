---
description: Lee el inbox del bridge WSL↔Windows y procesa el último mensaje pendiente
argument-hint: [windows|wsl]
allowed-tools: Read, Write, Edit, Bash
---

Estás procesando el inbox del bridge `agents/wsl_bridge/`. Ver el README en
`agents/wsl_bridge/README.md` para el protocolo completo.

## Paso 1 — Detectar tu lado

Si el usuario pasó `windows` o `wsl` como `$ARGUMENTS`, usa ese lado.

Si no, detéctalo automáticamente con `uname -s`:
- `Linux` → eres **`wsl-claude`**, tu inbox es `agents/wsl_bridge/inbox_wsl.md`
- `MSYS_NT*`, `MINGW*` o cualquier otro → eres **`windows-claude`**, tu inbox es
  `agents/wsl_bridge/inbox_windows.md`

## Paso 2 — Leer tu inbox

Lee TU inbox completo (no el del otro lado). Identifica el **último mensaje**:
es el bloque después del último header `## [TIMESTAMP] FROM: ...`.

## Paso 3 — Decidir si hay que procesar

Procesa el mensaje SI:
- Está dirigido a ti (`TO: <tu nombre>`)
- Tiene `Status: PENDING` o `IN_PROGRESS`
- No hay un mensaje POSTERIOR del lado opuesto respondiéndolo

Si no hay nada pendiente, díselo al usuario (1-2 líneas: "no hay mensajes nuevos en
inbox_X.md, último mensaje del [fecha] ya respondido") y termina.

## Paso 4 — Procesar y responder

Si hay algo pendiente:

1. **Lee y entiende** lo que pide el mensaje.
2. **Ejecuta** lo necesario (corre comandos, instala deps, lee archivos, etc.).
3. **Recopila resultados**: outputs, errores, hallazgos.
4. **Escribe la respuesta** al final del inbox del OTRO lado:
   - Si eres `wsl-claude` → escribes en `agents/wsl_bridge/inbox_windows.md`
   - Si eres `windows-claude` → escribes en `agents/wsl_bridge/inbox_wsl.md`

   Formato (sigue exactamente el del README):

   ```markdown

   ## [YYYY-MM-DD HH:MM:SS] FROM: <tu nombre> TO: <otro nombre>
   **Status**: DONE   <!-- o FAILED, BLOCKED si hubo problemas -->
   **Re**: <timestamp del mensaje original al que respondes>

   <texto de la respuesta: hallazgos, decisiones, qué se hizo>

   ```bash
   # output literal del comando, si aplica
   ```

   <conclusión + qué espera ver el otro lado / qué sigue>

   --- END ---
   ```

5. **Resume al usuario** lo que respondiste (2-3 líneas, no repitas todo el output).

## Notas

- Usa el comando `date '+%Y-%m-%d %H:%M:%S'` en bash para el timestamp.
- Append-only: jamás borres mensajes anteriores. Solo agregas al final.
- Si el mensaje pide algo que requiere confirmación del usuario (ej: instalar
  paquetes con sudo, modificar config crítica), pregunta primero antes de ejecutar.
- Si el mensaje original está mal formado o no se entiende, responde con `Status: BLOCKED`
  pidiendo aclaración.
