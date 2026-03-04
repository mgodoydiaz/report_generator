import pandas as pd
from rgenerator.tooling.data_tools import get_json_safe_df


def get_df(path):
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_excel(path)
    return get_json_safe_df(df)


def save_df(df, path):
    df.to_excel(path, index=False)
