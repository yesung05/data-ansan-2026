"""센서 데이터 기반 불량 발생 확률 예측 모델."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

DATA_DIR = Path(__file__).resolve().parent / "data"
RANDOM_STATE = 42

SENSOR_FEATURES = ["temp_C", "pressure_bar", "vibration_mm_s", "humidity_pct", "cycle_time_sec"]

# 센서 측정 오류로 보이는 극값 기준 (데이터 탐색에서 확인)
_VALID_RANGES = {
    "temp_C": (150.0, 300.0),
    "pressure_bar": (0.0, 10.0),
    "cycle_time_sec": (5.0, 100.0),
}


def load_and_clean_sensor(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """센서 원본을 로드하고 측정 오류 행을 제거한다."""
    sensor = pd.read_excel(data_dir / "01_process_sensor.xlsx")
    sensor["timestamp"] = pd.to_datetime(sensor["timestamp"])
    mask = pd.Series(True, index=sensor.index)
    for col, (lo, hi) in _VALID_RANGES.items():
        if col in sensor.columns:
            mask &= sensor[col].between(lo, hi) | sensor[col].isna()
    return sensor[mask].copy()


def train_sensor_model(data_dir: Path = DATA_DIR) -> dict[str, Any]:
    """센서 피처로 불량 발생 여부(defect_flag)를 예측하는 모델을 학습한다."""
    sensor = load_and_clean_sensor(data_dir)
    categorical = ["line_id"]

    preprocess = ColumnTransformer([
        ("num", SimpleImputer(strategy="median"), SENSOR_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
    ])
    model = Pipeline([
        ("preprocess", preprocess),
        ("model", RandomForestClassifier(
            n_estimators=200,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        )),
    ])
    X = sensor[SENSOR_FEATURES + categorical]
    y = sensor["defect_flag"]
    model.fit(X, y)

    # 라인별 중앙값을 슬라이더 기본값으로 사용
    line_medians: dict[str, dict[str, float]] = {}
    for line, grp in sensor.groupby("line_id"):
        line_medians[str(line)] = {
            col: float(grp[col].median()) for col in SENSOR_FEATURES
        }

    overall = sensor[SENSOR_FEATURES].agg(["median", "min", "max"])

    return {
        "model": model,
        "features": SENSOR_FEATURES,
        "categorical": categorical,
        "line_medians": line_medians,
        "overall_stats": overall,
        "train_size": len(sensor),
        "removed_rows": len(pd.read_excel(data_dir / "01_process_sensor.xlsx")) - len(sensor),
        "base_defect_rate": float(y.mean()),
        "sensor_period": (sensor["timestamp"].min(), sensor["timestamp"].max()),
    }


def predict_defect_prob(
    sensor_result: dict[str, Any],
    line: str,
    values: dict[str, float],
) -> float:
    """슬라이더 값으로 불량 발생 확률을 반환한다."""
    row = pd.DataFrame([{**values, "line_id": line}])
    return float(sensor_result["model"].predict_proba(row)[0][1])
