# Factory Quality Radar — API 설계 문서

## 개요

FastAPI 기반 REST API 서버. 센서 측정값 및 일별 운영 데이터를 수신해
기학습 모델로 불량 확률·불량률을 예측하고, 임계값 초과 시 `alerts.log`에 기록한다.

```
uvicorn api:app --reload --port 8000
```

---

## 엔드포인트 목록

### `POST /api/sensor` — 센서 데이터 수신

센서 1건을 수신해 불량 발생 확률(0~1)을 반환한다.  
확률이 `0.30` 이상이면 `alert: true`가 반환되고 `alerts.log`에 기록된다.

**Request Body**

```json
{
  "line_id":          "C",
  "temp_C":           185.0,
  "pressure_bar":     4.6,
  "vibration_mm_s":   3.2,
  "humidity_pct":     50.0,
  "cycle_time_sec":   35.0
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `line_id` | string | 라인 구분 (`A`, `B`, `C`) |
| `temp_C` | float | 공정 온도 (°C), 정상 범위 150–300 |
| `pressure_bar` | float | 압력 (bar), 정상 범위 0–10 |
| `vibration_mm_s` | float | 진동 (mm/s) |
| `humidity_pct` | float | 습도 (%) |
| `cycle_time_sec` | float | 사이클 타임 (초), 정상 범위 5–100 |

**Response 200**

```json
{
  "line_id":            "C",
  "defect_probability": 0.5523,
  "alert":              true,
  "threshold":          0.3,
  "timestamp":          "2026-08-20T14:35:22"
}
```

---

### `POST /api/daily` — 일별 운영 데이터 수신

당일 가동 실측값을 수신해 **다음날 예상 불량률**을 반환한다.  
예측 불량률이 학습 데이터 상위 20% 임계값 이상이면 `alert: true`.

**Request Body**

```json
{
  "line_id":           "A",
  "plan_min":          480.0,
  "run_min":           420.0,
  "downtime_min":      60.0,
  "prod_qty":          500.0,
  "good_qty":          475.0,
  "energy_kwh":        210.0,
  "defect_rate_today": 0.07
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `line_id` | string | 라인 구분 |
| `plan_min` | float | 계획 가동 시간 (분) |
| `run_min` | float | 실제 가동 시간 (분) |
| `downtime_min` | float | 비가동 시간 (분) |
| `prod_qty` | float | 생산 수량 |
| `good_qty` | float | 양품 수량 |
| `energy_kwh` | float | 에너지 소비 (kWh) |
| `defect_rate_today` | float | 오늘 실측 불량률 (기본값 `0.06`) |

**Response 200**

```json
{
  "line_id":               "A",
  "defect_rate_forecast":  0.0812,
  "risk_level":            "경고",
  "alert":                 true,
  "threshold":             0.0796,
  "timestamp":             "2026-08-20T14:35:22"
}
```

---

### `GET /api/status` — 모니터링 버퍼 조회

`monitoring_buffer.json` 전체 내용을 반환한다.  
Streamlit 모니터링 페이지가 10초마다 이 파일을 직접 읽어 갱신한다.

**Response 200**

```json
{
  "sensors": {
    "C": {
      "timestamp": "2026-08-20T14:35:22",
      "values": { "line_id": "C", "temp_C": 185.0, "..." : "..." },
      "defect_probability": 0.5523,
      "alert": true
    }
  },
  "daily": {
    "A": {
      "timestamp": "2026-08-20T14:30:00",
      "input": { "..." : "..." },
      "defect_rate_forecast": 0.0812,
      "risk_level": "경고",
      "alert": true
    }
  },
  "last_updated": "2026-08-20T14:35:22"
}
```

---

### `GET /api/forecast` — 최신 모델 예측 조회

학습 완료 모델 기준의 라인별 불량률 예측을 반환한다 (정적 값).

**Response 200**

```json
[
  { "line_id": "C", "prediction": 0.0843, "risk_level": "경고" },
  { "line_id": "B", "prediction": 0.0666, "risk_level": "주의" },
  { "line_id": "A", "prediction": 0.0460, "risk_level": "정상" }
]
```

---

## 알림 임계값

| 소스 | 필드 | 임계값 | 기준 |
|------|------|--------|------|
| `/api/sensor` | `defect_probability` | **0.30** | 고정값 |
| `/api/daily` | `defect_rate_forecast` | **q80 ≈ 0.080** | 학습 데이터 상위 20% |

---

## 알림 파일 형식 (`alerts.log`)

한 행 = 이벤트 1건 (JSON Lines)

```json
{"timestamp": "2026-08-20T14:35:22", "source": "sensor", "line_id": "C", "value": 0.5523, "threshold": 0.3, "context": {"temp_C": 185.0, "..."}}
{"timestamp": "2026-08-20T14:30:00", "source": "daily",  "line_id": "A", "value": 0.0812, "threshold": 0.0796, "context": {"plan_min": 480, "..."}}
```

---

## 테스트 예시 (PowerShell)

```powershell
# 센서 — 고온·고진동 (경고 발생)
curl -X POST http://localhost:8000/api/sensor `
  -H "Content-Type: application/json" `
  -d '{"line_id":"C","temp_C":185,"pressure_bar":4.6,"vibration_mm_s":3.2,"humidity_pct":50,"cycle_time_sec":35}'

# 일별 — 비가동 60분, 불량률 8%
curl -X POST http://localhost:8000/api/daily `
  -H "Content-Type: application/json" `
  -d '{"line_id":"A","plan_min":480,"run_min":420,"downtime_min":60,"prod_qty":500,"good_qty":475,"energy_kwh":210,"defect_rate_today":0.08}'

# 현황 확인
curl http://localhost:8000/api/status
curl http://localhost:8000/api/forecast
```

---

## 실행 순서

```powershell
# 1. 의존성 설치
pip install fastapi "uvicorn[standard]" streamlit-autorefresh

# 2. API 서버 기동 (터미널 1)
uvicorn api:app --reload --port 8000

# 3. Streamlit 앱 기동 (터미널 2)
python -m streamlit run app.py
```

Swagger UI: `http://localhost:8000/docs`
