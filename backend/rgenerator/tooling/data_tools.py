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
        # En el futuro podríamos registrar el error aquí
        return {"error": "Invalid JSON format", "raw": text}
