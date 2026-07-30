"""Convierte la pagina 1 del PDF descargado en informe_pdf.png.

Se ejecuta DENTRO del contenedor backend (ahi vive PyMuPDF). Lo invoca
automaticamente docs/tutoriales/img/_capturar.mjs; tambien se puede correr a
mano:

    docker compose -f docker-compose.dev.yml exec -T backend \
        python /app/docs/tutoriales/img/_pdf_a_png.py
"""
from pathlib import Path

import fitz

PDF = Path("/app/data/tmp/_informe_guia.pdf")
PNG = Path("/app/docs/tutoriales/img/informe_pdf.png")

if not PDF.exists():
    raise SystemExit(f"No existe {PDF}. Corre antes _capturar.mjs para descargar el informe.")

doc = fitz.open(PDF)
pix = doc[0].get_pixmap(dpi=150)
pix.save(PNG)
print(f"OK informe_pdf.png ({pix.width}x{pix.height}) desde pagina 1 de {doc.page_count}")
