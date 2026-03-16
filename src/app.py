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

def load_dividends(ticker):
    """加载分红数据"""
    safe_name = ticker.replace(".", "_")
    filepath = os.path.join(DATA_DIR, f"{safe_name}_dividends.csv")
    if not os.path.exists(filepath):
        return pd.Series(dtype=float)
    df = pd.read_csv(filepath, index_col=0, parse_dates=True)
    if isinstance(df, pd.DataFrame) and len(df.columns) > 0:
        return df.iloc[:, 0]
    return pd.Series(dtype=float)

def run_backtest(initial_investment=1000):
    """
    回测：每只股票在数据起始日投入资金，持有到最后一天
    包含分红再投资 (DRIP)
    """
    results = []
    for ticker, info in STOCKS.items():
        df = load_stock_data(ticker)
        if df is None or df.empty:
            continue
        
        close_col = "Close"
        if close_col not in df.columns:
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
        
        # --- 不含分红的简单回报 ---
        shares_no_drip = initial_investment / start_price
        final_no_drip = shares_no_drip * end_price
        
        # --- 含分红再投资 (DRIP) ---
        dividends = load_dividends(ticker)
        shares = initial_investment / start_price
        total_dividends_received = 0.0
        
        if len(dividends) > 0:
            # 确保 timezone-naive
            if dividends.index.tz is not None:
                dividends.index = dividends.index.tz_localize(None)
            
            for div_date, div_amount in dividends.items():
                if div_date < start_date or div_date > end_date:
                    continue
                # 分红收入
                div_income = shares * div_amount
                total_dividends_received += div_income
                # 找到分红日或之后最近的交易日价格
                valid_prices = prices[prices.index >= div_date]
                if len(valid_prices) > 0:
                    reinvest_price = valid_prices.iloc[0]
                    new_shares = div_income / reinvest_price
                    shares += new_shares
        
        final_value = shares * end_price
        total_return = (final_value - initial_investment) / initial_investment * 100
        
        # 年化收益率
        years = (end_date - start_date).days / 365.25
        if years > 0:
            cagr = ((final_value / initial_investment) ** (1 / years) - 1) * 100
            cagr_no_drip = ((final_no_drip / initial_investment) ** (1 / years) - 1) * 100
        else:
            cagr = 0
            cagr_no_drip = 0
        
        # 最大回撤（基于价格）
        cummax = prices.cummax()
        drawdown = (prices - cummax) / cummax
        max_drawdown = drawdown.min() * 100
        
        # 分红增益
        drip_bonus = final_value - final_no_drip
        drip_bonus_pct = (drip_bonus / final_no_drip * 100) if final_no_drip > 0 else 0
        
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
            "final_no_drip": round(float(final_no_drip), 2),
            "total_return_pct": round(float(total_return), 2),
            "cagr_pct": round(float(cagr), 2),
            "cagr_no_drip_pct": round(float(cagr_no_drip), 2),
            "max_drawdown_pct": round(float(max_drawdown), 2),
            "years": round(float(years), 1),
            "total_dividends": round(float(total_dividends_received), 2),
            "drip_bonus": round(float(drip_bonus), 2),
            "drip_bonus_pct": round(float(drip_bonus_pct), 2),
        })
    
    # 按最终价值排序
    results.sort(key=lambda x: x["final_value"], reverse=True)
    return results

def generate_portfolio_chart(results):
    """生成组合总览图（含 DRIP）"""
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
        dividends = load_dividends(r["ticker"])
        
        # 模拟 DRIP 逐日持仓价值
        start_price = prices.iloc[0]
        shares = 10000.0 / start_price
        
        # 确保 timezone-naive
        if len(dividends) > 0 and dividends.index.tz is not None:
            dividends.index = dividends.index.tz_localize(None)
        
        div_dict = {}
        if len(dividends) > 0:
            for d, amt in dividends.items():
                div_dict[d] = amt
        
        portfolio_values = []
        for date, price in prices.items():
            if date in div_dict:
                div_income = shares * div_dict[date]
                shares += div_income / price
            portfolio_values.append(shares * price)
        
        fig.add_trace(go.Scatter(
            x=prices.index,
            y=portfolio_values,
            mode='lines',
            name=f'{r["flag"]} {r["name"]}',
            hovertemplate=f'{r["name"]}<br>日期: %{{x}}<br>价值: $%{{y:,.0f}}<extra></extra>'
        ))
    
    fig.update_layout(
        title="📈 各 $10,000 投资增长曲线 · 含分红再投资 (2010-2025)",
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
    """生成最终价值柱状图（含 DRIP vs 不含）"""
    names = [f'{r["flag"]} {r["name"]}' for r in results]
    values = [r["final_value"] for r in results]
    values_no_drip = [r["final_no_drip"] for r in results]
    returns = [r["total_return_pct"] for r in results]
    
    # DRIP 柱
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=values,
        y=names,
        orientation='h',
        marker_color='#00ff88',
        name='含分红再投资 (DRIP)',
        text=[f'${v:,.0f} ({ret:+,.1f}%)' for v, ret in zip(values, returns)],
        textposition='outside',
        hovertemplate='%{y}<br>DRIP 最终价值: $%{x:,.0f}<extra></extra>'
    ))
    
    # 不含 DRIP 柱
    fig.add_trace(go.Bar(
        x=values_no_drip,
        y=names,
        orientation='h',
        marker_color='#4a4a8a',
        name='不含分红',
        text=[f'${v:,.0f}' for v in values_no_drip],
        textposition='inside',
        hovertemplate='%{y}<br>不含分红: $%{x:,.0f}<extra></extra>'
    ))
    
    # 本金线
    fig.add_vline(x=10000, line_dash="dash", line_color="yellow",
                  annotation_text="$10,000 本金", annotation_position="top")
    
    fig.update_layout(
        title="💰 $10,000 投入 → 最终价值排行（含分红再投资 vs 不含）",
        xaxis_title="最终价值 ($)",
        template="plotly_dark",
        height=750,
        barmode='overlay',
        yaxis=dict(autorange="reversed"),
        margin=dict(l=200),
        legend=dict(x=0.7, y=0.05)
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

@app.route("/")
def index():
    results = run_backtest(initial_investment=10000)
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
