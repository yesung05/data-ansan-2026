"""Factory Quality Radar의 시작 페이지."""

import streamlit as st

from ui_common import get_results, sidebar_augment_toggle

st.set_page_config(page_title="Factory Quality Radar", page_icon="🏭", layout="wide")
st.title("🏭 Factory Quality Radar")
st.subheader("AI 기반 제조 품질 리스크 예측·체험 서비스")

augment = sidebar_augment_toggle()
result = get_results(augment)
forecast = result["forecast"]
top = forecast.iloc[0]
_level_color = {"경고": "error", "주의": "warning", "정상": "success"}.get(top["risk_level"], "info")
getattr(st, _level_color)(
    f"내일({top['forecast_date'].strftime('%Y-%m-%d')}) 최고 위험 라인: "
    f"**{top['line_id']} 라인** — 예상 불량률 {top['prediction']:.2%} [{top['risk_level']}]"
)

st.markdown("""
이 서비스는 라인별 운영·품질 데이터를 이용해 **다음날 품질 불량률을 예측**하고,
사용자가 운영 조건을 직접 바꾸어 보며 품질 리스크의 변화를 체험하도록 만든 팀 프로젝트입니다.

왼쪽의 Streamlit 페이지 메뉴에서 발표 순서에 맞는 화면을 선택하세요.
""")

cols = st.columns(4)
for col, title, text in zip(cols, ["문제 정의", "AI 해결 설계", "직접 체험", "AI 챗봇"], [
    "왜 사전 품질 예측이 필요한지 설명합니다.",
    "데이터, 타깃, 회귀 모델의 동작을 설명합니다.",
    "슬라이더로 운영 조건을 바꾸고 결과를 확인합니다.",
    "자연어 질문으로 시나리오를 실행합니다.",
]):
    with col:
        st.markdown(f"### {title}")
        st.write(text)

st.info("발표 권장 순서: 문제 정의 → AI 해결 설계 → 직접 체험하기 → AI 챗봇에게 묻기 → 검증과 한계")
st.caption("현재 MVP는 가동률·품질검사 공통 기간을 활용합니다. 센서 데이터와 가동률 데이터는 날짜가 겹치지 않아 함께 학습하지 않습니다.")
