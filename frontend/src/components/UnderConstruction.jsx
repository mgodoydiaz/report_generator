import React from 'react';
import { Hammer, HardHat, Construction } from 'lucide-react';

const UnderConstruction = ({ title, icon: Icon }) => {
    return (
        <div className="max-w-4xl mx-auto py-20 px-6">
            <div className="bg-white rounded-[40px] shadow-2xl shadow-slate-200/50 border border-slate-100 overflow-hidden relative">
                {/* Decoración superior */}
                <div className="h-2 bg-amber-400 w-full" />

                <div className="p-12 flex flex-col items-center text-center space-y-8">
                    <div className="relative">
                        <div className="w-24 h-24 bg-amber-50 rounded-3xl flex items-center justify-center text-amber-500 animate-bounce">
                            {Icon ? <Icon size={48} /> : <Construction size={48} />}
                        </div>
                        <div className="absolute -bottom-2 -right-2 bg-white p-2 rounded-full shadow-lg">
                            <Hammer size={20} className="text-slate-400" />
                        </div>
                    </div>

                    <div className="space-y-3">
                        <h1 className="text-4xl font-black text-slate-900 tracking-tight">{title}</h1>
                        <p className="text-slate-500 text-lg font-medium max-w-md mx-auto">
                            Estamos trabajando intensamente para traerte las mejores herramientas de gestión. ¡Vuelve pronto!
                        </p>
                    </div>

                    <div className="flex gap-4">
                        <div className="flex items-center gap-2 px-4 py-2 bg-slate-50 rounded-full text-slate-500 text-sm font-bold border border-slate-100">
                            <HardHat size={16} />
                            En progreso
                        </div>
                    </div>
                </div>

                {/* Patrón de líneas decorativas */}
                <div className="absolute bottom-0 left-0 w-full h-1 bg-linear-to-r from-amber-400 via-slate-900 to-amber-400 repeating-linear-gradient"
                    style={{ backgroundImage: 'repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(0,0,0,0.1) 10px, rgba(0,0,0,0.1) 20px)' }} />
            </div>
        </div>
    );
};

export default UnderConstruction;
