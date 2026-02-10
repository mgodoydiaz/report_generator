import json
from typing import Any, Dict, Union

def safe_json_to_text(data: Any) -> str:
    """
    Transforma un objeto, lista o diccionario a texto JSON formateado.
    Si ocurre un error, retorna la representación en cadena del objeto.
    """
    try:
        if data is None:
            return ""
        return json.dumps(data, indent=4, ensure_ascii=False)
    except Exception:
        return str(data)

def safe_text_to_json(text: str) -> Union[Dict, list]:
    """
    Transforma texto JSON a un objeto Python (dict o list).
    Si el texto es inválido o está vacío, retorna un diccionario vacío o con el error.
    """
    if not text or not isinstance(text, str):
        return {}
    
    text = text.strip()
    if not text:
        return {}
        
    try:
        return json.loads(text)
    except Exception:
        return {"error": "Invalid JSON format", "raw": text}

def get_json_safe_df(df: Any) -> Any:
    """
    Recibe un DataFrame de Pandas y retorna uno seguro para serializar a JSON.
    Reemplaza NaN, Infinity y -Infinity por None.
    Itera columna por columna para mayor seguridad con tipos mixtos.
    """
    try:
        import pandas as pd
        if df is None or df.empty:
            return df

        # Iterar columnas para reemplazar NaN/Inf de forma segura
        for col in df.columns:
            # Convertir a object para permitir None
            df[col] = df[col].astype(object)
            
            def clean_val(x):
                try:
                    if pd.isna(x): return None
                    if isinstance(x, float) and (x == float('inf') or x == float('-inf')): return None
                    return x
                except:
                    return None
            
            df[col] = df[col].apply(clean_val)
            
        return df
    except Exception as e:
        print(f"Error en get_json_safe_df: {e}")
        return df
