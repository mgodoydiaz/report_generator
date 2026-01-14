import pandas as pd
import numpy as np
from .base import BaseETL

class CalculoVelozETL(BaseETL):
    def __init__(self):
        # Columnas objetivo según tu formato recomendado
        self.columnas_finales = [
            "Curso", "Mes", "N Evaluación", "Fecha", 
            "Rut", "Nombre", "Apellido", "Puntaje", "Nota"
        ]

    def procesar(self, archivos: dict, metadata: dict) -> dict:
        """
        Procesa el Excel crudo de los profesores y devuelve el formato limpio.
        metadata debe incluir: {'mes': 'Abril', 'n_evaluacion': 1, 'fecha': '2025-04-16'}
        """
        if 'input_profesor' not in archivos:
            raise ValueError("Falta archivo de entrada (input_profesor)")

        # Leemos todas las hojas del Excel (I°, II°, etc.)
        # Asumimos que 'archivos['input_profesor']' es el BytesIO del excel sucio
        xls = pd.ExcelFile(archivos['input_profesor'])
        
        dfs_consolidados = []

        for nombre_hoja in xls.sheet_names:
            # Filtramos hojas ocultas o de sistema si las hubiera
            if nombre_hoja.startswith("_"): continue

            # 1. Leer hoja
            df = pd.read_excel(xls, sheet_name=nombre_hoja)
            
            # 2. Normalización básica (Renombrar a estándar)
            # Aquí mapeamos las columnas del "Excel sucio" a tus columnas destino
            # Ajusta 'NombreAlumno' etc. según como venga el excel real
            column_map = {
                'RUT': 'Rut', 
                'Nombres': 'Nombre', 
                'Apellidos': 'Apellido',
                'Puntaje': 'Puntaje'
            }
            df = df.rename(columns=column_map)

            # 3. Inyectar Metadata (Curso, Mes, Fecha)
            df['Curso'] = nombre_hoja  # Usamos el nombre de la hoja como Curso (ej: "I°A")
            df['Mes'] = metadata.get('mes')
            df['N Evaluación'] = metadata.get('n_evaluacion')
            df['Fecha'] = metadata.get('fecha')

            # 4. Calcular Nota
            # Usamos los parámetros que subiste en CV Parámetros.csv
            df['Nota'] = df['Puntaje'].apply(self._calcular_nota)

            # 5. Seleccionar solo columnas del formato final
            # Aseguramos que existan todas, si no, se llenan con vacío
            for col in self.columnas_finales:
                if col not in df.columns:
                    df[col] = ""
            
            dfs_consolidados.append(df[self.columnas_finales])

        # Unimos todo en un gran DataFrame maestro
        df_final = pd.concat(dfs_consolidados, ignore_index=True)
        return {"calculo_veloz_formateado": df_final}

    def _calcular_nota(self, puntaje):
        """
        Calcula la nota basada en las rectas de 'CV Parámetros.csv'.
        Rango 0 (0-59): m=0.01666..., b=1
        Rango 60 (60-100): m=0.075, b=-0.5
        """
        try:
            p = float(puntaje)
            if p < 60:
                # Recta para bajo rendimiento (Exigencia 60%)
                nota = (p * 0.016666667) + 1
            else:
                # Recta para sobre exigencia
                nota = (p * 0.075) - 0.5
            
            # Redondear a 1 decimal
            return round(nota, 1)
        except:
            return 0.0