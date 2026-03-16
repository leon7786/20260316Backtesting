"""
下载 Top 20 全球市值股票的历史日线数据 (2010-2025)
"""
import yfinance as yf
import pandas as pd
import os
import time

# 20只股票 ticker 映射
STOCKS = {
    "NVDA": "NVIDIA",
    "AAPL": "Apple",
    "GOOGL": "Alphabet",
    "MSFT": "Microsoft",
    "AMZN": "Amazon",
    "META": "Meta Platforms",
    "TSM": "TSMC (台积电)",
    "AVGO": "Broadcom",
    "TSLA": "Tesla",
    "BRK-B": "Berkshire Hathaway",
    "WMT": "Walmart",
    "LLY": "Eli Lilly",
    "005930.KS": "Samsung Electronics (三星电子)",
    "JPM": "JPMorgan Chase",
    "0700.HK": "Tencent Holdings (腾讯)",
    "XOM": "Exxon Mobil",
    "V": "Visa",
    "JNJ": "Johnson & Johnson",
    "ASML": "ASML Holding",
    "MU": "Micron Technology",
}

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

def download_all():
    os.makedirs(DATA_DIR, exist_ok=True)
    
    results = {}
    for ticker, name in STOCKS.items():
        print(f"📥 Downloading {name} ({ticker})...")
        try:
            df = yf.download(ticker, start="2010-01-01", end="2025-12-31", auto_adjust=True, progress=False)
            if df.empty:
                print(f"  ⚠️ No data for {ticker}")
                continue
            
            # 清理列名（yfinance 有时返回 MultiIndex）
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # 保存 CSV
            safe_name = ticker.replace(".", "_")
            filepath = os.path.join(DATA_DIR, f"{safe_name}.csv")
            df.to_csv(filepath)
            rows = len(df)
            results[ticker] = {"name": name, "rows": rows, "file": f"{safe_name}.csv"}
            print(f"  ✅ {rows} rows saved → {filepath}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        time.sleep(0.5)  # 避免限流
    
    # 保存 metadata
    meta = pd.DataFrame.from_dict(results, orient="index")
    meta.to_csv(os.path.join(DATA_DIR, "_metadata.csv"))
    print(f"\n📊 Done! Downloaded {len(results)}/{len(STOCKS)} stocks.")
    return results

if __name__ == "__main__":
    download_all()
