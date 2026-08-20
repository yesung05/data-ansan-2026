"""현장 담당자가 오늘 가동 실측값을 입력하면 내일 불량률을 즉시 예측합니다."""

import numpy as np
import pandas as pd
import streamlit as st

from ui_common import get_results, risk_label, sidebar_augment_toggle

st.set_page_config(page_title="오늘 데이터 입력 | Factory Quality Radar", page_icon="📋", layout="wide")

augment = sidebar_augment_toggle()
result = get_results(augment)

st.title("📋 오늘 데이터 입력 → 내일 예측")
st.markdown(
    "오늘 마감 시점의 가동 실측값을 입력하면 **내일 예상 불량률과 위험 등급**을 즉시 계산합니다. "
    "과거 데이터 없이도 사용할 수 있으며, 동일 파일 형식(`03_machine_uptime.xlsx`)의 컬럼과 동일합니다."
)

# ── 최신 실측값을 기본값으로 ────────────────────────────────────────────
dataset = result["dataset"]
features = result["numeric_features"] + result["categorical_features"]

def _latest(line: str) -> pd.Series:
    rows = dataset[dataset["line_id"] == line].sort_values("inspect_date")
    return rows.iloc[-1] if not rows.empty else dataset.iloc[-1]

# ── 라인 선택 ─────────────────────────────────────────────────────────
line = st.selectbox("라인 선택", sorted(dataset["line_id"].unique()), key="input_line")
ref = _latest(line)

st.caption(
    f"입력 기본값은 {line}라인의 최근 데이터 "
    f"({pd.Timestamp(ref['inspect_date']).strftime('%Y-%m-%d')})를 참조합니다."
)

# ── 입력 폼 ───────────────────────────────────────────────────────────
with st.form("today_input"):
    st.subheader("가동 실측값 입력 (03_machine_uptime 스키마)")
    c1, c2, c3 = st.columns(3)

    with c1:
        plan_min = st.number_input(
            "계획 가동 시간 (분)", min_value=0, value=int(ref.get("plan_min", 480)),
            help="일 계획 총 가동 분",
        )
        run_min = st.number_input(
            "실제 가동 시간 (분)", min_value=0, value=int(ref.get("run_min", 440)),
            help="실제로 가동된 분 (plan_min 이하)",
        )
        downtime_min = st.number_input(
            "비가동 시간 (분)", min_value=0, value=int(ref.get("downtime_min", 40)),
            help="plan_min - run_min 과 대략 일치해야 함",
        )

    with c2:
        prod_qty = st.number_input(
            "생산 수량", min_value=0, value=int(ref.get("prod_qty", 500)),
        )
        good_qty = st.number_input(
            "양품 수량", min_value=0, value=int(ref.get("good_qty", 480)),
            help="생산 수량 이하",
        )
        energy_kwh = st.number_input(
            "에너지 소비 (kWh)", min_value=0.0, value=float(ref.get("energy_kwh", 200.0)), step=1.0,
        )

    with c3:
        # 비가동 사유별 시간 — 데이터에 있는 reason_ 컬럼 기반
        reason_cols = [c for c in result["numeric_features"] if c.startswith("reason_")]
        reason_inputs: dict[str, float] = {}
        for rc in reason_cols:
            label = rc.replace("reason_", "사유: ")
            reason_inputs[rc] = st.number_input(
                label, min_value=0.0, value=float(ref.get(rc, 0.0)), step=1.0,
                help="해당 비가동 사유로 멈춘 시간(분)",
            )

        # 품질 lag 값은 최신 실측값에서 자동 채움
        defect_rate_today = st.number_input(
            "오늘 불량률 (직접 입력, 0~1)",
            min_value=0.0, max_value=1.0,
            value=float(ref.get("defect_rate", 0.06)),
            step=0.001, format="%.3f",
            help="오늘 품질검사 결과 불량률 (알고 있으면 입력, 모르면 최근값 유지)",
        )

    submitted = st.form_submit_button("내일 불량률 예측", type="primary")

# ── 예측 실행 ─────────────────────────────────────────────────────────
if submitted:
    safe_qty = prod_qty if prod_qty > 0 else np.nan

    row = ref.copy()
    row["plan_min"] = plan_min
    row["run_min"] = run_min
    row["downtime_min"] = downtime_min
    row["prod_qty"] = prod_qty
    row["good_qty"] = good_qty
    row["energy_kwh"] = energy_kwh
    row["availability"] = run_min / plan_min if plan_min > 0 else 0.0
    row["downtime_rate"] = downtime_min / plan_min if plan_min > 0 else 0.0
    row["yield_rate"] = good_qty / safe_qty if pd.notna(safe_qty) else ref.get("yield_rate", 0.95)
    row["energy_per_unit"] = energy_kwh / safe_qty if pd.notna(safe_qty) else ref.get("energy_per_unit", 0.4)
    row["defect_rate"] = defect_rate_today
    row["defect_rate_lag_1"] = defect_rate_today          # 오늘 값이 lag_1 역할
    row["defect_rate_rolling_3"] = (                      # 최근 3일 평균 근사
        defect_rate_today * 0.5 + float(ref.get("defect_rate_rolling_3", defect_rate_today)) * 0.5
    )
    for rc, val in reason_inputs.items():
        row[rc] = val
    row["line_id"] = line

    prediction = float(np.clip(
        result["model"].predict(pd.DataFrame([row[features]]))[0], 0, 1
    ))
    level = risk_label(result, prediction)
    q50, q80 = result["risk_thresholds"]

    st.markdown("---")
    st.subheader("예측 결과")
    r1, r2, r3 = st.columns(3)
    r1.metric("내일 예상 불량률", f"{prediction:.2%}")
    r2.metric("위험 등급", level)
    r3.metric("가동가능률", f"{row['availability']:.1%}", f"비가동률 {row['downtime_rate']:.1%}")

    level_fn = {"경고": st.error, "주의": st.warning, "정상": st.success}.get(level, st.info)
    level_fn(
        f"{line}라인 내일 예측 불량률: **{prediction:.2%}** [{level}]  \n"
        f"기준 임계값 → 주의: {q50:.2%} / 경고: {q80:.2%}"
    )

    with st.expander("입력값 요약 (모델 피처 전체)"):
        st.dataframe(
            pd.DataFrame([row[features]]).T.rename(columns={0: "입력값"}),
            use_container_width=True,
        )

    st.caption(
        "lag·rolling 값은 오늘 입력 불량률과 최근 데이터에서 자동 근사합니다. "
        "더 정확한 예측은 실제 3일 불량률을 직접 입력하거나 Excel 업로드를 사용하세요."
    )
else:
    st.info("위 폼을 작성하고 '내일 불량률 예측' 버튼을 누르세요.")

# ── 개선 방향 안내 ─────────────────────────────────────────────────────
with st.expander("더 정확한 실시간 예측을 위한 다음 단계"):
    st.markdown("""
**A. 동일 포맷 Excel 업로드** (바로 구현 가능)
- `03_machine_uptime.xlsx`와 같은 컬럼 구조의 파일을 업로드
- 기존 학습 데이터에 병합 후 모델 재예측 → lag/rolling 자동 정확 계산
- `st.file_uploader()` + `pd.read_excel()` + `build_model_dataset()` 호출

**B. ERP/MES 연동** (중기)
- 가동률 시스템(MES)에서 일 마감 시 API로 데이터 자동 수신
- Streamlit을 주기적으로 새로고침하거나 Airflow 스케줄러로 배치 예측
- 현재 `train_and_evaluate()` 함수를 그대로 재사용 가능

**C. 센서 실시간 스트리밍** (장기)
- MQTT 브로커 또는 REST API로 센서 측정값을 수신
- `sensor_model.py`의 `predict_defect_prob()`를 5~10초 간격 호출
- 불량 확률이 임계값 초과 시 알림(Slack/이메일) 자동 발송
    """)
