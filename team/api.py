"""FastAPI REST 서버 — 센서·일별 운영 데이터를 받아 실시간 예측 및 알림을 제공한다.

실행:
    uvicorn api:app --reload --port 8000
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel

from alert_logger import write_alert
from quality_risk_model import train_and_evaluate
from sensor_model import train_sensor_model, predict_defect_prob

# ── 상수 ─────────────────────────────────────────────────────────────
SENSOR_ALERT_THRESHOLD = 0.30   # 센서 모델 불량 확률 임계값
BUFFER_FILE = Path(__file__).resolve().parent / "monitoring_buffer.json"

# ── 모델 초기화 (서버 기동 시 1회) ────────────────────────────────────
print("모델 로딩 중...", flush=True)
_sensor_result = train_sensor_model()
_quality_result = train_and_evaluate()
_daily_alert_threshold = _quality_result["risk_thresholds"][1]  # q80
print("모델 로딩 완료.", flush=True)

app = FastAPI(title="Factory Quality Radar API", version="1.0")


# ── 입력 스키마 ────────────────────────────────────────────────────────
class SensorReading(BaseModel):
    line_id: str
    temp_C: float
    pressure_bar: float
    vibration_mm_s: float
    humidity_pct: float
    cycle_time_sec: float


class DailyInput(BaseModel):
    line_id: str
    plan_min: float
    run_min: float
    downtime_min: float
    prod_qty: float
    good_qty: float
    energy_kwh: float
    defect_rate_today: float = 0.06  # 오늘 실측 불량률 (없으면 최근 평균 사용)


# ── 버퍼 유틸 ─────────────────────────────────────────────────────────
def _load_buffer() -> dict[str, Any]:
    if BUFFER_FILE.exists():
        try:
            return json.loads(BUFFER_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"sensors": {}, "daily": {}, "last_updated": None}


def _save_buffer(buf: dict) -> None:
    buf["last_updated"] = datetime.datetime.now().isoformat(timespec="seconds")
    BUFFER_FILE.write_text(json.dumps(buf, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 엔드포인트 ────────────────────────────────────────────────────────
@app.get("/api/status")
def get_status() -> dict:
    """monitoring_buffer.json 전체 현황을 반환한다."""
    return _load_buffer()


@app.get("/api/forecast")
def get_forecast() -> list[dict]:
    """학습 모델의 최신 라인별 불량률 예측을 반환한다."""
    fc = _quality_result["forecast"]
    return fc[["line_id", "prediction", "risk_level"]].to_dict("records")


@app.post("/api/sensor")
def ingest_sensor(reading: SensorReading) -> dict:
    """센서 1건을 수신해 불량 확률을 예측하고 임계값 초과 시 알림을 기록한다."""
    values = {
        "temp_C": reading.temp_C,
        "pressure_bar": reading.pressure_bar,
        "vibration_mm_s": reading.vibration_mm_s,
        "humidity_pct": reading.humidity_pct,
        "cycle_time_sec": reading.cycle_time_sec,
    }
    prob = predict_defect_prob(_sensor_result, reading.line_id, values)
    is_alert = prob >= SENSOR_ALERT_THRESHOLD

    buf = _load_buffer()
    buf["sensors"][reading.line_id] = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "values": reading.model_dump(),
        "defect_probability": round(prob, 4),
        "alert": is_alert,
    }
    _save_buffer(buf)

    if is_alert:
        write_alert(
            source="sensor",
            line=reading.line_id,
            value=prob,
            threshold=SENSOR_ALERT_THRESHOLD,
            context=reading.model_dump(),
        )

    return {
        "line_id": reading.line_id,
        "defect_probability": round(prob, 4),
        "alert": is_alert,
        "threshold": SENSOR_ALERT_THRESHOLD,
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
    }


@app.post("/api/daily")
def ingest_daily(data: DailyInput) -> dict:
    """일별 운영 데이터를 수신해 다음날 예상 불량률을 반환하고 임계값 초과 시 알림을 기록한다."""
    result = _quality_result
    features = result["numeric_features"] + result["categorical_features"]

    # 최신 기준 행에 입력값을 덮어써 피처 벡터 구성
    ref_rows = result["dataset"][result["dataset"]["line_id"] == data.line_id]
    row = ref_rows.sort_values("inspect_date").iloc[-1].copy() if not ref_rows.empty \
          else result["dataset"].iloc[-1].copy()

    safe_qty = data.prod_qty if data.prod_qty > 0 else np.nan
    row["line_id"] = data.line_id
    row["plan_min"] = data.plan_min
    row["run_min"] = data.run_min
    row["downtime_min"] = data.downtime_min
    row["prod_qty"] = data.prod_qty
    row["good_qty"] = data.good_qty
    row["energy_kwh"] = data.energy_kwh
    row["availability"] = data.run_min / data.plan_min if data.plan_min > 0 else 0.0
    row["downtime_rate"] = data.downtime_min / data.plan_min if data.plan_min > 0 else 0.0
    row["yield_rate"] = data.good_qty / safe_qty if pd.notna(safe_qty) else float(row.get("yield_rate", 0.95))
    row["energy_per_unit"] = data.energy_kwh / safe_qty if pd.notna(safe_qty) else float(row.get("energy_per_unit", 0.4))
    row["defect_rate"] = data.defect_rate_today
    row["defect_rate_lag_1"] = data.defect_rate_today
    row["defect_rate_rolling_3"] = (
        data.defect_rate_today * 0.5
        + float(row.get("defect_rate_rolling_3", data.defect_rate_today)) * 0.5
    )

    prediction = float(np.clip(result["model"].predict(pd.DataFrame([row[features]]))[0], 0, 1))
    risk_level = _risk_label(prediction)
    is_alert = prediction >= _daily_alert_threshold

    buf = _load_buffer()
    buf["daily"][data.line_id] = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "input": data.model_dump(),
        "defect_rate_forecast": round(prediction, 4),
        "risk_level": risk_level,
        "alert": is_alert,
    }
    _save_buffer(buf)

    if is_alert:
        write_alert(
            source="daily",
            line=data.line_id,
            value=prediction,
            threshold=_daily_alert_threshold,
            context=data.model_dump(),
        )

    return {
        "line_id": data.line_id,
        "defect_rate_forecast": round(prediction, 4),
        "risk_level": risk_level,
        "alert": is_alert,
        "threshold": round(_daily_alert_threshold, 4),
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
    }


def _risk_label(prediction: float) -> str:
    q50, q80 = _quality_result["risk_thresholds"]
    if prediction >= q80:
        return "경고"
    if prediction >= q50:
        return "주의"
    return "정상"
