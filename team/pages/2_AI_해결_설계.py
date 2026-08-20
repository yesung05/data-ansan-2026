import pandas as pd
import streamlit as st

st.set_page_config(page_title="AI 해결 설계 | Factory Quality Radar", page_icon="🧠", layout="wide")
st.title("AI 해결 설계: 다음날 불량률을 예측합니다")
st.subheader("무엇을 만들었나요?")
st.markdown("**라인별 다음날 품질 불량률 회귀 모델**과, 그 결과를 직접 조작해 보는 What-if 시뮬레이터를 만들었습니다.")
flow = pd.DataFrame({"단계": ["1. 운영 데이터", "2. 특징 생성", "3. 회귀 모델", "4. 현장 활용"], "내용": ["당일 가동시간·비가동시간·생산량·양품률·에너지·품질검사 정보를 수집", "가동가능률, 비가동률, 에너지/생산량, 최근 불량률, 비가동 사유별 시간을 계산", "Ridge·Random Forest와 기준 모델을 시간 순서대로 비교하여 다음날 불량률 예측", "예상 불량률과 위험 등급을 보고 고위험 라인을 우선 점검"]})
st.dataframe(flow, hide_index=True, use_container_width=True)
st.subheader("모델이 보는 입력값과 결과")
left, right = st.columns(2)
with left:
    st.markdown("**입력값 (D일 마감 시점에 이미 아는 값)**\n\n- 당일·최근 품질 불량률\n- 가동가능률과 비가동률\n- 생산량, 양품률, 에너지 효율\n- 비가동 사유별 시간\n- 라인 구분")
with right:
    st.markdown("**출력값 (D+1일)**\n\n- 예상 품질 검사 불량률\n- 정상 / 주의 / 경고 위험 등급\n- 현재 조건 대비 개선 또는 악화 폭\n- 우선 점검할 라인")
st.warning("센서 데이터는 3월 2일부터, 가동률 데이터는 3월 1일까지라 같은 날짜가 없습니다. 따라서 현재 MVP는 가동률·품질검사 공통 기간만 학습에 사용하며, 센서 결합은 향후 고도화 과제입니다.")
