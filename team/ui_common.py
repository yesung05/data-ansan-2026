"""Streamlit 페이지가 공유하는 모델 로딩과 표시 유틸리티."""

import streamlit as st

from quality_risk_model import train_and_evaluate


@st.cache_resource(show_spinner="품질 예측 모델을 학습하고 있습니다...")
def get_results():
    return train_and_evaluate()


def risk_label(result, prediction: float) -> str:
    targets = result["dataset"].dropna(subset=["target_defect_rate"])["target_defect_rate"]
    if prediction >= targets.quantile(0.8):
        return "경고"
    if prediction >= targets.quantile(0.5):
        return "주의"
    return "정상"
