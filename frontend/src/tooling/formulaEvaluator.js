/**
 * formulaEvaluator.js — Evaluador seguro de expresiones aritméticas
 *
 * Soporta: + - * / ( ) números decimales, referencias a campos (_nombre),
 * y funciones whitelisted: round(x), round(x,d), abs(x), min(x,y), max(x,y), sqrt(x)
 *
 * No usa eval(). Parser recursivo descendente.
 * División por cero → null. Campo inexistente → null.
 */

// ── Tokenizer ─────────────────────────────────────────────────────────────────

const TOKEN = {
    NUM:    'NUM',
    IDENT:  'IDENT',
    PLUS:   '+',
    MINUS:  '-',
    STAR:   '*',
    SLASH:  '/',
    LPAREN: '(',
    RPAREN: ')',
    COMMA:  ',',
    EOF:    'EOF',
};

function tokenize(src) {
    const tokens = [];
    let i = 0;
    while (i < src.length) {
        const ch = src[i];
        if (/\s/.test(ch))       { i++; continue; }
        if (/[0-9.]/.test(ch))   {
            let num = '';
            while (i < src.length && /[0-9.]/.test(src[i])) num += src[i++];
            tokens.push({ type: TOKEN.NUM, value: parseFloat(num) });
            continue;
        }
        if (/[a-zA-Z_]/.test(ch)) {
            let id = '';
            while (i < src.length && /[a-zA-Z0-9_]/.test(src[i])) id += src[i++];
            tokens.push({ type: TOKEN.IDENT, value: id });
            continue;
        }
        if (ch === '+') { tokens.push({ type: TOKEN.PLUS  }); i++; continue; }
        if (ch === '-') { tokens.push({ type: TOKEN.MINUS }); i++; continue; }
        if (ch === '*') { tokens.push({ type: TOKEN.STAR  }); i++; continue; }
        if (ch === '/') { tokens.push({ type: TOKEN.SLASH }); i++; continue; }
        if (ch === '(') { tokens.push({ type: TOKEN.LPAREN}); i++; continue; }
        if (ch === ')') { tokens.push({ type: TOKEN.RPAREN}); i++; continue; }
        if (ch === ',') { tokens.push({ type: TOKEN.COMMA }); i++; continue; }
        throw new Error(`Carácter no permitido: ${ch}`);
    }
    tokens.push({ type: TOKEN.EOF });
    return tokens;
}

// ── Parser recursivo ──────────────────────────────────────────────────────────

const WHITELIST_FNS = new Set(['round', 'abs', 'min', 'max', 'sqrt']);

function parse(tokens, record) {
    let pos = 0;

    const peek  = () => tokens[pos];
    const eat   = (t) => {
        if (peek().type !== t) throw new Error(`Esperado ${t}, encontrado ${peek().type}`);
        return tokens[pos++];
    };
    const match = (t) => { if (peek().type === t) { pos++; return true; } return false; };

    // expr → term ((+ | -) term)*
    function expr() {
        let left = term();
        while (peek().type === TOKEN.PLUS || peek().type === TOKEN.MINUS) {
            const op = tokens[pos++].type;
            const right = term();
            if (left === null || right === null) { left = null; continue; }
            left = op === TOKEN.PLUS ? left + right : left - right;
        }
        return left;
    }

    // term → unary ((* | /) unary)*
    function term() {
        let left = unary();
        while (peek().type === TOKEN.STAR || peek().type === TOKEN.SLASH) {
            const op = tokens[pos++].type;
            const right = unary();
            if (left === null || right === null) { left = null; continue; }
            if (op === TOKEN.SLASH) {
                left = right === 0 ? null : left / right;
            } else {
                left = left * right;
            }
        }
        return left;
    }

    // unary → -? primary
    function unary() {
        if (match(TOKEN.MINUS)) {
            const val = primary();
            return val === null ? null : -val;
        }
        return primary();
    }

    // primary → NUM | IDENT | IDENT(...) | ( expr )
    function primary() {
        const tok = peek();

        if (tok.type === TOKEN.NUM) {
            pos++;
            return tok.value;
        }

        if (tok.type === TOKEN.IDENT) {
            pos++;
            const name = tok.value;

            // Function call
            if (peek().type === TOKEN.LPAREN) {
                if (!WHITELIST_FNS.has(name)) throw new Error(`Función no permitida: ${name}`);
                eat(TOKEN.LPAREN);
                const args = [];
                if (peek().type !== TOKEN.RPAREN) {
                    args.push(expr());
                    while (match(TOKEN.COMMA)) args.push(expr());
                }
                eat(TOKEN.RPAREN);
                if (args.some(a => a === null)) return null;
                switch (name) {
                    case 'round': return args.length > 1 ? parseFloat(args[0].toFixed(args[1])) : Math.round(args[0]);
                    case 'abs':   return Math.abs(args[0]);
                    case 'min':   return Math.min(...args);
                    case 'max':   return Math.max(...args);
                    case 'sqrt':  return args[0] < 0 ? null : Math.sqrt(args[0]);
                    default:      return null;
                }
            }

            // Field reference — name as-is or with leading _
            const field = name.startsWith('_') ? name : `_${name}`;
            const val = record[field] ?? record[name];
            if (val === undefined || val === null) return null;
            const num = Number(val);
            return isNaN(num) ? null : num;
        }

        if (tok.type === TOKEN.LPAREN) {
            eat(TOKEN.LPAREN);
            const val = expr();
            eat(TOKEN.RPAREN);
            return val;
        }

        throw new Error(`Token inesperado: ${tok.type}`);
    }

    const result = expr();
    if (peek().type !== TOKEN.EOF) throw new Error('Expresión inválida');
    return result;
}

// ── API pública ───────────────────────────────────────────────────────────────

/**
 * Evalúa una expresión aritmética sobre un record.
 * @param {string} expression   ej. "correctas / total * 100"
 * @param {Object} record       fila de datos con campos _nombre
 * @returns {number|null}       resultado o null si hay error / división por cero
 */
export function evaluate(expression, record) {
    try {
        const tokens = tokenize(expression);
        const result = parse(tokens, record);
        return result === null || isNaN(result) || !isFinite(result) ? null : result;
    } catch {
        return null;
    }
}

/**
 * Aplica una lista de campos derivados a todos los records.
 * @param {Object[]} records          array de filas
 * @param {Object[]} derivedColumns   [{ name, expression }]
 * @returns {Object[]}                nuevos records con los campos derivados añadidos
 */
export function applyDerivedColumns(records, derivedColumns) {
    if (!derivedColumns?.length) return records;
    return records.map(r => {
        const extra = {};
        for (const { name, expression } of derivedColumns) {
            if (!name || !expression) continue;
            const field = name.startsWith('_') ? name : `_${name}`;
            extra[field] = evaluate(expression, r);
        }
        return { ...r, ...extra };
    });
}

/**
 * Valida una expresión con un record de prueba.
 * @returns {{ ok: boolean, error?: string }}
 */
export function validateExpression(expression, sampleRecord = {}) {
    try {
        const tokens = tokenize(expression);
        parse(tokens, sampleRecord);
        return { ok: true };
    } catch (e) {
        return { ok: false, error: e.message };
    }
}
