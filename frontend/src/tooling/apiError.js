/**
 * Helpers de error para respuestas de la API.
 *
 * Motivo: FastAPI devuelve los errores como {"detail": ...}, nunca como
 * {"error": ...}. El código antiguo comprobaba `result.error`, condición que
 * jamás se cumple, así que un 403/401/400/500 pasaba de largo y la UI mostraba
 * "guardado" sin haber guardado nada. Aquí la regla es una sola:
 * **`!response.ok` siempre es fallo**.
 *
 * Uso típico en una escritura:
 *
 *     const res = await fetchAuth(url, { method: 'POST', body });
 *     await lanzarSiFalla(res);          // lanza con mensaje legible si falló
 *     const result = await res.json();   // solo se llega aquí si res.ok
 *
 * `lanzarSiFalla` solo consume el cuerpo cuando la respuesta NO es ok, así que
 * el camino feliz puede seguir leyendo el JSON como siempre.
 *
 * El 401 no cierra sesión aquí: de eso ya se encarga `fetchAuth`
 * (context/AuthContext.jsx), que llama a logout() al ver un 401.
 */

/** Mensajes por código HTTP, usados cuando el cuerpo no trae nada legible. */
const MENSAJES_POR_CODIGO = {
    400: 'La solicitud no es válida.',
    401: 'Tu sesión expiró. Vuelve a iniciar sesión.',
    403: 'No tienes permisos para realizar esta acción. Tu usuario es de solo lectura.',
    404: 'No se encontró el recurso solicitado.',
    405: 'Operación no permitida.',
    409: 'El recurso ya existe o está en conflicto con otro.',
    413: 'El archivo enviado es demasiado grande.',
    422: 'Hay datos inválidos en el formulario.',
    429: 'Demasiadas solicitudes seguidas. Espera un momento e inténtalo de nuevo.',
    500: 'Error interno del servidor.',
    502: 'El servidor no está disponible en este momento.',
    503: 'El servicio no está disponible en este momento.',
    504: 'El servidor tardó demasiado en responder.',
};

const MENSAJE_GENERICO = 'Ocurrió un error inesperado.';

/** Códigos cuyo mensaje es siempre el nuestro: el detalle del backend no aporta. */
const CODIGOS_CON_MENSAJE_PROPIO = [401, 403];

/** Largo máximo de un mensaje tomado del cuerpo (evita volcar un HTML entero). */
const LARGO_MAXIMO = 300;

/** Segmentos de `loc` que no son el nombre del campo en un 422 de FastAPI. */
const LOC_IGNORADA = ['body', 'query', 'path', 'header', 'cookie'];

/**
 * Resume la lista `detail` de un 422 de FastAPI en texto legible.
 * Cada entrada es {loc: [...], msg: "...", type: "..."}; devolvemos
 * "campo: mensaje" y cortamos a 3 para no llenar el toast.
 */
function resumirErroresValidacion(detalles) {
    const partes = detalles
        .map((d) => {
            if (typeof d === 'string') return d.trim() || null;
            if (!d || typeof d !== 'object') return null;
            const campo = Array.isArray(d.loc)
                ? d.loc.filter((p) => typeof p === 'string' && !LOC_IGNORADA.includes(p)).pop()
                : null;
            const msg = typeof d.msg === 'string'
                ? d.msg
                : (typeof d.message === 'string' ? d.message : null);
            if (campo && msg) return `${campo}: ${msg}`;
            return msg || campo || null;
        })
        .filter(Boolean);

    if (partes.length === 0) return null;
    const visibles = partes.slice(0, 3).join('; ');
    return partes.length > 3 ? `${visibles} (y ${partes.length - 3} más)` : visibles;
}

/**
 * Extrae un mensaje de un cuerpo ya parseado (`detail` string, `detail` lista
 * de errores de validación, o `error`/`message`/`msg`).
 * Devuelve null si no hay nada usable — nunca "[object Object]".
 */
export function mensajeDesdeCuerpo(cuerpo) {
    if (typeof cuerpo === 'string') {
        const texto = cuerpo.trim();
        return texto || null;
    }
    if (!cuerpo || typeof cuerpo !== 'object') return null;

    const { detail } = cuerpo;
    if (typeof detail === 'string' && detail.trim()) return detail.trim();
    if (Array.isArray(detail)) {
        const resumen = resumirErroresValidacion(detail);
        if (resumen) return resumen;
    } else if (detail && typeof detail === 'object') {
        // Algunos handlers anidan {detail: {message: "..."}}
        const anidado = mensajeDesdeCuerpo(detail);
        if (anidado) return anidado;
    }

    for (const clave of ['error', 'message', 'msg']) {
        const valor = cuerpo[clave];
        if (typeof valor === 'string' && valor.trim()) return valor.trim();
    }
    return null;
}

/** Mensaje de fallback a partir del código HTTP. */
export function mensajePorCodigo(status) {
    if (MENSAJES_POR_CODIGO[status]) return MENSAJES_POR_CODIGO[status];
    return status ? `${MENSAJE_GENERICO} (HTTP ${status})` : MENSAJE_GENERICO;
}

/**
 * Construye el mensaje de error de una respuesta fallida.
 * Consume el cuerpo de `response`, así que solo debe llamarse cuando !ok.
 * Nunca lanza.
 */
export async function mensajeDeError(response) {
    if (!response) return MENSAJE_GENERICO;
    const status = response.status;

    if (CODIGOS_CON_MENSAJE_PROPIO.includes(status)) return MENSAJES_POR_CODIGO[status];

    let cuerpo = null;
    try {
        const texto = await response.text();
        const limpio = (texto || '').trim();
        if (limpio) {
            try {
                cuerpo = JSON.parse(limpio);
            } catch {
                // No es JSON: solo lo aceptamos si no parece una página HTML
                cuerpo = limpio.startsWith('<') ? null : limpio;
            }
        }
    } catch {
        cuerpo = null;
    }

    const mensaje = mensajeDesdeCuerpo(cuerpo);
    if (mensaje && mensaje.length <= LARGO_MAXIMO) return mensaje;
    return mensajePorCodigo(status);
}

/**
 * Lanza un Error con mensaje legible si la respuesta no es ok.
 * Si es ok no toca el cuerpo, para que el llamador siga con `response.json()`
 * exactamente como antes. El Error lleva `.status` con el código HTTP.
 */
export async function lanzarSiFalla(response) {
    if (response && response.ok) return response;
    const error = new Error(await mensajeDeError(response));
    error.status = response ? response.status : 0;
    throw error;
}
