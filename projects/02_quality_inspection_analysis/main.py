import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / 'backend'))

from app.config import DATA_PATH, THICKNESS_SPEC, HARDNESS_SPEC
from app.pipeline import load_data
from app.stats_engine import calculate_cpk, run_regression_analysis
from app.ml_engine import compute_feature_importance

def main():
    print("==================================================================")
    print(" [02_quality_inspection.xlsx] Statistical & ML EDA Report")
    print("==================================================================")
    df = load_data(DATA_PATH)
    print(f"Total Rows Loaded: {len(df):,} lots")
    
    total_insp = df['insp_qty'].sum()
    total_def = df['defect_qty'].sum()
    overall_rate = (total_def / total_insp) * 100
    print(f"Total Inspected Quantity: {total_insp:,} pcs")
    print(f"Total Defect Quantity:    {total_def:,} pcs")
    print(f"Overall Weighted Defect Rate: {overall_rate:.2f}%\n")
    
    print("--- 1. Defect Rate by Process Line ---")
    line_grp = df.groupby('line_id').apply(lambda g: (g['defect_qty'].sum() / g['insp_qty'].sum()) * 100, include_groups=False)
    for line, rate in line_grp.items():
        print(f"  Line {line}: {rate:.2f}%")
        
    print("\n--- 2. Defect Rate by Supplier ---")
    sup_grp = df.groupby('supplier').apply(lambda g: (g['defect_qty'].sum() / g['insp_qty'].sum()) * 100, include_groups=False)
    for sup, rate in sup_grp.items():
        print(f"  Supplier {sup}: {rate:.2f}%")
        
    print("\n--- 3. Process Capability Analysis (Cp / Cpk) ---")
    cpk_t = calculate_cpk(df['thickness_mm'], usl=THICKNESS_SPEC['usl'], lsl=THICKNESS_SPEC['lsl'])
    print(f"  [Thickness (mm)] USL={THICKNESS_SPEC['usl']}, LSL={THICKNESS_SPEC['lsl']}")
    print(f"    Mean={cpk_t['mean']}, Std={cpk_t['std']}")
    print(f"    Cp={cpk_t['cp']}, CPU={cpk_t['cpu']}, CPL={cpk_t['cpl']}, Cpk={cpk_t['cpk']}")
    if cpk_t['cpk'] < 1.0:
        print("    * Status: Unacceptable / High Process Variation (Cpk < 1.00)")
    
    cpk_h = calculate_cpk(df['hardness_HV'], usl=HARDNESS_SPEC['usl'], lsl=HARDNESS_SPEC['lsl'])
    print(f"  [Hardness (HV)] USL={HARDNESS_SPEC['usl']}, LSL={HARDNESS_SPEC['lsl']}")
    print(f"    Mean={cpk_h['mean']}, Std={cpk_h['std']}")
    print(f"    Cp={cpk_h['cp']}, CPU={cpk_h['cpu']}, CPL={cpk_h['cpl']}, Cpk={cpk_h['cpk']}")
    
    print("\n--- 4. Random Forest Feature Importance (Top Key Drivers) ---")
    importances = compute_feature_importance(df)
    for rank, item in enumerate(importances[:6], 1):
        print(f"  {rank}. {item['feature']}: {item['importance']}%")
        
    print("\n--- 5. Statistically Significant Factors (OLS Regression, p < 0.05) ---")
    reg = run_regression_analysis(df)
    for r in reg:
        if r['is_significant']:
            print(f"  - {r['variable']}: Coef={r['coef']}, t-stat={r['t_stat']}, p-value={r['p_value']}")
            
    print("\n==================================================================")
    print(" Report Generation Completed Successfully!")
    print("==================================================================")

if __name__ == '__main__':
    main()
