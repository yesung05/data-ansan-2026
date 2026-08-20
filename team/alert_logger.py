"""alerts.log 기록·읽기 유틸리티. API 서버와 Streamlit 모니터링 페이지가 공유한다."""

from __future__ import annotations

import json
import datetime
from pathlib import Path

ALERT_LOG = Path(__file__).resolve().parent / "alerts.log"


def write_alert(
    source: str,
    line: str,
    value: float,
    threshold: float,
    context: dict,
) -> None:
    """임계값 초과 이벤트를 alerts.log에 JSON 행으로 기록한다."""
    entry = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "source": source,       # "sensor" | "daily"
        "line_id": line,
        "value": round(value, 4),
        "threshold": round(threshold, 4),
        "context": context,
    }
    with open(ALERT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_recent_alerts(n: int = 10) -> list[dict]:
    """최근 n건의 알림을 최신순으로 반환한다. 파일이 없으면 빈 리스트."""
    if not ALERT_LOG.exists():
        return []
    lines = ALERT_LOG.read_text(encoding="utf-8").strip().splitlines()
    recent = lines[-n:][::-1]
    result = []
    for line in recent:
        try:
            result.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return result
