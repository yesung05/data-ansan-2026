import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from src.config import ORIGINAL_DATA_PATH, FIGURES_DIR, REPORTS_DIR, set_korean_font

class ProcessSensorAnalyzer:
    def __init__(self, file_path=ORIGINAL_DATA_PATH):
        self.file_path = Path(file_path)
        self.excel_data = None
        self.df = None
        set_korean_font()

    def load_data(self):
        print(f'[*] Loading Excel file from: {self.file_path}')
        if not self.file_path.exists():
            raise FileNotFoundError(f'File not found: {self.file_path}')
        
        # Check sheet names
        xl = pd.ExcelFile(self.file_path)
        print(f'[*] Sheet names found: {xl.sheet_names}')
        
        # Load the first sheet by default or primary sheet
        self.df = pd.read_excel(self.file_path, sheet_name=0)
        print(f'[*] Successfully loaded primary sheet. Shape: {self.df.shape}')
        return self.df

    def inspect_overview(self):
        print('\n=== Data Overview ===')
        print(f'Total Rows: {len(self.df)}, Total Columns: {len(self.df.columns)}')
        print('\n--- Column Info & Missing Values ---')
        info_df = pd.DataFrame({
            'Dtype': self.df.dtypes,
            'Non-Null Count': self.df.notnull().sum(),
            'Null Count': self.df.isnull().sum(),
            'Null Ratio (%)': (self.df.isnull().sum() / len(self.df) * 100).round(2),
            'Unique Values': self.df.nunique()
        })
        print(info_df)
        info_df.to_csv(REPORTS_DIR / 'column_overview.csv', encoding='utf-8-sig')
        return info_df

    def get_summary_statistics(self):
        print('\n=== Summary Statistics (Numerical Columns) ===')
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            desc = self.df[numeric_cols].describe().T
            desc['skew'] = self.df[numeric_cols].skew()
            desc['kurtosis'] = self.df[numeric_cols].kurt()
            print(desc.round(4))
            desc.round(4).to_csv(REPORTS_DIR / 'numeric_summary_statistics.csv', encoding='utf-8-sig')
            return desc
        else:
            print('No numeric columns found.')
            return None

    def plot_distributions(self):
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) == 0:
            return

        print('\n[*] Generating distribution plots...')
        n_cols = min(4, len(numeric_cols))
        n_rows = (len(numeric_cols) + n_cols - 1) // n_cols

        fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 4 * n_rows))
        if n_rows == 1 and n_cols == 1:
            axes = np.array([axes])
        axes = axes.flatten()

        for idx, col in enumerate(numeric_cols):
            sns.histplot(self.df[col].dropna(), kde=True, ax=axes[idx], color='royalblue')
            axes[idx].set_title(f'{col} Distribution', fontsize=11)
            axes[idx].grid(True, linestyle='--', alpha=0.5)

        # Hide extra empty subplots
        for idx in range(len(numeric_cols), len(axes)):
            fig.delaxes(axes[idx])

        plt.tight_layout()
        save_path = FIGURES_DIR / 'distributions.png'
        plt.savefig(save_path, dpi=300)
        plt.close()
        print(f'[+] Distribution plots saved to: {save_path}')

    def plot_correlation(self):
        numeric_df = self.df.select_dtypes(include=[np.number])
        if numeric_df.shape[1] > 1:
            print('\n[*] Generating correlation heatmap...')
            corr = numeric_df.corr()
            plt.figure(figsize=(max(8, len(numeric_df.columns)*0.8), max(6, len(numeric_df.columns)*0.6)))
            sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', vmin=-1, vmax=1, cbar=True)
            plt.title('Sensor Features Correlation Matrix', fontsize=14)
            plt.tight_layout()
            save_path = FIGURES_DIR / 'correlation_matrix.png'
            plt.savefig(save_path, dpi=300)
            plt.close()
            print(f'[+] Correlation heatmap saved to: {save_path}')

    def plot_time_series_if_applicable(self):
        # Look for datetime columns
        datetime_cols = self.df.select_dtypes(include=['datetime', 'datetime64']).columns
        if len(datetime_cols) == 0:
            # Check if any column name contains time / date / timestamp
            for col in self.df.columns:
                if any(kw in str(col).lower() for kw in ['time', 'date', 'timestamp', '일시', '시간']):
                    try:
                        self.df[col] = pd.to_datetime(self.df[col])
                        datetime_cols = [col]
                        break
                    except Exception:
                        pass
        
        if len(datetime_cols) > 0:
            time_col = datetime_cols[0]
            print(f'\n[*] Found time column: {time_col}. Generating time-series trends...')
            numeric_cols = [c for c in self.df.select_dtypes(include=[np.number]).columns if c != time_col]
            
            if len(numeric_cols) > 0:
                plt.figure(figsize=(14, 6))
                for col in numeric_cols[:5]: # Plot up to top 5 features
                    plt.plot(self.df[time_col], self.df[col], label=str(col), alpha=0.8)
                plt.xlabel(str(time_col))
                plt.ylabel('Sensor Values')
                plt.title('Process Sensor Time Series Trend')
                plt.legend()
                plt.grid(True, linestyle='--', alpha=0.5)
                plt.tight_layout()
                save_path = FIGURES_DIR / 'time_series_trend.png'
                plt.savefig(save_path, dpi=300)
                plt.close()
                print(f'[+] Time series trend saved to: {save_path}')
