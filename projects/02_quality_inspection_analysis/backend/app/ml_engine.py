import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from typing import List, Dict, Any

def compute_feature_importance(df: pd.DataFrame) -> List[Dict[str, Any]]:
    cat_features = ['line_id', 'product_code', 'supplier', 'inspector']
    num_features = ['thickness_mm', 'hardness_HV']
    
    X = pd.get_dummies(df[cat_features + num_features], drop_first=False, dtype=float)
    y = df['defect_rate']
    
    rf = RandomForestRegressor(n_estimators=150, max_depth=8, random_state=42)
    rf.fit(X, y)
    
    importances_raw = rf.feature_importances_
    feature_names = X.columns
    
    res = [
        {'feature': name, 'importance': round(float(imp * 100), 2)}
        for name, imp in zip(feature_names, importances_raw)
    ]
    res.sort(key=lambda x: x['importance'], reverse=True)
    return res
