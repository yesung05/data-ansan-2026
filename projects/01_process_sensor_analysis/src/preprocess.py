import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
import pickle

def load_and_clean_data(file_path):
    df = pd.read_excel(file_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Raw copies for anomaly tracking
    df['raw_temp_C'] = df['temp_C']
    df['raw_pressure_bar'] = df['pressure_bar']
    df['raw_cycle_time_sec'] = df['cycle_time_sec']
    
    # Anomaly flags
    df['temp_anomaly'] = df['temp_C'] >= 500
    df['pressure_anomaly'] = df['pressure_bar'] < 0
    df['cycle_anomaly'] = df['cycle_time_sec'] > 100
    df['has_sensor_error'] = df['temp_anomaly'] | df['pressure_anomaly'] | df['cycle_anomaly']
    
    # Clean sentinel values
    df.loc[df['temp_anomaly'], 'temp_C'] = np.nan
    df.loc[df['pressure_anomaly'], 'pressure_bar'] = np.nan
    
    # Impute missing values with group medians (by line_id)
    for col in ['temp_C', 'pressure_bar', 'vibration_mm_s', 'humidity_pct', 'cycle_time_sec']:
        df[col] = df.groupby('line_id')[col].transform(lambda x: x.fillna(x.median()))
        df[col] = df[col].fillna(df[col].median())
        
    return df

def train_defect_model(df):
    features = ['temp_C', 'pressure_bar', 'vibration_mm_s', 'humidity_pct', 'cycle_time_sec']
    X = df[features]
    y = df['defect_flag']
    
    # Balanced Random Forest
    model = RandomForestClassifier(n_estimators=100, max_depth=5, class_weight='balanced', random_state=42)
    model.fit(X, y)
    return model, features
