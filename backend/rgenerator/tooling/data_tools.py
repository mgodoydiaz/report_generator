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
    Reemplaza NaN, Infinity y -Infinity por None y convierte tipos numpy a Python nativos.
    """
    import math
    import numpy as np
    try:
        import pandas as pd
        if df is None or df.empty:
            return df

        def clean_val(x):
            try:
                if pd.isna(x):
                    return None
            except (TypeError, ValueError):
                pass
            if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
                return None
            # Convertir tipos numpy a Python nativos para que json.dumps los acepte
            if isinstance(x, (np.integer,)):
                return int(x)
            if isinstance(x, (np.floating,)):
                return float(x)
            if isinstance(x, (np.bool_,)):
                return bool(x)
            return x

        for col in df.columns:
            df[col] = df[col].astype(object).apply(clean_val)

        return df
    except Exception as e:
        print(f"Error en get_json_safe_df: {e}")
        return df
