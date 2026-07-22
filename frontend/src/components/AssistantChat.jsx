import React, { useState, useRef, useEffect } from 'react';
import { X, Send, Sparkles, Loader2 } from 'lucide-react';
import { API_BASE_URL } from '../constants';
import { useAuth } from '../context/AuthContext';

/**
 * Drawer de chat con el asistente de configuración de indicadores.
 * Backend: POST /api/assistant/chat (proveedor mock o Claude según env del server).
 * Si `indicator` viene, el asistente recibe su configuración como contexto.
 */
export default function AssistantChat({ isOpen, onClose, indicator }) {
    const { fetchAuth } = useAuth();
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [sending, setSending] = useState(false);
    const bottomRef = useRef(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, sending]);

    useEffect(() => {
        // Nueva conversación al cambiar de indicador
        setMessages([]);
    }, [indicator?.id_indicator]);

    if (!isOpen) return null;

    const handleSend = async (e) => {
        e?.preventDefault();
        const text = input.trim();
        if (!text || sending) return;

        const nextMessages = [...messages, { role: 'user', content: text }];
        setMessages(nextMessages);
        setInput('');
        setSending(true);
        try {
            const resp = await fetchAuth(`${API_BASE_URL}/assistant/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    messages: nextMessages,
                    indicator_id: indicator?.id_indicator ?? null,
                }),
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.detail || 'Error del asistente');
            setMessages(prev => [...prev, { role: 'assistant', content: data.reply }]);
        } catch (err) {
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: `⚠️ ${err.message || 'No se pudo contactar al asistente.'}`,
            }]);
        } finally {
            setSending(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex justify-end">
            <div className="absolute inset-0 bg-slate-900/30 backdrop-blur-sm" onClick={onClose} />
            <div className="relative w-full max-w-md h-full bg-white dark:bg-slate-900 shadow-2xl flex flex-col">
                <div className="flex items-center justify-between p-5 border-b border-slate-100 dark:border-slate-800">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-indigo-50 dark:bg-indigo-900/30 rounded-xl">
                            <Sparkles size={18} className="text-indigo-600 dark:text-indigo-400" />
                        </div>
                        <div>
                            <h3 className="font-bold text-slate-800 dark:text-slate-100 text-sm">Asistente de indicadores</h3>
                            {indicator && (
                                <p className="text-xs text-slate-400">Contexto: {indicator.name}</p>
                            )}
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-50 dark:hover:bg-slate-800 rounded-xl transition-all">
                        <X size={18} />
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-5 space-y-4">
                    {messages.length === 0 && (
                        <div className="text-sm text-slate-400 space-y-3">
                            <p>Puedo ayudarte a configurar {indicator ? `“${indicator.name}”` : 'tus indicadores'}:</p>
                            <ul className="list-disc list-inside space-y-1">
                                <li>Niveles de logro y colores</li>
                                <li>Layout del dashboard (tabs, gráficos, tablas)</li>
                                <li>Filtros por dimensión</li>
                                <li>Columnas calculadas (avance, delta, promedios)</li>
                            </ul>
                        </div>
                    )}
                    {messages.map((m, i) => (
                        <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`max-w-[85%] px-4 py-3 rounded-2xl text-sm whitespace-pre-wrap ${
                                m.role === 'user'
                                    ? 'bg-indigo-600 text-white rounded-br-md'
                                    : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 rounded-bl-md'
                            }`}>
                                {m.content}
                            </div>
                        </div>
                    ))}
                    {sending && (
                        <div className="flex justify-start">
                            <div className="px-4 py-3 rounded-2xl bg-slate-100 dark:bg-slate-800">
                                <Loader2 size={16} className="animate-spin text-slate-400" />
                            </div>
                        </div>
                    )}
                    <div ref={bottomRef} />
                </div>

                <form onSubmit={handleSend} className="p-4 border-t border-slate-100 dark:border-slate-800 flex gap-2">
                    <input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Escribe tu pregunta…"
                        className="flex-1 px-4 py-3 bg-slate-50 dark:bg-slate-800 rounded-xl text-sm text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-indigo-200"
                    />
                    <button
                        type="submit"
                        disabled={sending || !input.trim()}
                        className="p-3 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white rounded-xl transition-all active:scale-95"
                    >
                        <Send size={16} />
                    </button>
                </form>
            </div>
        </div>
    );
}
