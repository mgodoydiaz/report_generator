# -*- coding: utf-8 -*-
"""Genera el tutorial en Word usando la plantilla de Miguel."""
import sys
from pathlib import Path

SKILL = Path(r"C:\Users\magod\.claude\skills\plantilla-miguel")
sys.path.insert(0, str(SKILL / "scripts"))
from plantilla import Doc  # noqa: E402

PNG = Path(r"C:\Users\magod\AppData\Local\Temp\claude\--wsl-localhost-ubuntu-home-atlas-proyectos-report-generator\1768a28f-63eb-4b7a-a953-dc24ee9c53b9\scratchpad\png")
SALIDA = Path(r"C:\Users\magod\Desktop\SIMCE Panguipulli - Aptus\Tutorial - Descargar informes desde Aptus.docx")
ANCHO = 6.0

d = Doc()
d.headers(lhead="Report Generator", rhead="SIMCE Panguipulli",
          lfoot="Fundación PHP", cfoot="Guía de carga")

d.title("Cómo descargar los informes de SIMCE Panguipulli desde Aptus",
        "Guía de carga · agosto 2026")

d.body("Los ensayos SIMCE que aplica Aptus en Panguipulli. Esta guía muestra exactamente "
       "cuáles son los dos archivos que hay que bajar, de qué pantalla salen y qué hacer "
       "con ellos después.")

d.destacado(1, "Son dos archivos Excel: logros por Estudiante y logros por Habilidad. "
               "Los dos salen de la misma pantalla, de un panel plegado que dice «Informes».")
d.destacado(2, "Un archivo por mes alcanza. Cada Excel ya trae todos los cursos y todas las "
               "asignaturas de ese mes, así que no hay que repetir la descarga.")

# ---------------------------------------------------------------- 1
d.h1("Entrar a Aptus")
d.body("Anda a web.aptus.org e inicia sesión. Necesitas una cuenta con acceso a los "
       "resultados del establecimiento; si no ves la opción del paso 2, es que tu cuenta "
       "no tiene ese permiso.")

# ---------------------------------------------------------------- 2
d.h1("Abrir «Ver Resultados»")
d.body("En el menú azul de arriba, entra a Recursos Pedagógicos y elige Ver Resultados, "
       "la última opción de la lista.")
d.image(str(PNG / "pantalla_1.png"), width_in=ANCHO,
        caption="El menú superior desplegado. «Ver Resultados» es la última opción.")

# ---------------------------------------------------------------- 3
d.h1("Elegir el año y el colegio")
d.body("Arriba hay cuatro filtros, pero solo dos importan: Periodo, que es el año de la "
       "evaluación, y Colegio. Los otros dos dicen «no es obligatorio» y así se quedan.")
d.image(str(PNG / "pantalla_2.png"), width_in=ANCHO,
        caption="Se llenan Periodo y Colegio; Proyectos y Sostenedor quedan en blanco.")

# ---------------------------------------------------------------- 4
d.h1("Elegir EMN y el mes")
d.body("En la columna de la izquierda, deja marcado Evaluaciones (no Seguimiento). Abajo "
       "aparecen dos selectores que sí importan: Tipo de proceso, donde eliges EMN, y "
       "Proceso, donde eliges el mes.")
d.body("Aptus escribe los meses de forma despareja — «EMN Abril» y «EMN Mayo» con "
       "mayúscula, «EMN agosto» con minúscula. Es normal, no es un error.")
d.image(str(PNG / "pantalla_3.png"), width_in=ANCHO,
        caption="La columna izquierda con «EMN» y el mes elegido. Nivel y Asignatura pueden quedar como estén.")
d.destacado(2, "Nivel y Asignatura no cambian los Excel. Aunque filtres por un curso o por "
               "una asignatura, el archivo que baja Aptus trae siempre el mes completo: "
               "todos los niveles y todas las asignaturas. Esos filtros solo cambian la "
               "tabla que se ve en pantalla.")

# ---------------------------------------------------------------- 5
d.h1("Abrir «Informes» y bajar los dos Excel")
d.body("Sobre la tabla de resultados hay una barra gris plegada que dice Informes. Hazle "
       "clic para desplegarla: aparecen cuatro enlaces, pero solo dos son los que "
       "necesitas, por Estudiante y por Habilidad. Los otros dos —el PDF de comparación y "
       "el informe por OA— no se usan.")
d.image(str(PNG / "pantalla_4.png"), width_in=ANCHO,
        caption="El panel «Informes» desplegado. Los dos enlaces marcados son los que hay que descargar.")

# ---------------------------------------------------------------- 6
d.h1("Ponerle el mes al nombre")
d.body("Aptus entrega los archivos con la fecha en que los bajaste y sin el mes, así que "
       "descargas de meses distintos se ven casi iguales. Renómbralos apenas los bajes:")
d.table(["Como lo entrega Aptus", "Cómo conviene dejarlo"],
        [["Informe_logro_por_estudiante (04-05-2026).xlsx", "Informe_logro_por_estudiante MAYO.xlsx"],
         ["Informe_logro_por_habilidad (04-05-2026).xlsx",  "Informe_logro_por_habilidad MAYO.xlsx"]])
d.destacado(3, "El nombre es solo para ti. El sistema no lee el mes del nombre del archivo "
               "— lo saca de una columna de adentro. Renombrar es para que no te equivoques "
               "al subirlos, no un requisito técnico.")

# ---------------------------------------------------------------- 7
d.h1("Subirlos al sistema")
d.body("En Report Generator, anda a Ejecución y abre el proceso «SIMCE Panguipulli "
       "(Aptus)». No te va a preguntar ningún dato: el mes, el curso y la asignatura los "
       "saca de los propios archivos. Se detiene dos veces, una por archivo:")
d.table(["Pausa", "Qué dice el recuadro", "Qué archivo va"],
        [["1ª", "Informe de logros por Estudiante", "Informe_logro_por_estudiante"],
         ["2ª", "Informe de logros por Habilidad", "Informe_logro_por_habilidad"]])
d.destacado(3, "Un mes por ejecución, y nunca dos veces el mismo. Si tienes que cargar abril "
               "y mayo, corre el proceso dos veces. La carga suma, no reemplaza: si repites "
               "un mes ya cargado, sus datos quedan duplicados y los promedios salen mal. "
               "Revisa en Valores antes de volver a ejecutar.")

# ---------------------------------------------------------------- 8
d.h1("Qué no hacerle a los archivos")
for t in [
    "No cambies los títulos de las columnas. Vienen en mayúsculas (NOMBRE PROCESO, AÑO, "
    "NIVEL, CURSO, ASIGNATURA, PORCENTAJE LOGRO…) y el sistema los busca tal cual, con "
    "tildes incluidas.",
    "No toques la columna NOMBRE PROCESO. De ahí sale el mes: el sistema lee «EMN Mayo» y "
    "guarda MAYO. Si la editas, el mes se pierde.",
    "No arregles los decimales a mano. Vienen con coma (0,444444) y el sistema los convierte solo.",
    "No abras y vuelvas a guardar el archivo «para ordenarlo». Súbelo tal como lo bajaste.",
]:
    d.doc.add_paragraph("•  " + t, style="List Paragraph")

# ---------------------------------------------------------------- 9
d.h1("Antes de cerrar, revisa")
for t in [
    "Bajé los dos Excel del mes: Estudiante y Habilidad.",
    "Cada archivo tiene el mes en el nombre.",
    "El mes que voy a cargar no estaba cargado ya.",
    "Después de cargar, en Valores aparecen el año y el mes nuevos.",
    "En el dashboard del indicador, el mes nuevo se ve en la pestaña de tendencia.",
]:
    d.doc.add_paragraph("•  " + t, style="List Paragraph")

d.body("")
d.destacado(2, "Las pantallas de esta guía son reproducciones dibujadas, no capturas: la "
               "pantalla real muestra nombres y RUT de estudiantes. Los textos y los nombres "
               "de los enlaces sí son los reales, verificados en agosto de 2026. Si Aptus "
               "cambia su interfaz, manda lo que veas en pantalla.")

SALIDA.parent.mkdir(parents=True, exist_ok=True)
d.save(str(SALIDA))
print("generado:", SALIDA, SALIDA.stat().st_size, "bytes")
