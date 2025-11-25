export default function Plantillas() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Plantillas</h1>
      <p className="text-neutral-400">
        Aquí puedes configurar tus plantillas.
      </p>

      {/* Lista estática de ejemplo */}
      <ul className="mt-4 space-y-2">
        <li className="rounded-lg border border-neutral-800 bg-neutral-900 p-4">
          Plantilla 1 – Informe Lenguaje Básico
        </li>
        <li className="rounded-lg border border-neutral-800 bg-neutral-900 p-4">
          Plantilla 2 – Informe Matemáticas Avanzado
        </li>
        <li className="rounded-lg border border-neutral-800 bg-neutral-900 p-4">
          Plantilla 3 – Informe Ciencias
        </li>
      </ul>
    </div>
  );
}
