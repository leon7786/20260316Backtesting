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
    "NVDA": {"name": "NVIDIA", "name_cn": "英伟达", "flag": "🇺🇸"},
    "AAPL": {"name": "Apple", "name_cn": "苹果", "flag": "🇺🇸"},
    "GOOGL": {"name": "Alphabet", "name_cn": "谷歌", "flag": "🇺🇸"},
    "MSFT": {"name": "Microsoft", "name_cn": "微软", "flag": "🇺🇸"},
    "AMZN": {"name": "Amazon", "name_cn": "亚马逊", "flag": "🇺🇸"},
    "META": {"name": "Meta Platforms", "name_cn": "Meta", "flag": "🇺🇸"},
    "TSM": {"name": "TSMC", "name_cn": "台积电", "flag": "🇹🇼"},
    "AVGO": {"name": "Broadcom", "name_cn": "博通", "flag": "🇺🇸"},
    "TSLA": {"name": "Tesla", "name_cn": "特斯拉", "flag": "🇺🇸"},
    "BRK-B": {"name": "Berkshire Hathaway", "name_cn": "伯克希尔", "flag": "🇺🇸"},
    "WMT": {"name": "Walmart", "name_cn": "沃尔玛", "flag": "🇺🇸"},
    "LLY": {"name": "Eli Lilly", "name_cn": "礼来", "flag": "🇺🇸"},
    "005930.KS": {"name": "Samsung", "name_cn": "三星电子", "flag": "🇰🇷"},
    "JPM": {"name": "JPMorgan Chase", "name_cn": "摩根大通", "flag": "🇺🇸"},
    "0700.HK": {"name": "Tencent", "name_cn": "腾讯", "flag": "🇨🇳"},
    "XOM": {"name": "Exxon Mobil", "name_cn": "埃克森美孚", "flag": "🇺🇸"},
    "V": {"name": "Visa", "name_cn": "维萨", "flag": "🇺🇸"},
    "JNJ": {"name": "Johnson & Johnson", "name_cn": "强生", "flag": "🇺🇸"},
    "ASML": {"name": "ASML Holding", "name_cn": "阿斯麦", "flag": "🇳🇱"},
    "MU": {"name": "Micron Technology", "name_cn": "美光", "flag": "🇺🇸"},
    # --- 2010 Top 20 市值（新增） ---
    "0857.HK": {"name": "PetroChina", "name_cn": "中国石油", "flag": "🇨🇳"},
    "IBM": {"name": "IBM", "name_cn": "IBM", "flag": "🇺🇸"},
    "GE": {"name": "General Electric", "name_cn": "通用电气", "flag": "🇺🇸"},
    "0941.HK": {"name": "China Mobile", "name_cn": "中国移动", "flag": "🇨🇳"},
    "SHEL": {"name": "Royal Dutch Shell", "name_cn": "壳牌", "flag": "🇳🇱"},
    "CVX": {"name": "Chevron", "name_cn": "雪佛龙", "flag": "🇺🇸"},
    "1398.HK": {"name": "ICBC", "name_cn": "工商银行", "flag": "🇨🇳"},
    "BHP": {"name": "BHP Billiton", "name_cn": "必和必拓", "flag": "🇦🇺"},
    "T": {"name": "AT&T", "name_cn": "AT&T", "flag": "🇺🇸"},
    "PG": {"name": "Procter & Gamble", "name_cn": "宝洁", "flag": "🇺🇸"},
    "NESN.SW": {"name": "Nestlé", "name_cn": "雀巢", "flag": "🇨🇭"},
    "KO": {"name": "Coca-Cola", "name_cn": "可口可乐", "flag": "🇺🇸"},
    "PFE": {"name": "Pfizer", "name_cn": "辉瑞", "flag": "🇺🇸"},
    "VZ": {"name": "Verizon", "name_cn": "威瑞森", "flag": "🇺🇸"},
    "WFC": {"name": "Wells Fargo", "name_cn": "富国银行", "flag": "🇺🇸"},
    "NVS": {"name": "Novartis", "name_cn": "诺华", "flag": "🇨🇭"},
}

# 各年份全球市值排名（基于当年年初数据，仅覆盖本列表中的股票）
MARKET_CAP_RANKS = {
    # 2010 年初 Top 20 全球市值
    2010: {
        "XOM": 1, "0857.HK": 2, "MSFT": 3, "1398.HK": 4, "AAPL": 5,
        "WMT": 6, "BRK-B": 7, "0941.HK": 8, "SHEL": 9, "CVX": 10,
        "IBM": 11, "GE": 12, "PG": 13, "JNJ": 14, "JPM": 15,
        "T": 16, "GOOGL": 17, "PFE": 18, "KO": 19, "NVS": 20,
    },
    # 2012 年中（META 上市日附近）
    2012: {
        "AAPL": 1, "XOM": 2, "0857.HK": 3, "MSFT": 4, "1398.HK": 5,
        "IBM": 6, "WMT": 7, "SHEL": 8, "GE": 9, "0941.HK": 10,
        "CVX": 11, "GOOGL": 12, "BRK-B": 13, "T": 14, "JNJ": 15,
        "WFC": 16, "PG": 17, "NVS": 18, "PFE": 19, "BHP": 20,
    },
    # 2015 年初
    2015: {
        "AAPL": 1, "XOM": 2, "MSFT": 3, "GOOGL": 4, "BRK-B": 5,
        "WFC": 6, "JNJ": 7, "WMT": 8, "GE": 9, "NVS": 10,
        "PG": 11, "JPM": 12, "0941.HK": 13, "SHEL": 14, "CVX": 15,
        "PFE": 16, "KO": 17, "VZ": 18, "IBM": 19, "V": 20,
    },
    # 2020 年初
    2020: {
        "AAPL": 1, "MSFT": 2, "GOOGL": 3, "AMZN": 4, "META": 5,
        "BRK-B": 6, "V": 7, "JPM": 8, "JNJ": 9, "WMT": 10,
        "0700.HK": 11, "005930.KS": 12, "PG": 13, "TSM": 14, "XOM": 15,
        "NESN.SW": 16, "NVS": 17, "T": 18, "KO": 19, "VZ": 20,
    },
    # 2025 年初
    2025: {
        "AAPL": 1, "NVDA": 2, "MSFT": 3, "GOOGL": 4, "AMZN": 5,
        "META": 6, "TSM": 7, "AVGO": 8, "TSLA": 9, "BRK-B": 10,
        "WMT": 11, "LLY": 12, "005930.KS": 13, "JPM": 14, "0700.HK": 15,
        "XOM": 16, "V": 17, "JNJ": 18, "ASML": 19, "MU": 20,
    },
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
    # 统一起点/终点
    TARGET_START = pd.Timestamp("2012-05-18")
    TARGET_END = pd.Timestamp("2025-12-01")
    
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
        
        # 统一起点 2012-05-18，终点 2025-12-01
        valid = prices[(prices.index >= TARGET_START) & (prices.index <= TARGET_END)]
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
        
        ranks = {}
        for year in [2010, 2012, 2015, 2020, 2025]:
            ranks[year] = MARKET_CAP_RANKS.get(year, {}).get(ticker)
        
        results.append({
            "ticker": ticker,
            "name": info["name"],
            "name_cn": info.get("name_cn", ""),
            "flag": info["flag"],
            "rank_2010": ranks[2010],
            "rank_2012": ranks[2012],
            "rank_2015": ranks[2015],
            "rank_2020": ranks[2020],
            "rank_2025": ranks[2025],
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
    TARGET_END = pd.Timestamp("2025-12-01")
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
        # 统一起止点
        valid = prices[(prices.index >= TARGET_START) & (prices.index <= TARGET_END)]
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
            line=dict(width=1.2),
            opacity=0.7,
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
        title="📈 各 $10,000 投资增长曲线 · 含分红再投资 (2012.05 - 2025.12)",
        xaxis_title="日期",
        yaxis_title="投资价值 ($)",
        yaxis_type="log",
        yaxis_range=[log_min, log_max],
        yaxis_autorange=False,
        template="plotly_dark",
        height=700,
        legend=dict(
            font=dict(size=9),
            bgcolor="rgba(0,0,0,0.5)",
            bordercolor="rgba(255,255,255,0.1)",
            borderwidth=1,
            itemclick="toggle",
            itemdoubleclick=False,
        ),
        hovermode="closest",
        hoverlabel=dict(font_size=12),
    )
    
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def generate_bar_chart(results):
    """生成最终价值柱状图（对数 X 轴，含 DRIP vs 不含）"""
    # Y 轴标签：国旗 + 英文名 + 中文名 + CAGR
    names = []
    for r in results:
        cn = r.get("name_cn", "")
        label = f'{r["flag"]} {r["name"]}'
        if cn and cn != r["name"]:
            label += f' ({cn})'
        label += f'  CAGR {r["cagr_pct"]:+.1f}%'
        names.append(label)
    
    values = [r["final_value"] for r in results]
    values_no_drip = [r["final_no_drip"] for r in results]
    returns = [r["total_return_pct"] for r in results]
    
    # 计算柱状图高度
    bar_height = max(850, len(results) * 32)
    
    fig = go.Figure()
    
    # DRIP 柱
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
        textposition='none',
        hovertemplate='%{y}<br>不含分红: $%{x:,.0f}<extra></extra>'
    ))
    
    # 本金线
    fig.add_vline(x=10000, line_dash="dash", line_color="yellow",
                  annotation_text="$10,000 本金", annotation_position="top")
    
    fig.update_layout(
        title="💰 $10,000 投入 → 最终价值排行（对数坐标，含 DRIP vs 不含）",
        xaxis_title="最终价值 ($)",
        xaxis_type="log",
        template="plotly_dark",
        height=bar_height,
        barmode='overlay',
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(size=10),
        ),
        margin=dict(l=320, r=140),
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
