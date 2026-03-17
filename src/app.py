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
    # --- 2025 Top 20 市值 ---
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
    # --- 2010 Top 20 市值（新增） ---
    "0857.HK": {"name": "PetroChina (中石油)", "flag": "🇨🇳"},
    "IBM": {"name": "IBM", "flag": "🇺🇸"},
    "GE": {"name": "General Electric", "flag": "🇺🇸"},
    "0941.HK": {"name": "China Mobile (中国移动)", "flag": "🇨🇳"},
    "SHEL": {"name": "Royal Dutch Shell", "flag": "🇳🇱"},
    "CVX": {"name": "Chevron", "flag": "🇺🇸"},
    "1398.HK": {"name": "ICBC (工商银行)", "flag": "🇨🇳"},
    "BHP": {"name": "BHP Billiton", "flag": "🇦🇺"},
    "T": {"name": "AT&T", "flag": "🇺🇸"},
    "PG": {"name": "Procter & Gamble", "flag": "🇺🇸"},
    "NESN.SW": {"name": "Nestlé", "flag": "🇨🇭"},
    "KO": {"name": "Coca-Cola", "flag": "🇺🇸"},
    "PFE": {"name": "Pfizer", "flag": "🇺🇸"},
    "VZ": {"name": "Verizon", "flag": "🇺🇸"},
    "WFC": {"name": "Wells Fargo (富国银行)", "flag": "🇺🇸"},
    "NVS": {"name": "Novartis (诺华)", "flag": "🇨🇭"},
}

# 2012-05-18 附近的市值排名（亿美元，来源：历史数据）
MARKET_CAP_2012 = {
    "AAPL": 1, "XOM": 2, "0857.HK": 3, "MSFT": 4,
    "1398.HK": 5, "IBM": 6, "WMT": 7, "SHEL": 8,
    "GE": 9, "0941.HK": 10, "CVX": 11, "GOOGL": 12,
    "BRK-B": 13, "T": 14, "JNJ": 15, "WFC": 16,
    "PG": 17, "NVS": 18, "PFE": 19, "BHP": 20,
    # 以下为 2012 时不在 Top 20 的
    "NVDA": None, "AMZN": None, "META": None, "TSM": None,
    "AVGO": None, "TSLA": None, "LLY": None, "005930.KS": None,
    "JPM": None, "0700.HK": None, "V": None, "ASML": None,
    "MU": None, "KO": None, "VZ": None, "NESN.SW": None,
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
    """加载分红数据，确保 index 是 timezone-naive DatetimeIndex"""
    safe_name = ticker.replace(".", "_")
    filepath = os.path.join(DATA_DIR, f"{safe_name}_dividends.csv")
    if not os.path.exists(filepath):
        return pd.Series(dtype=float)
    df = pd.read_csv(filepath, index_col=0, parse_dates=True)
    if isinstance(df, pd.DataFrame) and len(df.columns) > 0:
        s = df.iloc[:, 0]
    elif isinstance(df, pd.Series):
        s = df
    else:
        return pd.Series(dtype=float)
    # 确保 index 是 DatetimeIndex 且 timezone-naive
    if not isinstance(s.index, pd.DatetimeIndex):
        s.index = pd.to_datetime(s.index, utc=True)
    if s.index.tz is not None:
        s.index = s.index.tz_localize(None)
    return s

def run_backtest(initial_investment=1000):
    """
    回测：每只股票从 2010-01-05 起投入资金，持有到最后一天
    包含分红再投资 (DRIP)
    若股票在该日期前未上市，则用最早可用日期
    """
    # 统一起点：META 上市日 2012-05-18
    TARGET_START = pd.Timestamp("2012-05-18")
    
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
        
        # 统一起点：2012-05-18 或之后最近的交易日
        valid = prices[prices.index >= TARGET_START]
        if len(valid) < 2:
            continue
        
        start_price = valid.iloc[0]
        end_price = valid.iloc[-1]
        start_date = valid.index[0]
        end_date = valid.index[-1]
        prices = valid
        
        # --- 不含分红的简单回报 ---
        shares_no_drip = initial_investment / start_price
        final_no_drip = shares_no_drip * end_price
        
        # --- 含分红再投资 (DRIP) ---
        dividends = load_dividends(ticker)
        shares = initial_investment / start_price
        total_dividends_received = 0.0
        
        if len(dividends) > 0:
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
        
        rank_2012 = MARKET_CAP_2012.get(ticker)
        
        results.append({
            "ticker": ticker,
            "name": info["name"],
            "flag": info["flag"],
            "rank_2012": rank_2012,
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
    TARGET_START = pd.Timestamp("2012-05-18")
    fig = go.Figure()
    all_values = []
    
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
        # 统一起点
        valid = prices[prices.index >= TARGET_START]
        if len(valid) >= 2:
            prices = valid
        
        dividends = load_dividends(r["ticker"])
        
        # 模拟 DRIP 逐日持仓价值
        start_price = prices.iloc[0]
        shares = 10000.0 / start_price
        
        # load_dividends 已确保 timezone-naive
        
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
        all_values.extend(portfolio_values)
    
    # 计算固定 Y 轴范围（log scale）
    import math
    if all_values:
        y_min = max(min(all_values), 1)
        y_max = max(all_values)
        log_min = math.floor(math.log10(y_min)) - 0.1
        log_max = math.ceil(math.log10(y_max)) + 0.1
    else:
        log_min, log_max = 3, 7
    
    fig.update_layout(
        title="📈 各 $10,000 投资增长曲线 · 含分红再投资 (2012-2025)",
        xaxis_title="日期",
        yaxis_title="投资价值 ($)",
        yaxis_type="log",
        yaxis_range=[log_min, log_max],  # 固定 Y 轴范围
        yaxis_autorange=False,
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
