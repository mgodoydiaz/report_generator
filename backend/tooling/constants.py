import itertools

# Lista de aprox 700 elementos con combinaciones de letras del alfabeto
alfabeto = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
# Se crea una lista con las letras del alfabeto en mayúscula, ['A', 'B', 'C', ..., 'Z', 'AA', 'AB', ...]
indice_alfabetico = []
for i in range(1, 3):  # Hasta 2 letras (puede ajustarse según necesidad)
    for combo in itertools.product(alfabeto, repeat=i):
        indice_alfabetico.append("".join(combo))

# Plantilla genérica de LaTeX para informes
formato_informe_generico = r""" 
\documentclass[11pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[spanish]{babel}
\usepackage[letterpaper,headheight=61pt, bottom=2cm, top=3.5cm, left=2.5cm,right=2.5cm]{geometry}
\usepackage{fancyhdr} %para encabezado y pie de página
\usepackage{tikz} %para imágenes en el encabezado
\usepackage{graphicx} %para imágenes
\usepackage{caption} %para comentarios en tablas e imágenes
\usepackage{multirow} % para las tablas
\usepackage{float} %usar [H]
\usepackage{setspace} %interlineado
\usepackage{fontspec} %para definir fuentes


\input{variables.tex} % archivo con variables

\setmainfont{Segoe UI}[
    BoldFont = Segoe UI Bold,
    ItalicFont = Segoe UI Italic
]
\setlength{\parskip}{5pt}

\pagestyle{fancy}

\lhead{\pgfimage[height=2.0cm]{\leftimage}}
\rhead{\pgfimage[height=2.0cm]{\rightimage}}

\chead{
	\centerheaderone\\
	\centerheadertwo\\
	\centerheaderthree\\
}

\lfoot{\leftfooter}
\cfoot{}
\rfoot{\rightfooter}

\renewcommand{\headrulewidth}{0.4pt}% Default \headrulewidth is 0.4pt
\renewcommand{\footrulewidth}{0.4pt}% Default \footrulewidth is 0pt

\renewcommand{\figurename}{Figura}
\renewcommand{\tablename}{Tabla}

\begin{document}

\thispagestyle{fancy}
\spacing{1.1}

% Se agrega el título
\begin{center}
    \huge{\documenttitle}\\
    \vspace{0.5cm}
    \Large{\schoolname}\\
    \vspace{0.5cm}
\end{center}
"""
