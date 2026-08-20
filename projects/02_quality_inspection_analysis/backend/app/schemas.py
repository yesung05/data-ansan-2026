from pydantic import BaseModel
from typing import Dict, List, Any, Optional

class KPISummaryResponse(BaseModel):
    overall_defect_rate: float
    total_inspected: int
    total_defects: int
    line_defect_rates: Dict[str, float]
    product_defect_rates: Dict[str, float]
    supplier_defect_rates: Dict[str, float]
    avg_cp³: float
    cpk_thickness: Dict[str, Any]
    cpk_hardness: Dict[str, Any]
    key_driver: str
    key_driver_importance: float

class DailyTrendItem(BaseModel):
    inspect_date: str
    total_insp: int
    total_defect: int
    defect_rate: float
    moving_avg_7d: float
    mean_thickness: float
    mean_hardness: float

class FactorAnalyticsResponse(BaseModel):
    feature_importance: List[Dict[str, Any]]
    regression: List[Dict[str, Any]]
    correlation: Dict[str, Any]
