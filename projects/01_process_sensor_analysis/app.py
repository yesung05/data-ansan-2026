import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

# Set page config
st.set_page_config(
    page_title="공정 센서 실시간 모니터링 & AI 분석 대시보드",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #1f77b4;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .metric-title { font-size: 0.85rem; color: #6c757d; font-weight: bold; }
    .metric-value { font-size: 1.6rem; font-weight: bold; color: #212529; }
    .status-normal { color: #28a745; font-weight: bold; }
    .status-warning { color: #ffc107; font-weight: bold; }
    .status-danger { color: #dc3545; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Add project root
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.config import ORIGINAL_DATA_PATH
from src.preprocess import load_and_clean_data, train_defect_model

@st.cache_data
def get_data():
    return load_and_clean_data(ORIGINAL_DATA_PATH)

@st.cache_resource
def get_model(df):
    return train_defect_model(df)

# Load data & model
df_clean = get_data()
model, feature_names = get_model(df_clean)

# Sidebar filters
st.sidebar.title("🏭 공정 관제 필터")
st.sidebar.markdown("---")

# Line filter
all_lines = sorted(df_clean['line_id'].unique().tolist())
selected_lines = st.sidebar.multiselect("생산 라인 선택", options=all_lines, default=all_lines)

# Machine filter
available_machines = sorted(df_clean[df_clean['line_id'].isin(selected_lines)]['machine_id'].unique().tolist())
selected_machines = st.sidebar.multiselect("설비 ID 선택", options=available_machines, default=available_machines)

# Shift filter
all_shifts = df_clean['shift'].unique().tolist()
selected_shifts = st.sidebar.multiselect("작업조 (Shift)", options=all_shifts, default=all_shifts)

# Defect status filter
defect_filter = st.sidebar.radio("품질 필터", options=["전체 보기", "정상 제품만 (0)", "불량 발생만 (1)"])

# Date range
min_date = df_clean['timestamp'].min().to_pydatetime()
max_date = df_clean['timestamp'].max().to_pydatetime()
date_range = st.sidebar.slider("수집 기간", min_value=min_date, max_value=max_date, value=(min_date, max_date), format="MM/DD HH:mm")

# Apply filters
filtered_df = df_clean[
    (df_clean['line_id'].isin(selected_lines)) &
    (df_clean['machine_id'].isin(selected_machines)) &
    (df_clean['shift'].isin(selected_shifts)) &
    (df_clean['timestamp'] >= date_range[0]) &
    (df_clean['timestamp'] <= date_range[1])
]

if defect_filter == "정상 제품만 (0)":
    filtered_df = filtered_df[filtered_df['defect_flag'] == 0]
elif defect_filter == "불량 발생만 (1)":
    filtered_df = filtered_df[filtered_df['defect_flag'] == 1]

# Header
st.title("🏭 스마트 공정 센서 모니터링 & AI 분석 대시보드")
st.caption(f"기준 데이터: {ORIGINAL_DATA_PATH.name} | 분석 레코드: {len(filtered_df):,}건")

# KPI Summary Row
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

total_records = len(filtered_df)
total_defects = int(filtered_df['defect_flag'].sum())
defect_rate = (total_defects / total_records * 100) if total_records > 0 else 0
sensor_errors = int(filtered_df['has_sensor_error'].sum())
avg_cycle = filtered_df['cycle_time_sec'].mean() if total_records > 0 else 0
avg_temp = filtered_df['temp_C'].mean() if total_records > 0 else 0

with kpi1:
    st.metric("총 공정 사이클", f"{total_records:,} 건")
with kpi2:
    st.metric("불량 건수 / 불량률", f"{total_defects} 건", f"{defect_rate:.2f}%", delta_color="inverse")
with kpi3:
    st.metric("센서 이상치(에러) 감지", f"{sensor_errors} 건", delta_color="inverse")
with kpi4:
    st.metric("평균 사이클 타임", f"{avg_cycle:.1f} 초")
with kpi5:
    st.metric("평균 챔버 온도", f"{avg_temp:.1f} °C")

st.markdown("---")

# Main Navigation Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 실시간 공정 텔레메트리",
    "📊 라인/설비 벤치마킹",
    "🧪 What-If 불량 예측 시뮬레이터",
    "📋 원본 데이터 & 리포트 다운로드"
])

# ----------------- TAB 1: Real-Time Telemetry -----------------
with tab1:
    st.subheader("⏱️ 시계열 센서 트렌드 & 이상 감지")
    
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        sensor_choice = st.selectbox("모니터링 센서 선택", ["온도 & 압력 (Dual Axis)", "진동 (Vibration)", "습도 (Humidity)", "사이클 타임 (Cycle Time)"])
    
    if len(filtered_df) > 0:
        if sensor_choice == "온도 & 압력 (Dual Axis)":
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=filtered_df['timestamp'], y=filtered_df['temp_C'], name="온도 (temp_C, °C)", line=dict(color='#ff7f0e', width=2)))
            fig.add_trace(go.Scatter(x=filtered_df['timestamp'], y=filtered_df['pressure_bar'], name="압력 (pressure_bar)", yaxis="y2", line=dict(color='#1f77b4', width=2)))
            
            # Highlight defects
            defects = filtered_df[filtered_df['defect_flag'] == 1]
            fig.add_trace(go.Scatter(x=defects['timestamp'], y=defects['temp_C'], mode='markers', marker=dict(color='red', size=8, symbol='x'), name="불량 발생 시점"))
            
            fig.update_layout(
                title="공정 온도 및 압력 시계열 변화 (불량 마커 표시)",
                xaxis=dict(title="측정 일시"),
                yaxis=dict(title="온도 (°C)", titlefont=dict(color="#ff7f0e"), tickfont=dict(color="#ff7f0e")),
                yaxis2=dict(title="압력 (bar)", titlefont=dict(color="#1f77b4"), tickfont=dict(color="#1f77b4"), overlaying="y", side="right"),
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
            
        elif sensor_choice == "진동 (Vibration)":
            fig = px.line(filtered_df, x='timestamp', y='vibration_mm_s', color='line_id', title="라인별 진동 속도 추이 (vibration_mm_s)")
            fig.add_hline(y=2.8, line_dash="dash", line_color="red", annotation_text="경고 임계치 (2.8 mm/s)")
            st.plotly_chart(fig, use_container_width=True)
            
        elif sensor_choice == "습도 (Humidity)":
            fig = px.line(filtered_df, x='timestamp', y='humidity_pct', color='line_id', title="라인별 챔버 습도 추이 (%)")
            st.plotly_chart(fig, use_container_width=True)
            
        elif sensor_choice == "사이클 타임 (Cycle Time)":
            fig = px.line(filtered_df, x='timestamp', y='cycle_time_sec', color='line_id', title="공정 사이클 타임 추이 (초)")
            fig.add_hline(y=45.0, line_dash="dash", line_color="orange", annotation_text="지연 임계치 (45초)")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("선택된 필터 조건에 해당하는 데이터가 없습니다.")

# ----------------- TAB 2: Benchmarks -----------------
with tab2:
    st.subheader("📊 생산 라인 및 설비 종합 비교")
    
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        # Defect rate by Line
        line_stats = df_clean.groupby('line_id').agg(
            total=('defect_flag', 'count'),
            defects=('defect_flag', 'sum'),
            defect_rate=('defect_flag', lambda x: (x.sum()/len(x)*100))
        ).reset_index()
        fig_line = px.bar(line_stats, x='line_id', y='defect_rate', color='line_id',
                          text=line_stats['defect_rate'].apply(lambda x: f"{x:.1f}%"),
                          title="라인별 불량률 비교 (%)", labels={'line_id': '라인 ID', 'defect_rate': '불량률 (%)'})
        st.plotly_chart(fig_line, use_container_width=True)
        
    with col_b2:
        # Defect rate by Machine
        machine_stats = df_clean.groupby(['machine_id', 'line_id']).agg(
            defect_rate=('defect_flag', lambda x: (x.sum()/len(x)*100))
        ).reset_index()
        fig_mach = px.bar(machine_stats, x='machine_id', y='defect_rate', color='line_id',
                          title="설비(Machine)별 불량률 비교 (%)", labels={'machine_id': '설비 ID', 'defect_rate': '불량률 (%)'})
        st.plotly_chart(fig_mach, use_container_width=True)

    col_b3, col_b4 = st.columns(2)
    with col_b3:
        fig_box = px.box(df_clean, x='shift', y='cycle_time_sec', color='shift',
                         points="outliers", title="주간(DAY) vs 야간(NIGHT) 교대조 사이클 타임 분포",
                         labels={'shift': '교대조', 'cycle_time_sec': '사이클 타임 (초)'})
        st.plotly_chart(fig_box, use_container_width=True)
        
    with col_b4:
        fig_scatter = px.scatter(df_clean, x='temp_C', y='vibration_mm_s', color='defect_flag',
                                 symbol='defect_flag', color_discrete_map={0: '#1f77b4', 1: '#d62728'},
                                 title="온도 vs 진동 산점도 (불량 클러스터)",
                                 labels={'temp_C': '온도 (°C)', 'vibration_mm_s': '진동 (mm/s)', 'defect_flag': '불량 여부'})
        st.plotly_chart(fig_scatter, use_container_width=True)

# ----------------- TAB 3: What-If Defect Simulator -----------------
with tab3:
    st.subheader("🧪 실시간 센서 파라미터 조절 & AI 불량 위험도 예측")
    st.markdown("슬라이더를 조작하여 센서 조건을 변경하면, Random Forest AI 모델이 실시간으로 제품 불량 확률을 예측합니다.")
    
    sim_col1, sim_col2 = st.columns([1, 1])
    
    with sim_col1:
        st.markdown("#### ⚙️ 센서 조건 설정")
        sim_temp = st.slider("온도 (°C)", min_value=150.0, max_value=210.0, value=float(df_clean['temp_C'].median()), step=0.5)
        sim_pressure = st.slider("압력 (bar)", min_value=3.0, max_value=6.0, value=float(df_clean['pressure_bar'].median()), step=0.05)
        sim_vib = st.slider("진동 (mm/s)", min_value=0.2, max_value=4.5, value=float(df_clean['vibration_mm_s'].median()), step=0.05)
        sim_hum = st.slider("습도 (%)", min_value=20.0, max_value=70.0, value=float(df_clean['humidity_pct'].median()), step=0.5)
        sim_cycle = st.slider("사이클 타임 (초)", min_value=20.0, max_value=60.0, value=float(df_clean['cycle_time_sec'].median()), step=0.5)
        
        # Inference
        input_data = pd.DataFrame([[sim_temp, sim_pressure, sim_vib, sim_hum, sim_cycle]], columns=feature_names)
        prob_defect = model.predict_proba(input_data)[0][1] * 100
        
    with sim_col2:
        st.markdown("#### 🎯 AI 예측 결과")
        
        # Gauge chart
        gauge_color = "green" if prob_defect < 30 else ("orange" if prob_defect < 65 else "red")
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=prob_defect,
            title={'text': "불량 발생 예측 확률 (%)", 'font': {'size': 20}},
            number={'suffix': "%", 'font': {'size': 32}},
            gauge={
                'axis': {'range': [0, 100], 'tickwidth': 1},
                'bar': {'color': gauge_color},
                'steps': [
                    {'range': [0, 30], 'color': "rgba(40, 167, 69, 0.2)"},
                    {'range': [30, 65], 'color': "rgba(255, 193, 7, 0.2)"},
                    {'range': [65, 100], 'color': "rgba(220, 53, 69, 0.2)"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 65
                }
            }
        ))
        fig_gauge.update_layout(height=280, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)
        
        if prob_defect < 30:
            st.success(f"🟢 **[정상 / 안전 구간]** 불량 위험도 {prob_defect:.1f}%: 공정 파라미터가 안정적입니다.")
        elif prob_defect < 65:
            st.warning(f"🟡 **[주의 구간]** 불량 위험도 {prob_defect:.1f}%: 진동 또는 압력 수치를 모니터링하세요.")
        else:
            st.error(f"🔴 **[위험 / 불량 경고]** 불량 위험도 {prob_defect:.1f}%: 불량 발생 확률이 높습니다! 공정 조정이 필요합니다.")
            
        # Feature importance
        feat_imp = pd.DataFrame({
            'Feature': ['온도', '압력', '진동', '습도', '사이클타임'],
            'Importance': model.feature_importances_
        }).sort_values('Importance', ascending=True)
        fig_imp = px.bar(feat_imp, x='Importance', y='Feature', orientation='h', title="AI 모델 주요 영향 인자 (Feature Importance)")
        fig_imp.update_layout(height=220, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_imp, use_container_width=True)

# ----------------- TAB 4: Raw Data & Download -----------------
with tab4:
    st.subheader("📋 필터링된 공정 데이터셋")
    st.dataframe(filtered_df[['timestamp', 'line_id', 'machine_id', 'shift', 'temp_C', 'pressure_bar', 'vibration_mm_s', 'humidity_pct', 'cycle_time_sec', 'defect_flag', 'has_sensor_error']], use_container_width=True)
    
    csv_data = filtered_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button(
        label="📥 필터링된 데이터 CSV 다운로드",
        data=csv_data,
        file_name="filtered_process_sensor_data.csv",
        mime="text/csv"
    )
