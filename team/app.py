"""Factory Quality Radar - 발표용 체험형 AI 품질 관리 시뮬레이터."""

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from chat_engine import explain_with_gpt, parse_question, simulate_from_changes
from quality_risk_model import train_and_evaluate


st.set_page_config(page_title="Factory Quality Radar", page_icon="🏭", layout="wide")


@st.cache_resource(show_spinner="품질 예측 모델을 학습하고 있습니다...")
def get_results():
    return train_and_evaluate()


result = get_results()
forecast = result["forecast"]
page = st.sidebar.radio("발표 순서", ["1. 문제 정의", "2. AI 해결 설계", "3. 직접 체험하기", "4. AI 챗봇에게 묻기", "5. 검증과 한계"])
st.sidebar.divider()
st.sidebar.caption("Factory Quality Radar · 제조 AI 팀 프로젝트")


def risk_label(prediction: float) -> str:
    targets = result["dataset"].dropna(subset=["target_defect_rate"])["target_defect_rate"]
    if prediction >= targets.quantile(0.8):
        return "경고"
    if prediction >= targets.quantile(0.5):
        return "주의"
    return "정상"


def section_problem():
    st.title("문제 정의: 불량을 발견한 뒤 대응하면 늦습니다")
    st.subheader("현장의 문제")
    st.markdown("""
    제조 현장에서는 품질검사가 끝난 뒤에야 불량률을 확인하는 경우가 많습니다.
    이때 담당자는 **어느 라인을 먼저 점검해야 하는지**, 설비의 비가동·생산성 변화가 품질 위험과 관련 있는지를
    데이터로 판단하기 어렵습니다. 결과적으로 정비와 검사 인력이 모든 라인에 동일하게 배분될 수 있습니다.
    """)
    c1, c2, c3 = st.columns(3)
    c1.metric("품질 검사 로트", "900건", "라인·일자별 불량 정보")
    c2.metric("설비 가동 기록", "720건", "가동·비가동·양품·에너지")
    c3.metric("의사결정 질문", "내일 위험 라인은?", "사전 점검 우선순위")
    st.subheader("우리가 해결하려는 것")
    st.info("전날까지 확보된 운영·품질 정보로 **라인별 다음날 품질 불량률을 예측**하고, 현장 담당자가 운영 조건을 직접 바꾸어 보며 개선 우선순위를 판단하도록 돕습니다.")
    st.subheader("사용 시나리오")
    st.markdown("""
    1. 생산관리자가 마감 시점에 라인별 가동 상태를 입력하거나 확인합니다.
    2. AI가 다음날 예상 불량률과 위험 등급을 제시합니다.
    3. 담당자가 비가동률·양품률·생산량을 조절해 개선 시나리오를 비교합니다.
    4. 경고 라인을 우선 정비·추가 검사 대상으로 배정합니다.
    """)


def section_design():
    st.title("AI 해결 설계: 다음날 불량률을 예측합니다")
    st.subheader("무엇을 만들었나요?")
    st.markdown("**라인별 다음날 품질 불량률 회귀 모델**과, 그 결과를 직접 조작해 보는 What-if 시뮬레이터를 만들었습니다.")
    flow = pd.DataFrame({
        "단계": ["1. 운영 데이터", "2. 특징 생성", "3. 회귀 모델", "4. 현장 활용"],
        "내용": [
            "당일 가동시간·비가동시간·생산량·양품률·에너지·품질검사 정보를 수집",
            "가동가능률, 비가동률, 에너지/생산량, 최근 불량률, 비가동 사유별 시간을 계산",
            "Ridge·Random Forest와 기준 모델을 시간 순서대로 비교하여 다음날 불량률 예측",
            "예상 불량률과 위험 등급을 보고 고위험 라인을 우선 점검",
        ],
    })
    st.dataframe(flow, hide_index=True, use_container_width=True)
    st.subheader("모델이 보는 입력값과 결과")
    left, right = st.columns(2)
    with left:
        st.markdown("**입력값 (D일 마감 시점에 이미 아는 값)**")
        st.markdown("- 당일·최근 품질 불량률\n- 가동가능률과 비가동률\n- 생산량, 양품률, 에너지 효율\n- 비가동 사유별 시간\n- 라인 구분")
    with right:
        st.markdown("**출력값 (D+1일)**")
        st.markdown("- 예상 품질 검사 불량률\n- 정상 / 주의 / 경고 위험 등급\n- 현재 조건 대비 개선 또는 악화 폭\n- 우선 점검할 라인")
    st.warning("센서 데이터는 3월 2일부터, 가동률 데이터는 3월 1일까지라 같은 날짜가 없습니다. 따라서 현재 MVP는 가동률·품질검사 공통 기간만 학습에 사용하며, 센서 결합은 향후 고도화 과제입니다.")


def section_simulator():
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
        st.metric("기준 가동가능률", f"{base['availability']:.1%}")
        st.metric("기준 예상 불량률", f"{base['prediction']:.2%}")
        st.caption("가동가능률은 비가동률 조절값에 맞춰 자동으로 계산됩니다.")

    scenario = base.copy()
    scenario["downtime_rate"] = downtime_rate
    scenario["availability"] = max(0.0, 1 - downtime_rate)
    scenario["downtime_min"] = scenario["plan_min"] * downtime_rate
    scenario["run_min"] = scenario["plan_min"] - scenario["downtime_min"]
    scenario["prod_qty"] = scenario["prod_qty"] * production_factor
    scenario["yield_rate"] = yield_rate
    scenario["good_qty"] = scenario["prod_qty"] * yield_rate
    scenario["energy_per_unit"] = scenario["energy_per_unit"] * energy_factor
    scenario["energy_kwh"] = scenario["energy_per_unit"] * scenario["prod_qty"]
    input_frame = pd.DataFrame([scenario[result["numeric_features"] + result["categorical_features"]]])
    simulated_prediction = float(np.clip(result["model"].predict(input_frame)[0], 0, 1))
    delta = simulated_prediction - float(base["prediction"])

    st.subheader("AI 예측 결과")
    x1, x2, x3 = st.columns(3)
    x1.metric("시뮬레이션 예상 불량률", f"{simulated_prediction:.2%}", f"{delta:+.2%}p vs 기준")
    x2.metric("AI 위험 등급", risk_label(simulated_prediction))
    x3.metric("조정 후 가동가능률", f"{scenario['availability']:.1%}", f"{scenario['availability'] - base['availability']:+.1%}p")

    comparison = pd.DataFrame({"시나리오": ["기준 운영", "사용자 조정"], "예상 불량률": [base["prediction"], simulated_prediction]})
    fig = px.bar(comparison, x="시나리오", y="예상 불량률", text=comparison["예상 불량률"].map("{:.2%}".format), color="시나리오", labels={"예상 불량률": "예상 불량률"})
    fig.update_layout(showlegend=False, yaxis_tickformat=".0%", title="조건 변경 전후 AI 예측 비교")
    st.plotly_chart(fig, use_container_width=True)

    if delta > 0.003:
        st.error("불량 위험이 높아졌습니다. 비가동률과 양품률 저하 요인을 먼저 점검하는 시나리오가 필요합니다.")
    elif delta < -0.003:
        st.success("개선 효과가 예측됩니다. 해당 조건을 정비·운영 계획의 후보안으로 검토할 수 있습니다.")
    else:
        st.info("예상 변화가 작습니다. 최근 품질 추이와 비가동 사유를 함께 확인해 주세요.")
    st.caption("주의: 이 기능은 과거 데이터로 학습한 모델의 가상 시뮬레이션입니다. 현장 적용 전에는 실험·검증이 필요합니다.")


def section_validation():
    st.title("검증과 한계: AI 결과를 신뢰 가능하게 사용하려면")
    st.subheader("어떻게 검증했나요?")
    st.markdown("미래 데이터를 미리 본 것처럼 학습하지 않도록, 과거 80%를 학습하고 이후 20%를 검증하는 **시간 순서 hold-out** 방식을 사용했습니다.")
    st.dataframe(result["metrics"].style.format({"MAE": "{:.4f}", "RMSE": "{:.4f}", "R²": "{:.3f}"}), use_container_width=True)
    test_result = result["test_result"]
    max_value = max(test_result["target_defect_rate"].max(), test_result["prediction"].max())
    fig = px.scatter(test_result, x="target_defect_rate", y="prediction", color="line_id", hover_data=["inspect_date"], labels={"target_defect_rate": "실제 다음날 불량률", "prediction": "AI 예측 불량률", "line_id": "라인"})
    fig.add_shape(type="line", x0=0, y0=0, x1=max_value, y1=max_value, line=dict(dash="dash", color="gray"))
    fig.update_layout(title="검증 구간: 실제값과 예측값 (점선에 가까울수록 정확)")
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("현재 한계와 다음 개선")
    st.markdown("""
    - 표본이 작아 AI 예측은 **점검 우선순위를 정하는 보조 도구**로 사용해야 합니다.
    - 센서와 가동률 데이터의 기간이 겹치지 않아 온도·압력·진동 변수는 현재 모델에 포함하지 못했습니다.
    - 로트와 생산 설비를 직접 연결하는 키가 없어, 현재는 라인·일자 수준으로 집계했습니다.
    - 다음 버전에서는 공통 기간 센서 데이터와 lot_id-설비-생산시각 연결 정보를 수집해, 공정 조건까지 반영한 예측 모델로 확장합니다.
    """)


def section_chatbot():
    st.title("AI 챗봇에게 묻기: 말로 조건을 바꿔 보세요")
    st.markdown("질문에서 라인과 운영 조건을 찾으면, GPT가 숫자를 임의로 계산하지 않고 **로컬 회귀 모델 시뮬레이션 결과**를 설명합니다.")
    st.info("예시: `A라인에서 비가동률을 3% 줄이고 수율을 2% 올리면 불량률이 어떻게 바뀌어?`")
    default_line = st.selectbox("기준 라인", sorted(forecast["line_id"].unique()), key="chat_line")
    question = st.chat_input("운영 조건과 궁금한 점을 입력하세요")
    if question:
        with st.chat_message("user"):
            st.write(question)
        line, changes, notes = parse_question(question, default_line)
        simulation = simulate_from_changes(result, line, changes)
        answer, used_gpt = explain_with_gpt(question, simulation, notes)
        with st.chat_message("assistant"):
            st.write(answer)
            st.caption("GPT 설명 모드" if used_gpt else "로컬 설명 모드 · OPENAI_API_KEY를 설정하면 GPT 설명을 사용합니다.")
        cols = st.columns(3)
        cols[0].metric("적용 라인", line)
        cols[1].metric("예상 불량률", f"{simulation['prediction']:.2%}", f"{simulation['delta']:+.2%}p")
        cols[2].metric("위험 등급", risk_label(simulation["prediction"]))
        with st.expander("챗봇이 적용한 조건 보기"):
            st.write(", ".join(notes) if notes else "수치 변경 표현을 찾지 못했습니다. 예: '비가동률을 3% 줄이고 수율을 2% 올리면'처럼 입력하세요.")
    else:
        st.caption("현재는 비가동률·양품률·생산량·단위당 에너지의 증감 질문을 지원합니다. 퍼센트는 비가동률·양품률에서 %p로 해석합니다.")


if page == "1. 문제 정의":
    section_problem()
elif page == "2. AI 해결 설계":
    section_design()
elif page == "3. 직접 체험하기":
    section_simulator()
elif page == "4. AI 챗봇에게 묻기":
    section_chatbot()
else:
    section_validation()
