"""다음날 라인별 품질 불량률 예측을 위한 데이터·모델 유틸리티."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


DATA_DIR = Path(__file__).resolve().parent / "data"
RANDOM_STATE = 42


def load_source_data(data_dir: Path = DATA_DIR) -> tuple[pd.DataFrame, pd.DataFrame]:
    """품질검사·가동률 원본을 불러와 분석 키를 정규화한다."""
    quality = pd.read_excel(data_dir / "02_quality_inspection.xlsx")
    uptime = pd.read_excel(data_dir / "03_machine_uptime.xlsx")
    quality["inspect_date"] = pd.to_datetime(quality["inspect_date"])
    uptime["date"] = pd.to_datetime(uptime["date"])
    uptime["line_id"] = uptime["machine_id"].str.split("-").str[0]
    return quality, uptime


def build_model_dataset(data_dir: Path = DATA_DIR) -> tuple[pd.DataFrame, pd.DataFrame]:
    """D일의 운영·품질 정보에서 D+1일 불량률을 예측할 학습/예측 행을 만든다.

    타깃은 반드시 정확히 다음 달력일의 검사 결과가 존재할 때만 생성한다.
    """
    quality, uptime = load_source_data(data_dir)

    quality_daily = quality.groupby(["inspect_date", "line_id"], as_index=False).agg(
        inspected_qty=("insp_qty", "sum"),
        defect_qty=("defect_qty", "sum"),
        lot_count=("lot_id", "nunique"),
    )
    quality_daily["defect_rate"] = quality_daily["defect_qty"] / quality_daily["inspected_qty"]
    quality_daily = quality_daily.sort_values(["line_id", "inspect_date"])
    quality_daily["defect_rate_lag_1"] = quality_daily.groupby("line_id")["defect_rate"].shift(1)
    quality_daily["defect_rate_rolling_3"] = (
        quality_daily.groupby("line_id")["defect_rate"].transform(lambda x: x.shift(1).rolling(3, min_periods=1).mean())
    )

    uptime_daily = uptime.groupby(["date", "line_id"], as_index=False).agg(
        plan_min=("plan_min", "sum"),
        run_min=("run_min", "sum"),
        downtime_min=("downtime_min", "sum"),
        prod_qty=("prod_qty", "sum"),
        good_qty=("good_qty", "sum"),
        energy_kwh=("energy_kWh", "sum"),
    )
    uptime_daily["availability"] = uptime_daily["run_min"] / uptime_daily["plan_min"]
    uptime_daily["downtime_rate"] = uptime_daily["downtime_min"] / uptime_daily["plan_min"]
    uptime_daily["yield_rate"] = uptime_daily["good_qty"] / uptime_daily["prod_qty"]
    uptime_daily["energy_per_unit"] = uptime_daily["energy_kwh"] / uptime_daily["prod_qty"]

    reasons = uptime.assign(downtime_reason=uptime["downtime_reason"].fillna("정상/미기록"))
    reason_minutes = reasons.pivot_table(
        index=["date", "line_id"], columns="downtime_reason", values="downtime_min", aggfunc="sum", fill_value=0
    ).add_prefix("reason_").reset_index()
    uptime_daily = uptime_daily.merge(reason_minutes, on=["date", "line_id"], how="left")

    features = quality_daily.merge(
        uptime_daily, left_on=["inspect_date", "line_id"], right_on=["date", "line_id"], how="inner"
    ).drop(columns="date")

    tomorrow_quality = quality_daily[["inspect_date", "line_id", "defect_rate"]].copy()
    tomorrow_quality["inspect_date"] -= pd.Timedelta(days=1)
    tomorrow_quality = tomorrow_quality.rename(columns={"defect_rate": "target_defect_rate"})
    model_data = features.merge(tomorrow_quality, on=["inspect_date", "line_id"], how="left")
    model_data = model_data.sort_values(["inspect_date", "line_id"]).reset_index(drop=True)
    return model_data, quality_daily


def feature_columns(dataset: pd.DataFrame) -> tuple[list[str], list[str]]:
    excluded = {"inspect_date", "target_defect_rate", "defect_qty"}
    categorical = ["line_id"]
    numeric = [c for c in dataset.columns if c not in excluded | set(categorical)]
    return numeric, categorical


def make_models(numeric_features: list[str], categorical_features: list[str]) -> dict[str, Pipeline]:
    preprocess_linear = ColumnTransformer([
        ("numeric", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric_features),
        ("line", OneHotEncoder(handle_unknown="ignore"), categorical_features),
    ])
    preprocess_tree = ColumnTransformer([
        ("numeric", SimpleImputer(strategy="median"), numeric_features),
        ("line", OneHotEncoder(handle_unknown="ignore"), categorical_features),
    ])
    return {
        "Ridge 회귀": Pipeline([("preprocess", preprocess_linear), ("model", Ridge(alpha=5.0))]),
        "Random Forest": Pipeline([
            ("preprocess", preprocess_tree),
            ("model", RandomForestRegressor(n_estimators=300, min_samples_leaf=3, max_features=0.8, random_state=RANDOM_STATE)),
        ]),
    }


def train_and_evaluate(data_dir: Path = DATA_DIR) -> dict[str, Any]:
    """시간 순서 hold-out 평가 후 성능이 가장 좋은 모델을 반환한다."""
    dataset, quality_daily = build_model_dataset(data_dir)
    labeled = dataset.dropna(subset=["target_defect_rate"]).copy()
    numeric, categorical = feature_columns(labeled)
    dates = np.sort(labeled["inspect_date"].unique())
    split_date = dates[max(1, int(len(dates) * 0.8))]
    train = labeled[labeled["inspect_date"] < split_date].copy()
    test = labeled[labeled["inspect_date"] >= split_date].copy()
    x_train, y_train = train[numeric + categorical], train["target_defect_rate"]
    x_test, y_test = test[numeric + categorical], test["target_defect_rate"]

    predictions: dict[str, np.ndarray] = {"기준 모델(당일 불량률)": test["defect_rate"].to_numpy()}
    fitted_models = make_models(numeric, categorical)
    for name, model in fitted_models.items():
        model.fit(x_train, y_train)
        predictions[name] = model.predict(x_test)

    metrics = []
    for name, pred in predictions.items():
        metrics.append({
            "모델": name,
            "MAE": mean_absolute_error(y_test, pred),
            "RMSE": mean_squared_error(y_test, pred) ** 0.5,
            "R²": r2_score(y_test, pred),
        })
    metrics_df = pd.DataFrame(metrics).sort_values("MAE").reset_index(drop=True)
    best_name = metrics_df.iloc[0]["모델"]
    best_model = fitted_models.get(best_name)
    if best_model is None:
        # 기준 모델이 우수할 때도 서비스용 모델은 전체 데이터로 학습해 참고 예측을 제공한다.
        best_name = "Random Forest (참고 예측)"
        best_model = make_models(numeric, categorical)["Random Forest"]
    best_model.fit(labeled[numeric + categorical], labeled["target_defect_rate"])

    test_result = test[["inspect_date", "line_id", "target_defect_rate"]].copy()
    test_result["prediction"] = predictions[metrics_df.iloc[0]["모델"]]
    test_result["prediction"] = test_result["prediction"].clip(0, 1)

    latest_feature_date = dataset["inspect_date"].max()
    latest_features = dataset[dataset["inspect_date"] == latest_feature_date].copy()
    latest_features["prediction"] = best_model.predict(latest_features[numeric + categorical]).clip(0, 1)
    train_target = labeled["target_defect_rate"]
    latest_features["risk_level"] = pd.cut(
        latest_features["prediction"],
        bins=[-np.inf, train_target.quantile(0.5), train_target.quantile(0.8), np.inf],
        labels=["정상", "주의", "경고"],
    ).astype(str)
    latest_features["forecast_date"] = latest_feature_date + pd.Timedelta(days=1)

    return {
        "dataset": dataset,
        "quality_daily": quality_daily,
        "metrics": metrics_df,
        "test_result": test_result,
        "forecast": latest_features.sort_values("prediction", ascending=False),
        "best_model_name": best_name,
        "model": best_model,
        "numeric_features": numeric,
        "categorical_features": categorical,
        "feature_count": len(numeric) + len(categorical),
        "train_rows": len(train),
        "test_rows": len(test),
    }
