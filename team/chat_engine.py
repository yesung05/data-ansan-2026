"""자연어 제조 질문을 회귀 모델 시뮬레이션으로 연결하는 안전한 어댑터."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def load_local_env() -> None:
    """의존성 없이 프로젝트 루트의 .env 값을 환경 변수로 읽는다."""
    env_file = Path(__file__).resolve().parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_local_env()


def parse_question(question: str, default_line: str) -> tuple[str, dict[str, float], list[str]]:
    """자주 쓰는 한국어 조건 변경 표현을 모델의 제한된 입력값으로 변환한다.

    퍼센트는 상대 변화가 아닌 퍼센트포인트(%p)로 해석한다.
    """
    normalized = question.replace(" ", "")
    line_match = re.search(r"([ABC])라인", normalized, flags=re.IGNORECASE)
    line = line_match.group(1).upper() if line_match else default_line
    changes: dict[str, float] = {}
    notes: list[str] = []

    def amount_after(words: str) -> float | None:
        match = re.search(words + r"[^0-9]{0,12}(\d+(?:\.\d+)?)%", normalized)
        return float(match.group(1)) / 100 if match else None

    for words, field, label, low, high in [
        (r"(?:비가동률|비가동)", "downtime_rate", "비가동률", 0.0, 0.30),
        (r"(?:수율|양품률)", "yield_rate", "양품률", 0.80, 1.0),
    ]:
        value = amount_after(words)
        if value is None:
            continue
        segment = re.search(words + r".{0,25}", normalized)
        text = segment.group(0) if segment else normalized
        if re.search(r"(줄|감소|낮|내리|개선)", text):
            changes[field] = -value
            notes.append(f"{label} {value:.1%}p 감소")
        elif re.search(r"(늘|증가|올리|높)", text):
            changes[field] = value
            notes.append(f"{label} {value:.1%}p 증가")

    for words, field, label in [
        (r"(?:생산량|생산)", "production_factor", "생산량"),
        (r"(?:에너지|전력)", "energy_factor", "단위당 에너지"),
    ]:
        value = amount_after(words)
        if value is None:
            continue
        segment = re.search(words + r".{0,25}", normalized)
        text = segment.group(0) if segment else normalized
        if re.search(r"(줄|감소|낮|내리)", text):
            changes[field] = 1 - value
            notes.append(f"{label} {value:.1%} 감소")
        elif re.search(r"(늘|증가|올리|높)", text):
            changes[field] = 1 + value
            notes.append(f"{label} {value:.1%} 증가")
    return line, changes, notes


def simulate_from_changes(result: dict[str, Any], line: str, changes: dict[str, float]) -> dict[str, Any]:
    """허용된 운영 변수만 변경해 로컬 회귀 모델을 실행한다."""
    base = result["forecast"].loc[result["forecast"]["line_id"] == line].iloc[0].copy()
    scenario = base.copy()
    scenario["downtime_rate"] = float(np.clip(base["downtime_rate"] + changes.get("downtime_rate", 0), 0, 0.30))
    scenario["availability"] = 1 - scenario["downtime_rate"]
    scenario["downtime_min"] = scenario["plan_min"] * scenario["downtime_rate"]
    scenario["run_min"] = scenario["plan_min"] - scenario["downtime_min"]
    scenario["yield_rate"] = float(np.clip(base["yield_rate"] + changes.get("yield_rate", 0), 0.80, 1.0))
    scenario["prod_qty"] = scenario["prod_qty"] * changes.get("production_factor", 1.0)
    scenario["good_qty"] = scenario["prod_qty"] * scenario["yield_rate"]
    scenario["energy_per_unit"] = scenario["energy_per_unit"] * changes.get("energy_factor", 1.0)
    scenario["energy_kwh"] = scenario["energy_per_unit"] * scenario["prod_qty"]
    features = result["numeric_features"] + result["categorical_features"]
    prediction = float(np.clip(result["model"].predict(pd.DataFrame([scenario[features]]))[0], 0, 1))
    return {"base": base, "scenario": scenario, "prediction": prediction, "delta": prediction - float(base["prediction"])}


def explain_with_gpt(question: str, simulation: dict[str, Any], notes: list[str]) -> tuple[str, bool]:
    """계산 결과를 GPT가 설명하게 한다. 키가 없으면 결정론적 설명으로 동작한다."""
    base = simulation["base"]
    change_text = ", ".join(notes) if notes else "운영 조건 변경을 인식하지 못함"
    facts = (
        f"질문: {question}\n라인: {base['line_id']}\n적용 변경: {change_text}\n"
        f"기준 예상 불량률: {base['prediction']:.2%}\n시뮬레이션 예상 불량률: {simulation['prediction']:.2%}\n"
        f"변화: {simulation['delta']:+.2%}p\n기준 비가동률: {base['downtime_rate']:.2%}\n"
        f"조정 비가동률: {simulation['scenario']['downtime_rate']:.2%}\n기준 양품률: {base['yield_rate']:.2%}\n"
        f"조정 양품률: {simulation['scenario']['yield_rate']:.2%}"
    )
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from openai import OpenAI

            model = os.getenv("OPENAI_MODEL", "gpt-5.6")
            prompt = (
                "당신은 제조 품질 분석 챗봇입니다. 아래의 계산 결과만 근거로 한국어로 3문장 이내로 답하세요. "
                "인과관계를 단정하지 말고, 예측 불량률·변화폭·점검 행동을 설명하세요. 계산값을 바꾸거나 새 수치를 만들지 마세요.\n\n"
                + facts
            )
            response = OpenAI(api_key=api_key).responses.create(model=model, input=prompt)
            return response.output_text, True
        except Exception as error:  # 앱은 API 오류에도 로컬 시뮬레이션을 유지한다.
            return f"GPT 설명을 불러오지 못했습니다: {error}", False
    direction = "상승" if simulation["delta"] > 0 else "하락" if simulation["delta"] < 0 else "변화 없음"
    text = (
        f"{base['line_id']} 라인에서 {change_text}으로 해석했습니다. "
        f"회귀 모델의 예상 불량률은 {base['prediction']:.2%}에서 {simulation['prediction']:.2%}로 {abs(simulation['delta']):.2%}p {direction}합니다. "
        "이 결과는 과거 패턴 기반의 참고 예측이므로, 실제 적용 전에는 해당 라인의 비가동 사유와 최근 검사 결과를 함께 점검하세요."
    )
    return text, False
