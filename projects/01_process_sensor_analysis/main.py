import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.analyzer import ProcessSensorAnalyzer

def main():
    print('='*60)
    print('Starting Process Sensor Data Analysis')
    print('='*60)
    
    analyzer = ProcessSensorAnalyzer()
    analyzer.load_data()
    analyzer.inspect_overview()
    analyzer.get_summary_statistics()
    analyzer.plot_distributions()
    analyzer.plot_correlation()
    analyzer.plot_time_series_if_applicable()
    
    print('\n' + '='*60)
    print('Analysis pipeline completed successfully!')
    print('='*60)

if __name__ == '__main__':
    main()
