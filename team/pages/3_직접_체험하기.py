import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from ui_common import get_results, risk_label

st.set_page_config(page_title="직접 체험하기 | Factory Quality Radar", page_icon="🎛️", layout="wide")
result = get_results(); forecast = result["forecast"]
st.title("직접 체험하기: 운영 조건을 바꿔 보세요")
st.markdown("기준 운영 조건을 선택한 뒤 슬라이더를 움직이면, 학습된 회귀 모델이 **다음날 예상 불량률**을 다시 계산합니다.")
line = st.selectbox("시뮬레이션할 라인", sorted(forecast["line_id"].unique()))
base = forecast.loc[forecast["line_id"] == line].iloc[0].copy()
st.caption(f"기준 데이터 일자: {base['inspect_date'].strftime('%Y-%m-%d')} → 예측 대상일: {base['forecast_date'].strftime('%Y-%m-%d')}")
st.subheader("운영 조건 조절")
a, b, c = st.columns(3)
with a:
    downtime_rate = st.slider("비가동률", 0.0, 0.30, float(base["downtime_rate"]), 0.005, format="%.1f%%")
    production_factor = st.slider("생산량 변화", 0.60, 1.40, 1.00, 0.05, format="%.0f%%")
with b:
    yield_rate = st.slider("양품률", 0.80, 1.00, float(base["yield_rate"]), 0.005, format="%.1f%%")
    energy_factor = st.slider("단위당 에너지 변화", 0.70, 1.30, 1.00, 0.05, format="%.0f%%")
with c:
    st.metric("기준 가동가능률", f"{base['availability']:.1%}"); st.metric("기준 예상 불량률", f"{base['prediction']:.2%}"); st.caption("가동가능률은 비가동률 조절값에 맞춰 자동으로 계산됩니다.")
scenario = base.copy(); scenario["downtime_rate"] = downtime_rate; scenario["availability"] = max(0.0, 1-downtime_rate); scenario["downtime_min"] = scenario["plan_min"]*downtime_rate; scenario["run_min"] = scenario["plan_min"]-scenario["downtime_min"]; scenario["prod_qty"] *= production_factor; scenario["yield_rate"] = yield_rate; scenario["good_qty"] = scenario["prod_qty"]*yield_rate; scenario["energy_per_unit"] *= energy_factor; scenario["energy_kwh"] = scenario["energy_per_unit"]*scenario["prod_qty"]
input_frame = pd.DataFrame([scenario[result["numeric_features"]+result["categorical_features"]]])
simulated_prediction = float(np.clip(result["model"].predict(input_frame)[0], 0, 1)); delta = simulated_prediction-float(base["prediction"])
st.subheader("AI 예측 결과")
x1, x2, x3 = st.columns(3)
x1.metric("시뮬레이션 예상 불량률", f"{simulated_prediction:.2%}", f"{delta:+.2%}p vs 기준"); x2.metric("AI 위험 등급", risk_label(result, simulated_prediction)); x3.metric("조정 후 가동가능률", f"{scenario['availability']:.1%}", f"{scenario['availability']-base['availability']:+.1%}p")
comparison = pd.DataFrame({"시나리오": ["기준 운영", "사용자 조정"], "예상 불량률": [base["prediction"], simulated_prediction]})
fig = px.bar(comparison, x="시나리오", y="예상 불량률", text=comparison["예상 불량률"].map("{:.2%}".format), color="시나리오", labels={"예상 불량률": "예상 불량률"}); fig.update_layout(showlegend=False, yaxis_tickformat=".0%", title="조건 변경 전후 AI 예측 비교"); st.plotly_chart(fig, use_container_width=True)
if delta > 0.003: st.error("불량 위험이 높아졌습니다. 비가동률과 양품률 저하 요인을 먼저 점검하는 시나리오가 필요합니다.")
elif delta < -0.003: st.success("개선 효과가 예측됩니다. 해당 조건을 정비·운영 계획의 후보안으로 검토할 수 있습니다.")
else: st.info("예상 변화가 작습니다. 최근 품질 추이와 비가동 사유를 함께 확인해 주세요.")
st.caption("주의: 이 기능은 과거 데이터로 학습한 모델의 가상 시뮬레이션입니다. 현장 적용 전에는 실험·검증이 필요합니다.")
