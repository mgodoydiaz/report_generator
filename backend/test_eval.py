import pandas as pd
import numpy as np

row = pd.Series({'Correcta': np.nan, 'A': 1, 'B': 2})
# math_ns allowed in etl_tools.py:
_math_ns = {"__builtins__": {}, "abs": abs, "round": round, "min": min, "max": max, "sum": sum, "len": len, "str": str, "float": float, "int": int}
env = {**_math_ns, "row": row}

cond1 = eval("row.isna()['Correcta']", env)
print("cond1 (isnan):", cond1)

try:
    exp2 = eval("str(row['Correcta']).upper()", env)
    print("exp2 (str.upper on nan):", exp2)
except Exception as e:
    print("exp2 error:", e)

try:
    cond3 = eval("str(row['Correcta']) == 'nan'", env)
    print("cond3 (str=='nan'):", cond3)
except Exception as e:
    print("cond3 error:", e)

