import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Tuple
from app.config import DATA_PATH

def load_data(file_path: Path = DATA_PATH) -> pd.DataFrame:
    df = pd.read_excel(file_path, sheet_name=0)
    return preprocess_data(df)

def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    
    # 1. Date formatting
    df['inspect_date'] = pd.to_datetime(df['inspect_date']).dt.strftime('%Y-%m-%d')
    
    # 2. Handle missing defect_type
    df['defect_type'] = df['defect_type'].fillna('정상/기타')
    
    # 3. Compute defect rate (%) = (defect_qty / insp_qty) * 100
    df['defect_rate'] = (df['defect_qty'] / df['insp_qty']) * 100.0
    
    # 4. Outlier detection using IQR (Thickness)
    q1_t = df['thickness_mm'].quantile(0.25)
    q3_t = df['thickness_mm'].quantile(0.75)
    iqr_t = q3_t - q1_t
    df['is_thickness_outlier_iqr'] = (df['thickness_mm'] < (q1_t - 1.5 * iqr_t)) | (df['thickness_mm'] > (q3_t + 1.5 * iqr_t))
    
    # 5. Outlier detection using Z-score (Hardness)
    mean_h = df['hardness_HV'].mean()
    std_h = df['hardness_HV'].std()
    df['hardness_zscore'] = (df['hardness_HV'] - mean_h) / (std_h if std_h != 0 else 1.0)
    df['is_hardness_outlier_z'] = df['hardness_zscore'].abs() > 3.0
    
    return df
