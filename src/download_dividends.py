"""
下载 Top 20 股票的分红数据
"""
import yfinance as yf
import os
import time

TICKERS = [
    "NVDA", "AAPL", "GOOGL", "MSFT", "AMZN", "META", "TSM", "AVGO",
    "TSLA", "BRK-B", "WMT", "LLY", "005930.KS", "JPM", "0700.HK",
    "XOM", "V", "JNJ", "ASML", "MU"
]

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

def download_dividends():
    os.makedirs(DATA_DIR, exist_ok=True)
    
    for ticker in TICKERS:
        print(f"📥 Downloading dividends for {ticker}...")
        try:
            t = yf.Ticker(ticker)
            divs = t.dividends
            if divs is None or len(divs) == 0:
                print(f"  ℹ️ No dividends for {ticker}")
                continue
            
            # 过滤 2010-2025
            divs = divs["2010-01-01":"2025-12-31"]
            
            safe_name = ticker.replace(".", "_")
            filepath = os.path.join(DATA_DIR, f"{safe_name}_dividends.csv")
            divs.to_csv(filepath)
            print(f"  ✅ {len(divs)} dividend records saved → {filepath}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        time.sleep(0.5)

if __name__ == "__main__":
    download_dividends()
