import streamlit as st

from ui_common import get_results, sidebar_augment_toggle

st.set_page_config(page_title="문제 정의 | Factory Quality Radar", page_icon="🏭", layout="wide")

augment = sidebar_augment_toggle()
result = get_results(augment)
qd = result["quality_daily"]

# 라인별 실측 수치 계산
line_mean = qd.groupby("line_id")["defect_rate"].mean()
c_mean  = line_mean.get("C", 0.092)
ab_mean = (line_mean.get("A", 0.059) + line_mean.get("B", 0.059)) / 2
ratio   = c_mean / ab_mean if ab_mean > 0 else 1.5

# ── 결론부터 ────────────────────────────────────────────────────────────
st.title("문제 정의: 불량을 발견한 뒤 대응하면 늦습니다")

st.error(
    f"**C라인 평균 불량률 {c_mean:.1%}** — A·B라인({ab_mean:.1%})의 **{ratio:.1f}배**  \n"
    "그런데 이 사실을 담당자는 **다음 날 아침에야** 알 수 있었습니다."
)

st.markdown("---")

# ── 핵심 지표 ────────────────────────────────────────────────────────────
st.subheader("데이터로 확인한 현황")

c1, c2, c3, c4 = st.columns(4)
c1.metric("C라인 평균 불량률", f"{c_mean:.1%}", f"A·B 대비 +{(c_mean - ab_mean):.1%}p",
          delta_color="inverse")
c2.metric("A·B라인 평균 불량률", f"{ab_mean:.1%}", "기준")
c3.metric("품질검사 로트", "900건", "3개 라인 · 4개월")
c4.metric("설비 가동 기록", "720건", "일별 비가동·생산·에너지")

st.markdown("---")

# ── 현장의 문제 ──────────────────────────────────────────────────────────
st.subheader("현장의 문제")
left, right = st.columns([3, 2])

with left:
    st.markdown("""
제조 현장에서는 품질검사가 끝난 **뒤에야** 불량률을 확인합니다.

- 당일 아침 품질 결과가 나오면 이미 그 전날 공정은 끝난 상태
- **어느 라인을 먼저 점검해야 하는지** 데이터로 판단하기 어려움
- 설비의 비가동·생산성 변화가 품질 위험과 관련 있는지 불분명
- 결과적으로 정비·검사 인력이 모든 라인에 동일하게 배분
""")

with right:
    st.info(
        "**우리 팀의 질문**  \n\n"
        "전날 마감 시점에 확보되는 가동·품질 데이터로  \n"
        "**다음날 라인별 불량률을 미리 예측**할 수 있을까?  \n\n"
        "예측이 가능하다면, 고위험 라인을 사전에 집중 점검해  \n"
        "불량 발생 자체를 줄일 수 있다."
    )

st.markdown("---")

# ── 활용 시나리오 ─────────────────────────────────────────────────────────
st.subheader("사용 시나리오")
s1, s2, s3, s4 = st.columns(4)

with s1:
    st.markdown("**① 마감 데이터 수집**")
    st.markdown("생산관리자가 당일 가동 상태를 시스템에서 확인")

with s2:
    st.markdown("**② AI 예측 실행**")
    st.markdown("모델이 다음날 라인별 예상 불량률과 위험 등급 제시")

with s3:
    st.markdown("**③ 조건 시뮬레이션**")
    st.markdown("비가동률·생산량을 조절하며 개선 시나리오 비교")

with s4:
    st.markdown("**④ 우선 점검 배정**")
    st.markdown("경고 라인을 우선 정비·추가 검사 대상으로 배정")
