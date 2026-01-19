from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data" / "output"
STYLE_PATH = ROOT_DIR / "streamlit_style.css"


def apply_style() -> None:
    if STYLE_PATH.exists():
        styles = STYLE_PATH.read_text(encoding="utf-8")
        st.markdown(f"<style>{styles}</style>", unsafe_allow_html=True)
    else:
        st.info("No se encontro streamlit_style.css.")


def get_data_path(filename: str) -> Path:
    return DATA_DIR / filename


@st.cache_data(show_spinner=False)
def load_excel(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    try:
        return pd.read_excel(path)
    except Exception:
        return None


def to_float(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("%", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None
