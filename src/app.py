"""
股票看板 / 回测界面
端口: 5005
"""
import os
import json
import pandas as pd
import plotly
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from flask import Flask, render_template, jsonify, request

app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"),
            static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "static"))

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# 股票映射
STOCKS = {
    "NVDA": {"name": "NVIDIA", "flag": "🇺🇸"},
    "AAPL": {"name": "Apple", "flag": "🇺🇸"},
    "GOOGL": {"name": "Alphabet", "flag": "🇺🇸"},
    "MSFT": {"name": "Microsoft", "flag": "🇺🇸"},
    "AMZN": {"name": "Amazon", "flag": "🇺🇸"},
    "META": {"name": "Meta Platforms", "flag": "🇺🇸"},
    "TSM": {"name": "TSMC (台积电)", "flag": "🇹🇼"},
    "AVGO": {"name": "Broadcom", "flag": "🇺🇸"},
    "TSLA": {"name": "Tesla", "flag": "🇺🇸"},
    "BRK-B": {"name": "Berkshire Hathaway", "flag": "🇺🇸"},
    "WMT": {"name": "Walmart", "flag": "🇺🇸"},
    "LLY": {"name": "Eli Lilly", "flag": "🇺🇸"},
    "005930.KS": {"name": "Samsung (三星)", "flag": "🇰🇷"},
    "JPM": {"name": "JPMorgan Chase", "flag": "🇺🇸"},
    "0700.HK": {"name": "Tencent (腾讯)", "flag": "🇨🇳"},
    "XOM": {"name": "Exxon Mobil", "flag": "🇺🇸"},
    "V": {"name": "Visa", "flag": "🇺🇸"},
    "JNJ": {"name": "Johnson & Johnson", "flag": "🇺🇸"},
    "ASML": {"name": "ASML Holding", "flag": "🇳🇱"},
    "MU": {"name": "Micron Technology", "flag": "🇺🇸"},
}

def load_stock_data(ticker):
    """加载单只股票 CSV 数据"""
    safe_name = ticker.replace(".", "_")
    filepath = os.path.join(DATA_DIR, f"{safe_name}.csv")
    if not os.path.exists(filepath):
        return None
    df = pd.read_csv(filepath, index_col=0, parse_dates=True)
    return df

def run_backtest(initial_investment=1000):
    """
    简单回测：每只股票在数据起始日投入 $1000，持有到最后一天
    """
    results = []
    for ticker, info in STOCKS.items():
        df = load_stock_data(ticker)
        if df is None or df.empty:
            continue
        
        close_col = "Close"
        if close_col not in df.columns:
            # 尝试其他可能的列名
            for col in df.columns:
                if "close" in col.lower():
                    close_col = col
                    break
        
        if close_col not in df.columns:
            continue
        
        prices = df[close_col].dropna()
        if len(prices) < 2:
            continue
        
        start_price = prices.iloc[0]
        end_price = prices.iloc[-1]
        start_date = prices.index[0]
        end_date = prices.index[-1]
        
        shares = initial_investment / start_price
        final_value = shares * end_price
        total_return = (final_value - initial_investment) / initial_investment * 100
        
        # 年化收益率
        years = (end_date - start_date).days / 365.25
        if years > 0:
            cagr = ((final_value / initial_investment) ** (1 / years) - 1) * 100
        else:
            cagr = 0
        
        # 最大回撤
        cummax = prices.cummax()
        drawdown = (prices - cummax) / cummax
        max_drawdown = drawdown.min() * 100
        
        results.append({
            "ticker": ticker,
            "name": info["name"],
            "flag": info["flag"],
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "start_price": round(float(start_price), 2),
            "end_price": round(float(end_price), 2),
            "initial": initial_investment,
            "final_value": round(float(final_value), 2),
            "total_return_pct": round(float(total_return), 2),
            "cagr_pct": round(float(cagr), 2),
            "max_drawdown_pct": round(float(max_drawdown), 2),
            "years": round(float(years), 1),
        })
    
    # 按最终价值排序
    results.sort(key=lambda x: x["final_value"], reverse=True)
    return results

def generate_portfolio_chart(results):
    """生成组合总览图"""
    fig = go.Figure()
    
    for r in results:
        df = load_stock_data(r["ticker"])
        if df is None:
            continue
        
        close_col = "Close"
        if close_col not in df.columns:
            for col in df.columns:
                if "close" in col.lower():
                    close_col = col
                    break
        
        prices = df[close_col].dropna()
        # 归一化为 $1000 起始
        normalized = prices / prices.iloc[0] * 1000
        
        fig.add_trace(go.Scatter(
            x=normalized.index,
            y=normalized.values,
            mode='lines',
            name=f'{r["flag"]} {r["name"]}',
            hovertemplate=f'{r["name"]}<br>日期: %{{x}}<br>价值: $%{{y:,.0f}}<extra></extra>'
        ))
    
    fig.update_layout(
        title="📈 各 $1,000 投资增长曲线 (2010-2025)",
        xaxis_title="日期",
        yaxis_title="投资价值 ($)",
        yaxis_type="log",
        template="plotly_dark",
        height=600,
        legend=dict(font=dict(size=10)),
        hovermode="x unified"
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def generate_bar_chart(results):
    """生成最终价值柱状图"""
    names = [f'{r["flag"]} {r["name"]}' for r in results]
    values = [r["final_value"] for r in results]
    colors = ['#00ff88' if v > 1000 else '#ff4444' for v in values]
    
    fig = go.Figure(go.Bar(
        x=values,
        y=names,
        orientation='h',
        marker_color=colors,
        text=[f'${v:,.0f}' for v in values],
        textposition='outside',
        hovertemplate='%{y}<br>最终价值: $%{x:,.0f}<extra></extra>'
    ))
    
    # 加一条竖线表示 $1000 本金
    fig.add_vline(x=1000, line_dash="dash", line_color="yellow",
                  annotation_text="$1,000 本金", annotation_position="top")
    
    fig.update_layout(
        title="💰 $1,000 投入 → 最终价值排行",
        xaxis_title="最终价值 ($)",
        template="plotly_dark",
        height=700,
        yaxis=dict(autorange="reversed"),
        margin=dict(l=200)
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

@app.route("/")
def index():
    results = run_backtest()
    portfolio_chart = generate_portfolio_chart(results)
    bar_chart = generate_bar_chart(results)
    
    total_invested = sum(r["initial"] for r in results)
    total_final = sum(r["final_value"] for r in results)
    total_return = (total_final - total_invested) / total_invested * 100
    
    best = results[0] if results else None
    worst = results[-1] if results else None
    
    return render_template("index.html",
                           results=results,
                           portfolio_chart=portfolio_chart,
                           bar_chart=bar_chart,
                           total_invested=total_invested,
                           total_final=total_final,
                           total_return=total_return,
                           best=best,
                           worst=worst,
                           stock_count=len(results))

@app.route("/api/backtest")
def api_backtest():
    investment = request.args.get("investment", 1000, type=float)
    results = run_backtest(investment)
    total_invested = sum(r["initial"] for r in results)
    total_final = sum(r["final_value"] for r in results)
    return jsonify({
        "results": results,
        "summary": {
            "total_invested": total_invested,
            "total_final": round(total_final, 2),
            "total_return_pct": round((total_final - total_invested) / total_invested * 100, 2),
            "stock_count": len(results)
        }
    })

@app.route("/api/stock/<ticker>")
def api_stock(ticker):
    df = load_stock_data(ticker)
    if df is None:
        return jsonify({"error": "Stock not found"}), 404
    
    close_col = "Close"
    if close_col not in df.columns:
        for col in df.columns:
            if "close" in col.lower():
                close_col = col
                break
    
    return jsonify({
        "ticker": ticker,
        "info": STOCKS.get(ticker, {}),
        "data_points": len(df),
        "date_range": [df.index[0].strftime("%Y-%m-%d"), df.index[-1].strftime("%Y-%m-%d")],
        "latest_close": round(float(df[close_col].iloc[-1]), 2)
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=False)
