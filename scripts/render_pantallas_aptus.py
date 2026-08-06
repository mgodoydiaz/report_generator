# -*- coding: utf-8 -*-
"""Extrae las reproducciones de pantalla del tutorial HTML y las convierte en PNG,
para poder incrustarlas en el .docx. Cada bloque .tut-screen se renderiza solo,
con el mismo CSS, y se recorta el blanco sobrante.
"""
import re
import subprocess
import sys
from pathlib import Path

import fitz  # PyMuPDF

BASE = Path("/mnt/c/Users/magod/AppData/Local/Temp/claude/--wsl-localhost-ubuntu-home-atlas-proyectos-report-generator/1768a28f-63eb-4b7a-a953-dc24ee9c53b9/scratchpad")
SRC = BASE / "tutorial_aptus_body.html"
OUT = BASE / "png"
OUT.mkdir(exist_ok=True)

html = SRC.read_text(encoding="utf-8")
estilo = re.search(r"<style>.*?</style>", html, re.S).group(0)

# cada figura: el bloque .tut-screen + su pie
figuras = re.findall(
    r'<div class="tut-figure">\s*(<div class="tut-screen">.*?</div>)\s*<p class="tut-caption">(.*?)</p>',
    html, re.S)
print(f"figuras encontradas: {len(figuras)}")

def recortar(pix):
    """Devuelve (x0,y0,x1,y1) del contenido no blanco."""
    w, h, n = pix.width, pix.height, pix.n
    data = pix.samples
    x0, y0, x1, y1 = w, h, 0, 0
    for y in range(h):
        fila = y * w * n
        for x in range(w):
            i = fila + x * n
            if data[i] < 246 or data[i+1] < 246 or data[i+2] < 246:
                if x < x0: x0 = x
                if x > x1: x1 = x
                if y < y0: y0 = y
                if y > y1: y1 = y
    return x0, y0, x1, y1

rutas = []
for i, (screen, pie) in enumerate(figuras, 1):
    doc = f"""<!doctype html><html lang="es"><head><meta charset="utf-8">{estilo}
<style>@page {{ size: 260mm 300mm; margin: 5mm; }} body {{ margin:0 }}
 .tut {{ padding:0; background:#fff; }}</style></head>
<body><article class="tut"><div class="tut-col-wide">{screen}</div></article></body></html>"""
    tmp_html = BASE / f"_fig{i}.html"
    tmp_pdf = BASE / f"_fig{i}.pdf"
    tmp_html.write_text(doc, encoding="utf-8")
    subprocess.run([sys.executable, "-m", "weasyprint", str(tmp_html), str(tmp_pdf)],
                   check=True, capture_output=True)
    d = fitz.open(tmp_pdf)
    pix = d[0].get_pixmap(dpi=190)
    x0, y0, x1, y1 = recortar(pix)
    m = 6
    clip = fitz.Rect(max(0, x0-m), max(0, y0-m), min(pix.width, x1+m), min(pix.height, y1+m))
    clip = clip * (72/190)  # de px a puntos
    pix2 = d[0].get_pixmap(dpi=190, clip=clip)
    ruta = OUT / f"pantalla_{i}.png"
    pix2.save(ruta)
    d.close()
    tmp_html.unlink(); tmp_pdf.unlink()
    pie_txt = re.sub(r"<[^>]+>", "", pie).strip()
    rutas.append((str(ruta), pie_txt))
    print(f"  {ruta.name}  {pix2.width}x{pix2.height}px  | {pie_txt[:60]}")

(BASE / "pantallas.txt").write_text(
    "\n".join(f"{r}\t{p}" for r, p in rutas), encoding="utf-8")
print("\nlistado en pantallas.txt")
