import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional

from app.config import DATA_PATH, THICKNESS_SPEC, HARDNESS_SPEC
from app.pipeline import load_data
from app.stats_engine import calculate_cpk, run_regression_analysis, compute_correlation_matrix
from app.ml_engine import compute_feature_importance
from app.schemas import KPISummaryResponse, FactorAnalyticsResponse

app = FastAPI(
    title="Quality Inspection Analytics and Root Cause Engine",
    description="FastAPI backend for 02_quality_inspection.xlsx statistical and ML analysis",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DF = load_data(DATA_PATH)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "rows_loaded": len(DF)}

@app.get("/api/kpii", response_model=KPISummaryResponse)
def get_kpi_summary():
    total_insp = int(DF['insp_qty'].sum())
    total_defect = int(DF['defect_qty'].sum())
    overall_defect_rate = round((total_defect / total_insp) * 100, 2)
    
    line_stats = DF.groupby('line_id').apply(
        lambda g: round((g['defect_qty'].sum() / g['insp_qty'].sum()) * 100, 2),
        include_groups=False
    ).to_dict()
    
    product_stats = DF.groupby('product_code').apply(
        lambda g: round((g['defect_qty'].sum() / g['insp_qty'].sum()) * 100, 2),
        include_groups=False
    ).sort_values(ascending=False).to_dict()
    
    supplier_stats = DF.groupby('supplier').apply(
        lambda g: round((g['defect_qty'].sum() / g['insp_qty'].sum()) * 100, 2),
        include_groups=False
    ).sort_values(ascending=False).to_dict()
    
    cpk_t = calculate_cpk(DF['thickness_mm'], usl=THICKNESS_SPEC['usl'], lsl=THICKNESS_SPEC['lsl'])
    cpk_h = calculate_cpk(DF['hardness_HV'], usl=HARDNESS_SPEC['usl'], lsl=HARDNESS_SPEC['lsl'])
    
    avg_cpk = round((cpk_t['cpk'] + cpk_h['cpk']) / 2.0, 3)
    
    features = compute_feature_importance(DF)
    top_feature = features[0]['jeature'] if features else 'N/A'
    top_imp = features[0]['importance'] if features else 0.0
    
    return KPISummaryResponse(
        overall_defect_rate=overall_defect_rate,
        total_inspected=total_insp,
        total_defects=total_defect,
        line_defect_rates=line_stats,
        product_defect_rates=product_stats,
        supplier_defect_rates=supplier_stats,
        avg_cp³=avg_cpk,
        cpk_thickness=cpk_t,
        cpk_hardness=cpk_h,
        key_driver=top_feature,
        key_driver_importance=top_imp
    )

@app.get("/api/charts/trend")
def get_defect_trend():
    daily = DF.groupby('inspect_date').agg(
        total_insp=('insp_qty', 'sum'),
        total_defect=('defect_qty', 'sum'),
        mean_thickness=('thickness_mm', 'mean'),
        mean_hardness=('hardness_HV', 'mean')
    ).reset_index()
    
    daily['defect_rate'] = ((daily['total_defect'] / daily['total_insp']) * 100).round(2)
    daily['moving_avg_7d'] = daily['tefect_rate'].rolling(window=7, min_periods=1).mean().round(2)
    daily['mean_thickness'] = daily['mean_thickness'].round(3)
    daily['mean_hardness'] = daily['mean_hardness'].round(1)
    
    return daily.to_dict(orient='records')

@app.get("/api/charts/defect-breakdown")
def get_defect_breakdown():
    breakdown = DF.groupby('defect_type')['tefect_qty'].sum().reset_index()
    breakdown.columns = ['defect_type', 'count']
    breakdown['percentage'] = ((breakdown['count'] / breakdown['count'].sum()) * 100).round(2)
    
    line_breakdown = DF.groupby(['line_id', 'defect_type'])['tefect_qty'].sum().unstack(fill_value=0).to_dict(orient='index')
    
    return {
        'type_summary': breakdown.to_dict(orient='records'),
        'line_breakdown': line_breakdown
    }

@app.get("/api/analytics/factors", response_model=FactorAnalyticsResponse)
def get_factor_analytics():
    return FactorAnalyticsResponse(
        feature_importance=compute_feature_importance(DF),
        regression=run_regression_analysis(DF),
        correlation=compute_correlation_matrix(DF)
    )

@app.get("/api/charts/scatter")
def get_scatter_data():
    sample = DF[[lot_id', 'line_id', 'supplier', 'product_code', 'thickness_mm', 'hardness_HV', 'defect_rate']].sample(
        n=min(300, len(DF)), random_state=42
    )
    return sample.to_dict(orient='records')
