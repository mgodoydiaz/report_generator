
import json


def cargar_config_desde_txt(ruta_txt: str) -> dict:
    """
    Lee un archivo .txt tipo:
        tipo_etl = estudiantes
        directorio_archivos = simce/lectura
        mes = Marzo
        numero_prueba = 1
        asignatura = Lenguaje
        columnas_relevantes = RBD,Curso,Letra,Run,Nombre,Puntaje,Nivel
        nombre_salida = resultados_estudiantes_simce.xlsx
    Retorna un dict con las claves y valores.
    """
    config = {}
    with open(ruta_txt, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            if "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            config[clave.strip()] = valor.strip()
    return config

def cargar_config_desde_json(ruta_json: str) -> dict:
    """
    Lee un archivo .json y retorna un dict con las claves y valores.
    """
    with open(ruta_json, encoding="utf-8") as f:
        return json.load(f)

def parsear_lista_desde_config(config: dict, clave: str) -> list:
    """
    Convierte una línea "a,b,c" en ["a", "b", "c"].
    """
    valor = config.get(clave, "")
    if not valor:
        return []
    return [item.strip() for item in valor.split(",")]
