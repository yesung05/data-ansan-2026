from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_PATH = BASE_DIR / 'data' / '02_quality_inspection.xlsx'
OUTPUT_DIR = BASE_DIR / 'output'

# Specification limits
THICKNESS_SPEC = {
    'target': 2.50,
    'usl': 2.60,
    'lsl': 2.40,
    'unit': 'mm'
}

HARDNESS_SPEC = {
    'target': 210.0,
    'usl': 245.0,
    'lsl': 175.0,
    'unit': 'HV'
}
