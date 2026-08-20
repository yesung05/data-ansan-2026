import pandas as pd
import numpy as np
import statsmodels.api as sm
from typing import Dict, Any, List

def calculate_cpk(data: pd.Series, usl: float, lsl: float) -> Dict[str, float]:
    mu = float(data.mean())
    sigma = float(data.std(ddof=1))
    
    if sigma == 0:
        return {'cp': 0.0, 'cpk': 0.0, 'cpu': 0.0, 'cpl': 0.0, 'mean': mu, 'std': 0.0, 'usl': usl, 'lsl': lsl}
    
    cp = (usl - lsl) / (6.0 * sigma)
    cpu = (usl - mu) / (3.0 * sigma)
    cpl = (mu - lsl) / (3.0 * sigma)
    cpk = min(cpu, cpl)
    
    return {
        'cp': round(cp, 3),
        'cpk': round(cpk, 3),
        'cpu': round(cpu, 3),
        'cpl': round(cpl, 3),
        'mean': round(mu, 4),
        'std': round(sigma, 4),
        'usl': usl,
        'lsl': lsl
    }

def run_regression_analysis(df: pd.DataFrame) -> List[Dict[str, Any]]:
    feature_cols = ['line_id', 'product_code', 'supplier', 'thickness_mm', 'hardness_HV', 'inspector']
    df_encoded = pd.get_dummies(df[feature_cols], drop_first=True, dtype=float)
    
    X = sm.add_constant(df_encoded)
    y = df['defect_rate']
    
    model = sm.OLS(y, X).fit()
    
    results = []
    for var_name in model.params.index:
        if var_name == 'const':
            continue
        results.append({
            'variable': var_name,
            'coef': round(float(model.params[var_name]), 4),
            'std_err': round(float(model.bse[var_name]), 4),
            't_stat': round(float(model.tvalues[var_name]), 3),
            'p_value': round(float(model.pvalues[var_name]), 6),
            'is_significant': bool(model.pvalues[var_name] < 0.05)
        })
    
    results.sort(key=lambda x: abs(x['coef']), reverse=True)
    return results

def compute_correlation_matrix(df: pd.DataFrame) -> Dict[str, Any]:
    numeric_cols = ['insp_qty', 'defect_qty', 'defect_rate', 'thickness_mm', 'hardness_HV']
    corr = df[numeric_cols].corr().round(3)
    return {
        'columns': numeric_cols,
        'matrix': corr.to_dict()
    }
