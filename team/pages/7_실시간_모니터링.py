"""실시간 센서·운영 모니터링 대시보드.

monitoring_buffer.json을 읽어 라인별 현황을 표시하고,
임계값 초과 시 배너와 토스트로 알림을 보낸다.
10초마다 자동 갱신 (streamlit-autorefresh 패키지 필요).
"""

import json
from pathlib import Path

import streamlit as st

from alert_logger import read_recent_alerts
from ui_common import sidebar_augment_toggle

st.set_page_config(
    page_title="실시간 모니터링 | Factory Quality Radar",
    page_icon="📡",
    layout="wide",
)
sidebar_augment_toggle()

# ── 자동 새로고침 ─────────────────────────────────────────────────────
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=10_000, limit=None, key="monitor_refresh")
    refresh_mode = "자동 (10초)"
except ImportError:
    refresh_mode = "수동"
    if st.button("🔄 새로고침"):
        st.rerun()

BUFFER_FILE = Path(__file__).resolve().parent.parent / "monitoring_buffer.json"
SENSOR_THRESHOLD = 0.30

# ── 버퍼 로드 ─────────────────────────────────────────────────────────
def _load_buffer() -> dict:
    if not BUFFER_FILE.exists():
        return {}
    try:
        return json.loads(BUFFER_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

buf = _load_buffer()
sensors = buf.get("sensors", {})
daily = buf.get("daily", {})
last_updated = buf.get("last_updated", "—")

# ── 헤더 ─────────────────────────────────────────────────────────────
st.title("📡 실시간 모니터링")
st.caption(
    f"새로고침: **{refresh_mode}** · 마지막 데이터: **{last_updated}** · "
    f"API: `POST http://localhost:8000/api/sensor` / `POST /api/daily`"
)

if not sensors and not daily:
    st.info(
        "수신된 데이터가 없습니다. API 서버를 기동하고 데이터를 전송하세요.\n\n"
        "```powershell\n"
        "uvicorn api:app --reload --port 8000\n"
        "```"
    )
    st.stop()

# ── 전체 경고 배너 ────────────────────────────────────────────────────
alert_lines = [line for line, d in {**sensors, **daily}.items() if d.get("alert")]
if alert_lines:
    st.error(f"경고: **{', '.join(sorted(set(alert_lines)))}** 라인에서 임계값 초과!")
    for line in sorted(set(alert_lines)):
        st.toast(f"{line}라인 불량 위험 임계값 초과!", icon="🚨")

st.markdown("---")

# ── 센서 현황 ─────────────────────────────────────────────────────────
st.subheader("① 센서 불량 확률 (POST /api/sensor)")

if sensors:
    cols = st.columns(len(sensors))
    for col, (line, info) in zip(cols, sorted(sensors.items())):
        prob = info.get("defect_probability", 0)
        is_alert = info.get("alert", False)
        ts = info.get("timestamp", "—")
        with col:
            if is_alert:
                st.error(f"**{line}라인** 🚨")
            else:
                st.success(f"**{line}라인** ✅")
            st.metric("불량 확률", f"{prob:.1%}", delta=f"임계 {SENSOR_THRESHOLD:.0%}")
            vals = info.get("values", {})
            st.caption(
                f"온도 {vals.get('temp_C', '-'):.1f}°C · "
                f"진동 {vals.get('vibration_mm_s', '-'):.2f}mm/s · "
                f"{ts}"
            )
else:
    st.info("/api/sensor 데이터 없음")

st.markdown("---")

# ── 일별 예측 현황 ────────────────────────────────────────────────────
st.subheader("② 일별 운영 데이터 예측 (POST /api/daily)")

if daily:
    cols2 = st.columns(len(daily))
    for col, (line, info) in zip(cols2, sorted(daily.items())):
        forecast = info.get("defect_rate_forecast", 0)
        risk = info.get("risk_level", "—")
        is_alert = info.get("alert", False)
        ts = info.get("timestamp", "—")
        with col:
            if is_alert:
                st.error(f"**{line}라인** 🚨 [{risk}]")
            elif risk == "주의":
                st.warning(f"**{line}라인** ⚠ [{risk}]")
            else:
                st.success(f"**{line}라인** ✅ [{risk}]")
            st.metric("내일 예상 불량률", f"{forecast:.2%}")
            st.caption(ts)
else:
    st.info("/api/daily 데이터 없음")

st.markdown("---")

# ── 알림 로그 ─────────────────────────────────────────────────────────
st.subheader("③ 최근 알림 로그")

recent = read_recent_alerts(n=20)
if recent:
    import pandas as pd
    log_df = pd.DataFrame(recent)[["timestamp", "source", "line_id", "value", "threshold"]]
    log_df["value"] = log_df["value"].map("{:.2%}".format)
    log_df["threshold"] = log_df["threshold"].map("{:.2%}".format)
    log_df.columns = ["시각", "소스", "라인", "측정값", "임계값"]
    st.dataframe(log_df, use_container_width=True, hide_index=True)
else:
    st.info("alerts.log가 없거나 알림 이력이 없습니다.")
