import streamlit as st

from ui_common import sidebar_augment_toggle

st.set_page_config(page_title="문제 정의 | Factory Quality Radar", page_icon="🏭", layout="wide")
sidebar_augment_toggle()
st.title("문제 정의: 불량을 발견한 뒤 대응하면 늦습니다")
st.subheader("현장의 문제")
st.markdown("""제조 현장에서는 품질검사가 끝난 뒤에야 불량률을 확인하는 경우가 많습니다. 이때 담당자는 **어느 라인을 먼저 점검해야 하는지**, 설비의 비가동·생산성 변화가 품질 위험과 관련 있는지를 데이터로 판단하기 어렵습니다. 결과적으로 정비와 검사 인력이 모든 라인에 동일하게 배분될 수 있습니다.""")
c1, c2, c3 = st.columns(3)
c1.metric("품질 검사 로트", "900건", "라인·일자별 불량 정보")
c2.metric("설비 가동 기록", "720건", "가동·비가동·양품·에너지")
c3.metric("의사결정 질문", "내일 위험 라인은?", "사전 점검 우선순위")
st.subheader("우리가 해결하려는 것")
st.info("전날까지 확보된 운영·품질 정보로 **라인별 다음날 품질 불량률을 예측**하고, 현장 담당자가 운영 조건을 직접 바꾸어 보며 개선 우선순위를 판단하도록 돕습니다.")
st.subheader("사용 시나리오")
st.markdown("""1. 생산관리자가 마감 시점에 라인별 가동 상태를 확인합니다.
2. AI가 다음날 예상 불량률과 위험 등급을 제시합니다.
3. 담당자가 비가동률·양품률·생산량을 조절해 개선 시나리오를 비교합니다.
4. 경고 라인을 우선 정비·추가 검사 대상으로 배정합니다.""")
