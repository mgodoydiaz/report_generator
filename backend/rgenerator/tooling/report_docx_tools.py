from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
from docx2pdf import convert
import os
from pathlib import Path

def render_docx_report(template_path, context, output_path, auto_convert_pdf=True):
    """
    Renderiza una plantilla .docx usando un contexto (diccionario) con docxtpl.
    
    Args:
        template_path (str|Path): Ruta al archivo .docx plantilla.
        context (dict): Diccionario con variables para Jinja2.
        output_path (str|Path): Ruta donde guardar el .docx resultante.
        auto_convert_pdf (bool): Si es True, intenta convertir a PDF usando docx2pdf.
    
    Returns:
        Path: Ruta al archivo generado (.pdf si se convirtió, sino .docx).
    """
    template_path = Path(template_path)
    output_path = Path(output_path)
    
    if not template_path.exists():
        raise FileNotFoundError(f"Plantilla no encontrada: {template_path}")
        
    doc = DocxTemplate(str(template_path))
    
    # Pre-procesamiento de imágenes en el contexto
    # Si hay rutas de imágenes en el contexto, se pueden convertir a InlineImage
    # Asumimos que si una clave termina en '_img' es una ruta de imagen
    processed_context = {}
    for k, v in context.items():
        if isinstance(k, str) and k.endswith('_img') and isinstance(v, (str, Path)):
            if os.path.exists(v):
                # Ancho por defecto 150mm, ajustable
                processed_context[k] = InlineImage(doc, str(v), width=Mm(150))
            else:
                print(f"Advertencia: Imagen no encontrada {v}")
                processed_context[k] = ""
        else:
            processed_context[k] = v
            
    doc.render(processed_context)
    doc.save(output_path)
    
    final_output = output_path
    
    if auto_convert_pdf:
        try:
            # docx2pdf requiere rutas absolutas en windows a veces, o paths string
            pdf_path = output_path.with_suffix(".pdf")
            convert(str(output_path), str(pdf_path))
            final_output = pdf_path
        except Exception as e:
            print(f"Error convirtiendo a PDF: {e}. Se conserva el .docx.")
            
    return final_output

def generate_sample_context():
    """Retorna un contexto de ejemplo para probar la plantilla."""
    return {
        "nombre_establecimiento": "Colegio Ejemplo",
        "asignatura": "Matemáticas",
        "fecha": "29 de Enero, 2026",
        "tablas": [
            {"col1": "Dato 1", "col2": 10},
            {"col1": "Dato 2", "col2": 20},
            {"col1": "Total", "col2": 30},
        ],
        "mostrar_seccion_extra": True
    }
