"""
Clase Base para procesos ETL.
Define la interfaz que todas las evaluaciones (SIMCE, Fluidez, etc.) deben respetar.
"""
from abc import ABC, abstractmethod
import pandas as pd
import io

class BaseETL(ABC):
    
    def leer_archivo(self, file_obj, header=0, **kwargs) -> pd.DataFrame:
        """Helper universal para leer Excel/CSV sin repetir código try-except."""
        try:
            # Si es bytes (Streamlit), lo preparamos
            if isinstance(file_obj, bytes):
                file_obj = io.BytesIO(file_obj)
            
            # Intento básico de lectura
            if file_obj.name.endswith('.csv'):
                return pd.read_csv(file_obj, header=header, **kwargs)
            else:
                return pd.read_excel(file_obj, header=header, **kwargs)
        except Exception as e:
            raise ValueError(f"Error leyendo archivo {getattr(file_obj, 'name', 'desconocido')}: {e}")

    @abstractmethod
    def procesar(self, archivos: dict, metadata: dict) -> dict:
        """
        Contrato: Toda clase hija DEBE implementar este método.
        Entrada: Diccionario de archivos.
        Salida: Diccionario con DataFrames listos para reporte.
        """
        pass