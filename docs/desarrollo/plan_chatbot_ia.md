# Plan — Chatbot IA integrado (ruta /chat)

**Fecha**: 2026-08-07 · **Estado**: propuesta, sin implementar
**Objetivo**: asistente conversacional dentro del SaaS, conectado a la API de Claude, que ayude al usuario a (a) cargar y revisar archivos, (b) configurar indicadores, y (c) comunicarse con el administrador.

## 1. Casos de uso concretos

1. **Carga de archivos**: "quiero subir el DIA de marzo" → el bot identifica el pipeline correcto, explica qué archivos espera (roles, formato, columnas), valida el archivo subido contra el spec ANTES de ejecutar, y explica en lenguaje simple los errores (`NEEDS_REVIEW`, columnas faltantes, hoja incorrecta).
2. **Revisión post-carga**: "¿quedó bien la carga de ayer?" → consulta conteos de la ejecución, filas insertadas por métrica, advertencias del log (ej. el guard de cobertura 0%).
3. **Configurar indicadores**: "agrega el nivel 'Destacado' color verde al indicador IDEL" → el bot arma la propuesta de cambio y la muestra como borrador; el usuario confirma con un botón (nunca escribe directo).
4. **Contacto con admin**: "necesito que me carguen el año 2024" → crea un mensaje/ticket para el admin de la org con el contexto de la conversación adjunto.

## 2. Arquitectura

```
frontend /chat (React) ── SSE ──> backend /api/chat (FastAPI router nuevo)
                                     │  historial en DB (chat_sessions, chat_messages)
                                     │  Anthropic SDK Python (streaming + tool use)
                                     ▼
                              Claude API (tool loop server-side nuestro)
                                     │ tools org-scoped (siempre con org_id + rol del JWT)
                                     ▼
                              SQLAlchemy / servicios existentes
```

- **Backend**: router `backend/routers/chat.py`. Endpoint `POST /api/chat/{session_id}/message` con respuesta SSE (streaming de texto + eventos de tool). El loop de tools corre en el backend (patrón manual o tool runner del SDK `anthropic`); el frontend solo ve texto y "tarjetas de confirmación".
- **Modelo**: `claude-opus-5` (recomendación vigente de Anthropic; thinking adaptativo por defecto) con `output_config={"effort": "low"}` para chat interactivo — latencia y costo bajos con calidad sobrada para este dominio. Configurable por env var `CHAT_MODEL`.
- **Prompt caching**: system prompt estable por org (contexto de la fundación, indicadores, glosario IDEL/DIA) con `cache_control` — el costo por turno cae ~90% en conversaciones largas. Estado volátil (rol del usuario, página actual) va al final, no al system.
- **API key**: `ANTHROPIC_API_KEY` como variable de entorno del backend (Railway → Variables), **nunca** expuesta al frontend ni almacenada en DB en texto plano. Fase posterior opcional: key por org en `org_settings` cifrada (Fernet) para facturación separada.

## 3. Tools (todas org-scoped, el JWT manda)

| Tool | Tipo | Descripción |
|---|---|---|
| `listar_pipelines` | lectura | Pipelines disponibles de la org con qué archivos esperan |
| `validar_archivo` | lectura | Valida un upload contra el spec del pipeline (columnas, hojas, tipos) sin ejecutar |
| `estado_ejecucion` | lectura | Estado/logs/conteos de una ejecución (RUNNING/NEEDS_REVIEW/DONE/FAILED) |
| `resumen_carga` | lectura | Filas por métrica/curso de una carga reciente + advertencias |
| `get_indicador` | lectura | Config de un indicador (niveles, colores, dimensiones) |
| `proponer_cambio_indicador` | **borrador** | Devuelve un diff estructurado; la UI lo muestra como tarjeta con botón Confirmar. El write real ocurre en un endpoint clásico tras el clic — el modelo nunca escribe directo |
| `enviar_mensaje_admin` | **borrador** | Igual: el bot redacta, el usuario confirma el envío |

Regla dura: **el modelo jamás ejecuta un write**. Los tools de escritura producen borradores que viajan como JSON estructurado (structured outputs / `strict: true`) y el commit es un clic humano sobre un endpoint normal con la autorización de siempre. Esto neutraliza prompt injection vía archivos subidos.

## 4. Seguridad y límites

- Cada tool recibe `org_id` y rol desde el JWT del request, no desde el modelo. Viewer: solo tools de lectura. Editor/Admin: además borradores.
- Rate limit por usuario (ej. 30 mensajes/hora) y tope de tokens por conversación.
- Historial persistido en `chat_sessions` / `chat_messages` (org_id, user_id, role, content, tool_calls_json) — auditable y reutilizable como contexto.
- Contenido de archivos subidos = **dato no confiable**: se pasa al modelo como datos a analizar, y las instrucciones que contenga no se ejecutan (el system prompt lo declara y los writes ya están gateados por diseño).
- PII de estudiantes: los tools devuelven agregados donde sea posible; nombres individuales solo cuando el caso de uso lo exige (validación de archivo).

## 5. Fases

| Fase | Contenido | Estimación |
|---|---|---|
| F0 | Página `/chat` (ruta + sidebar + UI de burbujas) con backend echo (sin IA aún) — valida UX y navegación | 1 agente (~150k) |
| F1 | Conexión a Claude: router SSE + system prompt org + historial en DB + tools de lectura (`listar_pipelines`, `estado_ejecucion`, `resumen_carga`, `get_indicador`) | 2 agentes (~450k) |
| F2 | `validar_archivo`: upload dentro del chat + validación contra spec + explicación de errores | 1 agente (~250k) |
| F3 | Borradores con confirmación: `proponer_cambio_indicador` + tarjetas Confirmar/Rechazar + endpoint de commit | 2 agentes (~400k) |
| F4 | `enviar_mensaje_admin` + bandeja del admin + notificación por correo | 1 agente (~250k) |

## 6. Costos de operación (orden de magnitud)

Con Opus 5 ($5/$25 por MTok), system prompt cacheado y effort low: una conversación típica de 10 turnos con 2-3 tool calls ≈ 30-60k tokens in (mayoría cache read a ~0.1×) + 5-10k out ≈ **US$0.15-0.35 por conversación**. Con volumen real conviene medir y evaluar `claude-haiku-4-5` para los turnos triviales.

## 7. Decisiones abiertas para Miguel

1. ¿Key global de la fundación (simple, F1) o key por org (facturación separada, más adelante)?
2. ¿El chat ve datos de estudiantes individuales o solo agregados? (impacta `validar_archivo`)
3. ¿F0 ahora como stub navegable o partir directo en F1?
