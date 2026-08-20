import streamlit as st

from chat_engine import explain_with_gpt, parse_question, simulate_from_changes
from ui_common import get_results, risk_label, sidebar_augment_toggle


st.set_page_config(page_title="AI 챗봇 | Factory Quality Radar", page_icon="💬", layout="wide")
augment = sidebar_augment_toggle()
result = get_results(augment)
forecast = result["forecast"]

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
    cols[2].metric("위험 등급", risk_label(result, simulation["prediction"]))
    with st.expander("챗봇이 적용한 조건 보기"):
        st.write(", ".join(notes) if notes else "수치 변경 표현을 찾지 못했습니다. 예: '비가동률을 3% 줄이고 수율을 2% 올리면'처럼 입력하세요.")
else:
    st.caption("현재는 비가동률·양품률·생산량·단위당 에너지의 증감 질문을 지원합니다. 퍼센트는 비가동률·양품률에서 %p로 해석합니다.")
