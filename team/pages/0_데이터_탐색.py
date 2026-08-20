import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from quality_risk_model import load_source_data
from ui_common import get_results, sidebar_augment_toggle

st.set_page_config(page_title="데이터 탐색 | Factory Quality Radar", page_icon="🔍", layout="wide")

augment = sidebar_augment_toggle()
result = get_results(augment)
quality_daily = result["quality_daily"]
dataset = result["dataset"]
labeled = dataset.dropna(subset=["target_defect_rate"])


@st.cache_data
def _load_raw():
    return load_source_data()


quality, uptime = _load_raw()

# ── 제목 ─────────────────────────────────────────────────────────────
st.title("데이터 탐색: 어떤 데이터로 무엇을 알 수 있나")
st.markdown("모델 학습에 사용한 원본 데이터의 분포·추이·상관관계를 확인합니다.")

# ── 1. 데이터 규모 ────────────────────────────────────────────────────
st.subheader("1. 데이터 규모")
c1, c2, c3, c4 = st.columns(4)
c1.metric("품질검사 로트", f"{len(quality):,}건", "3개 라인 · 5종 불량유형")
c2.metric("가동 기록", f"{len(uptime):,}건", "설비별 일별")
c3.metric(
    "품질검사 기간",
    f"{quality['inspect_date'].min().strftime('%m/%d')}–{quality['inspect_date'].max().strftime('%m/%d')}",
    "2026",
)
c4.metric(
    "가동률 기간",
    f"{uptime['date'].min().strftime('%m/%d')}–{uptime['date'].max().strftime('%m/%d')}",
    "2026",
)
st.warning(
    "품질검사(~4월)와 가동률(~3월) 기간이 달라, 현재 모델은 **공통 구간(1~3월)**만 학습합니다. "
    "센서·가동률 결합은 향후 과제입니다."
)

# ── 2. 라인별 불량률 분포 ──────────────────────────────────────────────
st.subheader("2. 라인별 일별 불량률 분포")

line_stats = quality_daily.groupby("line_id")["defect_rate"].agg(
    평균=("mean"), 표준편차=("std"), 최솟값=("min"), 최댓값=("max")
).round(4)
st.dataframe(line_stats.style.format("{:.2%}"), use_container_width=True)

fig_box = px.box(
    quality_daily,
    x="line_id", y="defect_rate", color="line_id",
    points="all",
    labels={"line_id": "라인", "defect_rate": "일별 불량률"},
    title="라인별 불량률 분포 (점: 개별 날짜, 상자: 사분위)",
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig_box.update_layout(yaxis_tickformat=".0%", showlegend=False)
st.plotly_chart(fig_box, use_container_width=True)
st.caption("C라인 불량률 평균이 A·B라인의 약 1.5배입니다. 고위험 라인 우선 점검 근거로 활용합니다.")

# ── 3. 불량률 시계열 ──────────────────────────────────────────────────
st.subheader("3. 불량률 시계열 추이")

fig_ts = px.line(
    quality_daily.sort_values("inspect_date"),
    x="inspect_date", y="defect_rate", color="line_id",
    labels={"inspect_date": "날짜", "defect_rate": "불량률", "line_id": "라인"},
    title="라인별 일별 불량률 추이",
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig_ts.update_layout(yaxis_tickformat=".0%")
st.plotly_chart(fig_ts, use_container_width=True)

# ── 4. 비가동 사유별 구성 ──────────────────────────────────────────────
st.subheader("4. 비가동 사유별 누적 시간")

reasons = uptime.copy()
reasons["downtime_reason"] = reasons["downtime_reason"].fillna("정상/미기록")
reason_summary = (
    reasons.groupby(["line_id", "downtime_reason"])["downtime_min"]
    .sum()
    .reset_index()
)
fig_reason = px.bar(
    reason_summary,
    x="line_id", y="downtime_min", color="downtime_reason",
    labels={"line_id": "라인", "downtime_min": "총 비가동 시간(분)", "downtime_reason": "사유"},
    title="라인·사유별 총 비가동 시간 (가동률 데이터 기간 내)",
)
st.plotly_chart(fig_reason, use_container_width=True)

# ── 5. 특징–타깃 상관관계 ──────────────────────────────────────────────
st.subheader("5. 특징과 다음날 불량률의 상관관계")

num_cols = result["numeric_features"]
corr_series = (
    labeled[num_cols + ["target_defect_rate"]]
    .corr()["target_defect_rate"]
    .drop("target_defect_rate")
)
corr_df = pd.DataFrame({
    "특징": corr_series.index,
    "상관계수": corr_series.values,
    "절댓값": corr_series.abs().values,
})
corr_df = corr_df.sort_values("절댓값", ascending=False).head(12).reset_index(drop=True)
corr_df["방향"] = corr_df["상관계수"].apply(lambda v: "양의 상관 (+)" if v > 0 else "음의 상관 (−)")

fig_corr = px.bar(
    corr_df,
    x="상관계수", y="특징", color="방향", orientation="h",
    title="다음날 불량률과 상관관계 상위 12개 특징 (Pearson r)",
    color_discrete_map={"양의 상관 (+)": "#EF553B", "음의 상관 (−)": "#636EFA"},
)
fig_corr.update_layout(yaxis={"categoryorder": "total ascending"}, xaxis_range=[-1, 1])
fig_corr.add_vline(x=0, line_dash="dash", line_color="gray")
st.plotly_chart(fig_corr, use_container_width=True)
st.caption(
    "상관계수는 선형 관계 강도만 나타냅니다. "
    "Random Forest는 비선형·상호작용 효과도 학습하므로 여기 순위와 모델의 중요도가 다를 수 있습니다."
)

# ── 6. 핵심 산점도 ────────────────────────────────────────────────────
st.subheader("6. 핵심 특징과 다음날 불량률 산점도")

left, right = st.columns(2)

with left:
    fig_dt = px.scatter(
        labeled, x="downtime_rate", y="target_defect_rate", color="line_id",
        trendline="ols",
        labels={
            "downtime_rate": "당일 비가동률",
            "target_defect_rate": "다음날 불량률",
            "line_id": "라인",
        },
        title="비가동률 vs 다음날 불량률",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_dt.update_layout(xaxis_tickformat=".0%", yaxis_tickformat=".0%")
    st.plotly_chart(fig_dt, use_container_width=True)

with right:
    fig_yr = px.scatter(
        labeled, x="yield_rate", y="target_defect_rate", color="line_id",
        trendline="ols",
        labels={
            "yield_rate": "당일 양품률",
            "target_defect_rate": "다음날 불량률",
            "line_id": "라인",
        },
        title="양품률 vs 다음날 불량률",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_yr.update_layout(xaxis_tickformat=".0%", yaxis_tickformat=".0%")
    st.plotly_chart(fig_yr, use_container_width=True)

st.caption(
    f"분석 대상: 학습+검증 행 {len(labeled)}개 "
    f"(학습 {result['train_rows']}행 / 검증 {result['test_rows']}행)"
    + (" · 데이터 증강 적용됨" if result["augmented"] else "")
)
