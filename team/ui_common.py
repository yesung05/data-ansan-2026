"""Streamlit 페이지가 공유하는 모델 로딩과 표시 유틸리티."""

import streamlit as st

from quality_risk_model import train_and_evaluate


@st.cache_resource(show_spinner="품질 예측 모델을 학습하고 있습니다...")
def _cached_results(augment: bool):
    return train_and_evaluate(augment=augment)


def sidebar_augment_toggle() -> bool:
    """사이드바에 데이터 증강 토글을 그리고 현재 값을 반환한다."""
    return st.sidebar.toggle(
        "데이터 증강 (5×)",
        key="augment",
        value=False,
        help="학습 데이터에 가우시안 노이즈를 더해 5배로 늘립니다. 테스트 셋은 그대로 유지됩니다.",
    )


def get_results(augment: bool = False):
    return _cached_results(augment)


def risk_label(result, prediction: float) -> str:
    q50, q80 = result["risk_thresholds"]
    if prediction >= q80:
        return "경고"
    if prediction >= q50:
        return "주의"
    return "정상"
