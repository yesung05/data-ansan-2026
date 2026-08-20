import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from sensor_model import predict_defect_prob
from ui_common import get_results, get_sensor_result, risk_label, sidebar_augment_toggle

st.set_page_config(page_title="직접 체험하기 | Factory Quality Radar", page_icon="🎛️", layout="wide")

augment = sidebar_augment_toggle()
result = get_results(augment)
sensor_result = get_sensor_result()

dataset = result["dataset"]

# ── 라인 선택 (두 섹션 공유) ───────────────────────────────────────────
st.title("직접 체험하기: 운영 조건을 바꿔 보세요")
line = st.selectbox("시뮬레이션할 라인", sorted(dataset["line_id"].unique()))

# ════════════════════════════════════════════════════════════════════════
# SECTION 1 : 운영 조건 시뮬레이터  (가동률·생산량·에너지)
# ════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.subheader("① 운영 조건 시뮬레이터 — 다음날 예상 불량률")
st.markdown(
    "기준 날짜의 운영 조건을 조절하면, 학습된 회귀 모델이 **다음날 예상 불량률**을 다시 계산합니다."
)

# 해당 라인의 최근 7일치 날짜 목록
line_data = dataset[dataset["line_id"] == line].sort_values("inspect_date")
available_dates = sorted(line_data["inspect_date"].unique())[-7:][::-1]  # 최근 7일, 최신순

selected_date = st.selectbox(
    "기준 날짜 (최근 7일)",
    options=available_dates,
    format_func=lambda d: pd.Timestamp(d).strftime("%Y-%m-%d (%a)"),
)

base_rows = line_data[line_data["inspect_date"] == selected_date]
if base_rows.empty:
    st.warning("선택한 날짜에 해당 라인 데이터가 없습니다.")
    st.stop()
base = base_rows.iloc[0].copy()

# dataset에는 prediction 컬럼이 없으므로 직접 계산
features = result["numeric_features"] + result["categorical_features"]
base_prediction = float(np.clip(
    result["model"].predict(pd.DataFrame([base[features]]))[0], 0, 1
))

has_target = not pd.isna(base.get("target_defect_rate"))
if has_target:
    st.caption(
        f"기준일: {pd.Timestamp(selected_date).strftime('%Y-%m-%d')} "
        f"→ 예측 대상일: {pd.Timestamp(selected_date + pd.Timedelta(days=1)).strftime('%Y-%m-%d')} "
        f"· 실제 불량률: {base['target_defect_rate']:.2%}"
    )
else:
    st.caption(
        f"기준일: {pd.Timestamp(selected_date).strftime('%Y-%m-%d')} "
        f"→ 예측 대상일: {pd.Timestamp(selected_date + pd.Timedelta(days=1)).strftime('%Y-%m-%d')} "
        f"· 다음날 실제값 없음 (참고 예측)"
    )

# ── 슬라이더 ──────────────────────────────────────────────────────────
st.subheader("운영 조건 조절")
col_a, col_b, col_c = st.columns(3)

with col_a:
    downtime_pct = st.slider(
        "비가동률",
        min_value=0.0, max_value=30.0,
        value=float(base["downtime_rate"]) * 100,
        step=0.5, format="%.1f%%",
        help="계획 가동 시간 중 실제로 멈춰 있던 비율",
    )
    downtime_rate = downtime_pct / 100

    production_delta = st.slider(
        "생산량 변화", min_value=-40, max_value=40, value=0, step=5, format="%+d%%",
        help="기준 생산량 대비 증감 (±%)",
    )
    production_factor = 1.0 + production_delta / 100

with col_b:
    energy_delta = st.slider(
        "단위당 에너지 변화", min_value=-30, max_value=30, value=0, step=5, format="%+d%%",
        help="단위 생산당 에너지 소비 변화 (±%)",
    )
    energy_factor = 1.0 + energy_delta / 100

with col_c:
    st.metric("기준 가동가능률", f"{base['availability']:.1%}")
    st.metric("기준 예상 불량률", f"{base_prediction:.2%}")
    st.caption("가동가능률은 비가동률 조절값에 맞춰 자동 계산됩니다.")

# ── 시나리오 계산 ─────────────────────────────────────────────────────
scenario = base.copy()
scenario["downtime_rate"] = downtime_rate
scenario["availability"] = max(0.0, 1 - downtime_rate)
scenario["downtime_min"] = scenario["plan_min"] * downtime_rate
scenario["run_min"] = scenario["plan_min"] - scenario["downtime_min"]
scenario["prod_qty"] = scenario["prod_qty"] * production_factor
scenario["good_qty"] = scenario["prod_qty"] * scenario["yield_rate"]
scenario["energy_per_unit"] = scenario["energy_per_unit"] * energy_factor
scenario["energy_kwh"] = scenario["energy_per_unit"] * scenario["prod_qty"]

input_frame = pd.DataFrame([scenario[features]])
simulated_prediction = float(np.clip(result["model"].predict(input_frame)[0], 0, 1))
delta = simulated_prediction - base_prediction

# ── 결과 표시 ─────────────────────────────────────────────────────────
st.subheader("AI 예측 결과")
x1, x2, x3 = st.columns(3)
x1.metric("시뮬레이션 예상 불량률", f"{simulated_prediction:.2%}", f"{delta:+.2%}p vs 기준")
x2.metric("AI 위험 등급", risk_label(result, simulated_prediction))
x3.metric(
    "조정 후 가동가능률",
    f"{scenario['availability']:.1%}",
    f"{scenario['availability'] - base['availability']:+.1%}p",
)

comparison = pd.DataFrame({
    "시나리오": ["기준 운영", "사용자 조정"],
    "예상 불량률": [base_prediction, simulated_prediction],
})
fig = px.bar(
    comparison,
    x="시나리오", y="예상 불량률",
    text=comparison["예상 불량률"].map("{:.2%}".format),
    color="시나리오",
    labels={"예상 불량률": "예상 불량률"},
)
fig.update_layout(showlegend=False, yaxis_tickformat=".0%", title="조건 변경 전후 AI 예측 비교")
st.plotly_chart(fig, use_container_width=True)

if delta > 0.003:
    st.error("불량 위험이 높아졌습니다. 비가동률과 양품률 저하 요인을 먼저 점검하세요.")
elif delta < -0.003:
    st.success("개선 효과가 예측됩니다. 해당 조건을 정비·운영 계획의 후보안으로 검토할 수 있습니다.")
else:
    st.info("예상 변화가 작습니다. 최근 품질 추이와 비가동 사유를 함께 확인해 주세요.")

st.caption("주의: 과거 데이터 기반 가상 시뮬레이션입니다. 현장 적용 전 실험·검증이 필요합니다.")

# ════════════════════════════════════════════════════════════════════════
# SECTION 2 : 센서 조건 시뮬레이터
# ════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.subheader("② 센서 조건 시뮬레이터 — 불량 발생 확률")

sensor_period = sensor_result["sensor_period"]
st.markdown(
    f"센서 데이터({sensor_period[0].strftime('%Y-%m-%d')} ~ {sensor_period[1].strftime('%Y-%m-%d')}) "
    "기반 별도 모델입니다. 슬라이더로 공정 조건을 바꿔 불량 발생 확률이 어떻게 달라지는지 확인합니다."
)
st.info(
    f"학습 데이터: {sensor_result['train_size']}건 "
    f"(이상값 {sensor_result['removed_rows']}건 제거) · "
    f"기준 불량 발생률: {sensor_result['base_defect_rate']:.1%}"
)

# 해당 라인의 중앙값을 슬라이더 기본값으로
medians = sensor_result["line_medians"].get(line, {})
stats = sensor_result["overall_stats"]

def _med(col: str) -> float:
    return medians.get(col, float(stats.loc["median", col]))

def _range(col: str) -> tuple[float, float]:
    return float(stats.loc["min", col]), float(stats.loc["max", col])

s1, s2, s3 = st.columns(3)

with s1:
    lo, hi = _range("temp_C")
    temp = st.slider("온도 (°C)", lo, hi, _med("temp_C"), 0.5)

    lo, hi = _range("pressure_bar")
    pressure = st.slider("압력 (bar)", lo, hi, _med("pressure_bar"), 0.05)

with s2:
    lo, hi = _range("vibration_mm_s")
    vibration = st.slider("진동 (mm/s)", lo, hi, _med("vibration_mm_s"), 0.05)

    lo, hi = _range("humidity_pct")
    humidity = st.slider("습도 (%)", lo, hi, _med("humidity_pct"), 1.0)

with s3:
    lo, hi = _range("cycle_time_sec")
    cycle_time = st.slider("사이클 타임 (초)", lo, hi, _med("cycle_time_sec"), 0.5)

sensor_values = {
    "temp_C": temp,
    "pressure_bar": pressure,
    "vibration_mm_s": vibration,
    "humidity_pct": humidity,
    "cycle_time_sec": cycle_time,
}

# 기준값(라인 중앙값)과 시뮬레이션 확률 비교
base_sensor_values = {col: _med(col) for col in sensor_result["features"]}
base_prob = predict_defect_prob(sensor_result, line, base_sensor_values)
sim_prob = predict_defect_prob(sensor_result, line, sensor_values)
prob_delta = sim_prob - base_prob

p1, p2, p3 = st.columns(3)
p1.metric("라인 기준 불량 확률", f"{base_prob:.1%}")
p2.metric("시뮬레이션 불량 확률", f"{sim_prob:.1%}", f"{prob_delta:+.1%}p")
p3.metric("라인", line)

if prob_delta > 0.05:
    st.error("공정 조건이 불량 확률을 높이는 방향입니다. 온도·진동·사이클타임을 우선 점검하세요.")
elif prob_delta < -0.05:
    st.success("공정 조건이 개선되어 불량 확률이 낮아졌습니다.")
else:
    st.info("불량 확률 변화가 크지 않습니다.")

st.caption(
    "이 모델은 운영 조건 모델(①)과 독립적입니다. "
    "센서 기간(3월)과 가동률 기간(1~3월)이 달라 두 모델을 직접 비교하면 안 됩니다."
)
