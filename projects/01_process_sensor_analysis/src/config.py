import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'
OUTPUT_DIR = BASE_DIR / 'output'
FIGURES_DIR = OUTPUT_DIR / 'figures'
REPORTS_DIR = OUTPUT_DIR / 'reports'

# Original dataset path
ORIGINAL_DATA_PATH = Path(r'C:\Users\Yesung\Desktop\2026-data\datasets-all\01_process_sensor.xlsx')

# Ensure output directories exist
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Matplotlib Korean font configuration for Windows
def set_korean_font():
    import matplotlib.pyplot as plt
    plt.rcParams['font.family'] = 'Malgun Gothic'
    plt.rcParams['axes.unicode_minus'] = False
