import plotly.express as px
import streamlit as st

from ui_common import get_results, sidebar_augment_toggle


st.set_page_config(page_title="검증과 한계 | Factory Quality Radar", page_icon="📊", layout="wide")
augment = sidebar_augment_toggle()
result = get_results(augment)

st.title("검증과 한계: AI 결과를 신뢰 가능하게 사용하려면")
st.subheader("어떻게 검증했나요?")
aug_note = f" · 증강 학습 ({result['train_rows']}행)" if result["augmented"] else f" · 원본 학습 ({result['train_rows']}행)"
st.markdown(
    "미래 데이터를 미리 본 것처럼 학습하지 않도록, 과거 80%를 학습하고 이후 20%를 검증하는 "
    f"**시간 순서 hold-out** 방식을 사용했습니다.{aug_note} / 검증 {result['test_rows']}행"
)
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
