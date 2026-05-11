# python3 -m streamlit run script.py

import plotly.express as px
import streamlit as st
import yfinance as yf
from streamlit_autorefresh import st_autorefresh

st.set_page_config(layout="wide", page_title="Stock Simulator")

if "cash" not in st.session_state:
    st.session_state.cash = 100000.0
if "portfolio" not in st.session_state:
    st.session_state.portfolio = {}
if "short_positions" not in st.session_state:
    st.session_state.short_positions = {}
if "history" not in st.session_state:
    st.session_state.history = []

st_autorefresh(interval=1000, key="auto_refresh")

st.markdown("""
<style>
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
[data-testid="stVerticalBlock"] {
    background-color: #0a0c10;
}
[data-testid="stSidebar"],
[data-testid="stSidebarContent"] {
    background-color: #0a0c10;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] a {
    color: #ffffff !important;
}
[data-testid="stMarkdownContainer"],
[data-testid="stText"],
[data-testid="stCaptionContainer"],
p, label {
    color: #e2e8f0 !important;
    font-family: 'Inter', -apple-system, sans-serif;
}
h1, h2, h3 {
    color: #f8fafc !important;
}
[data-testid="metric-container"] {
    background-color: #111318;
    border: 1px solid #1e2330;
    padding: 16px;
    border-radius: 10px;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #f8fafc !important;
    font-size: 22px !important;
}
[data-testid="metric-container"] [data-testid="stMetricLabel"] {
    color: #94a3b8 !important;
}
button[data-baseweb="tab"] {
    background-color: transparent;
    color: #94a3b8;
    font-weight: 500;
    font-size: 14px;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #f8fafc;
    border-bottom: 2px solid #3b82f6;
}
input, textarea, select {
    background-color: #111318 !important;
    color: #f8fafc !important;
    border-radius: 8px !important;
    border: 1px solid #1e2330 !important;
}
div.stButton button {
    background-color: #111318;
    color: #e2e8f0;
    border: 1px solid #1e2330;
    border-radius: 8px;
    height: 40px;
    font-size: 13px;
}
div.stButton button:hover {
    background-color: #1e2330;
}
div[data-baseweb="select"] > div {
    background-color: #111318 !important;
    border: 1px solid #1e2330 !important;
    border-radius: 8px !important;
}
div[data-baseweb="select"] span {
    color: #f8fafc !important;
}
ul[role="listbox"] {
    background-color: #111318 !important;
    border: 1px solid #1e2330 !important;
}
li[role="option"] {
    background-color: #111318 !important;
    color: #f8fafc !important;
}
li[role="option"]:hover {
    background-color: #1e2330 !important;
}
hr {
    border-color: #1e2330 !important;
}
[data-testid="stSidebarCollapsedControl"] span,
[data-testid="collapsedControl"] span {
    font-size: 0 !important;
}
</style>
""", unsafe_allow_html=True)


def get_price(symbol):
    stock = yf.Ticker(symbol)
    data = stock.history(period="1d")
    if data.empty:
        return None
    return data["Close"].iloc[-1]


def buy_stock(symbol, shares):
    price = get_price(symbol)
    if price is None:
        st.error("Invalid ticker symbol.")
        return
    cost = price * shares
    if st.session_state.cash >= cost:
        st.session_state.cash -= cost
        st.session_state.portfolio[symbol] = st.session_state.portfolio.get(symbol, 0) + shares
        st.session_state.history.insert(0, f"Buy {shares} {symbol} @ ${price:.2f}")
    else:
        st.error("Not enough cash.")


def sell_stock(symbol, shares):
    if st.session_state.portfolio.get(symbol, 0) < shares:
        st.error("Not enough shares.")
        return
    price = get_price(symbol)
    if price is None:
        st.error("Invalid ticker symbol.")
        return
    st.session_state.cash += price * shares
    st.session_state.portfolio[symbol] -= shares
    if st.session_state.portfolio[symbol] == 0:
        del st.session_state.portfolio[symbol]
    st.session_state.history.insert(0, f"Sell {shares} {symbol} @ ${price:.2f}")


def short_stock(symbol, shares):
    price = get_price(symbol)
    if price is None:
        st.error("Invalid ticker symbol.")
        return
    st.session_state.cash += price * shares
    st.session_state.short_positions[symbol] = st.session_state.short_positions.get(symbol, 0) + shares
    st.session_state.history.insert(0, f"Short {shares} {symbol} @ ${price:.2f}")


def cover_short(symbol, shares):
    owed = st.session_state.short_positions.get(symbol, 0)
    if owed < shares:
        st.error(f"Only short {owed} shares of {symbol}.")
        return
    price = get_price(symbol)
    if price is None:
        st.error("Invalid ticker symbol.")
        return
    cost = price * shares
    if st.session_state.cash < cost:
        st.error("Not enough cash to cover.")
        return
    st.session_state.cash -= cost
    st.session_state.short_positions[symbol] -= shares
    if st.session_state.short_positions[symbol] == 0:
        del st.session_state.short_positions[symbol]
    st.session_state.history.insert(0, f"Cover {shares} {symbol} @ ${price:.2f}")


def portfolio_value():
    total = st.session_state.cash
    for sym, sh in st.session_state.portfolio.items():
        price = get_price(sym)
        if price:
            total += price * sh
    for sym, sh in st.session_state.short_positions.items():
        price = get_price(sym)
        if price:
            total -= price * sh
    return total


pv  = portfolio_value()
pnl = pv - 100000
col = "#22c55e" if pnl >= 0 else "#ef4444"

st.markdown(f"""
<div>
    <span style='font-size:22px;font-weight:600;'>Stock Simulator</span>
    <span style='margin-left:10px;'>${pv:,.0f}</span>
    <span style='color:{col};margin-left:6px;'>{pnl:+,.0f}</span>
</div>
""", unsafe_allow_html=True)

st.divider()

tabs = st.tabs(["Portfolio", "Trade", "History", "Search"])

with tabs[0]:
    pv2  = portfolio_value()
    pnl2 = pv2 - 100000
    long_val   = sum((get_price(s) or 0) * q for s, q in st.session_state.portfolio.items())
    short_liab = sum((get_price(s) or 0) * q for s, q in st.session_state.short_positions.items())

    m1, m2, m3 = st.columns(3)
    m1.metric("Cash",        f"${st.session_state.cash:,.2f}")
    m2.metric("Long Value",  f"${long_val:,.2f}")
    m3.metric("Total P&L",   f"${pnl2:+,.2f}")

    st.markdown("<br>", unsafe_allow_html=True)

    if st.session_state.portfolio:
        st.markdown("<div style='font-size:11px;color:#475569;letter-spacing:1px;text-transform:uppercase;margin-bottom:12px;'>Long Holdings</div>", unsafe_allow_html=True)
        grid = st.columns(3)
        for i, (sym, sh) in enumerate(st.session_state.portfolio.items()):
            price = get_price(sym)
            val   = (price or 0) * sh
            grid[i % 3].markdown(f"""
            <div style='background:#111318;padding:16px;border-radius:12px;margin-bottom:12px;border:1px solid #1e2330;'>
                <div style='display:flex;justify-content:space-between;align-items:center;'>
                    <span style='color:#f1f5f9;font-size:16px;font-weight:600;'>{sym}</span>
                    <span style='color:#475569;font-size:12px;'>{sh} shares</span>
                </div>
                <div style='color:#3b82f6;font-size:20px;font-weight:700;margin-top:8px;'>${val:,.2f}</div>
                <div style='color:#475569;font-size:12px;margin-top:4px;'>@ ${f"{price:.2f}" if price else "N/A"}</div>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown("<div style='color:#334155;padding:20px 0;'>No long positions.</div>", unsafe_allow_html=True)

    if st.session_state.short_positions:
        st.markdown("<div style='font-size:11px;color:#475569;letter-spacing:1px;text-transform:uppercase;margin:20px 0 12px 0;'>Short Positions</div>", unsafe_allow_html=True)
        grid2 = st.columns(3)
        for i, (sym, sh) in enumerate(st.session_state.short_positions.items()):
            price = get_price(sym)
            liab  = (price or 0) * sh
            grid2[i % 3].markdown(f"""
            <div style='background:#111318;padding:16px;border-radius:12px;margin-bottom:12px;border:1px solid #2d1f1f;'>
                <div style='display:flex;justify-content:space-between;align-items:center;'>
                    <span style='color:#f1f5f9;font-size:16px;font-weight:600;'>{sym}</span>
                    <span style='color:#f97316;font-size:12px;'>SHORT {sh} shares</span>
                </div>
                <div style='color:#f97316;font-size:20px;font-weight:700;margin-top:8px;'>-${liab:,.2f}</div>
                <div style='color:#475569;font-size:12px;margin-top:4px;'>@ ${f"{price:.2f}" if price else "N/A"}</div>
            </div>""", unsafe_allow_html=True)

with tabs[1]:
    left, right = st.columns([2, 1])

    with left:
        symbol = st.text_input("Stock Symbol").upper()
        shares = st.number_input("Number of Shares", min_value=1, value=1)

        if symbol:
            price = get_price(symbol)
            if price:
                m1, m2 = st.columns(2)
                m1.metric("Current Price", f"${price:.2f}")
                m2.metric("Order Total",   f"${price * shares:,.2f}")
            else:
                st.markdown("<div style='color:#ef4444;font-size:13px;'>Invalid symbol or no data.</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div style='font-size:11px;color:#475569;letter-spacing:1px;text-transform:uppercase;margin-bottom:12px;'>Place Order</div>", unsafe_allow_html=True)

        if symbol:
            price       = get_price(symbol)
            owned_long  = st.session_state.portfolio.get(symbol, 0)
            owned_short = st.session_state.short_positions.get(symbol, 0)
            st.markdown(f"""
            <div style='background:#111318;border:1px solid #1e2330;border-radius:8px;padding:12px;margin-bottom:12px;'>
                <div style='display:flex;justify-content:space-between;margin-bottom:6px;'>
                    <span style='color:#475569;font-size:12px;'>Cash available</span>
                    <span style='color:#f1f5f9;font-size:13px;font-weight:500;'>${st.session_state.cash:,.2f}</span>
                </div>
                <div style='display:flex;justify-content:space-between;margin-bottom:6px;'>
                    <span style='color:#475569;font-size:12px;'>Long position</span>
                    <span style='color:#f1f5f9;font-size:13px;'>{owned_long} shares</span>
                </div>
                <div style='display:flex;justify-content:space-between;'>
                    <span style='color:#475569;font-size:12px;'>Short position</span>
                    <span style='color:#ef4444;font-size:13px;'>{owned_short} shares</span>
                </div>
            </div>""", unsafe_allow_html=True)

        b1, b2 = st.columns(2)
        b3, b4 = st.columns(2)

        if b1.button("Buy",   use_container_width=True, type="primary"):
            if symbol: buy_stock(symbol, shares)
        if b2.button("Sell",  use_container_width=True):
            if symbol: sell_stock(symbol, shares)
        if b3.button("Short", use_container_width=True):
            if symbol: short_stock(symbol, shares)
        if b4.button("Cover", use_container_width=True):
            if symbol: cover_short(symbol, shares)
with tabs[2]:
    if not st.session_state.history:
        st.markdown("<div style='color:#334155;text-align:center;padding:40px 0;'>No trades yet.</div>", unsafe_allow_html=True)
    else:
        for t in st.session_state.history[:30]:
            action = t.split()[0]
            color  = {"Buy":"#22c55e","Sell":"#ef4444","Short":"#f97316","Cover":"#3b82f6"}.get(action, "#94a3b8")
            st.markdown(f"""
            <div style='background:#111318;border:1px solid #1e2330;border-radius:8px;
                        padding:10px 14px;margin-bottom:6px;display:flex;align-items:center;gap:10px;'>
                <span style='color:{color};font-size:12px;font-weight:600;min-width:44px;'>{action}</span>
                <span style='color:#e2e8f0;font-size:13px;'>{' '.join(t.split()[1:])}</span>
            </div>""", unsafe_allow_html=True)

with tabs[3]:
    r1, r2 = st.columns([3, 1])
    research_symbol = r1.text_input("Symbol", value="AAPL").upper()
    timeframe = r2.selectbox("Range", ["1d","5d","1mo","3mo","6mo","1y","2y","5y","max"])

    if research_symbol:
        ticker = yf.Ticker(research_symbol)

        interval_map = {
            "1d":  ("1d",  "1m"),
            "5d":  ("5d",  "1m"),
            "1mo": ("1mo", "4h"),
            "3mo": ("3mo", "4h"),
            "6mo": ("6mo", "4h"),
            "1y":  ("1y",  "4h"),
            "2y":  ("2y",  "4h"),
        }
        if timeframe in interval_map:
            period, interval = interval_map[timeframe]
            hist = ticker.history(period=period, interval=interval)
        else:
            hist = ticker.history(period=timeframe)

        if not hist.empty:
            fig = px.line(hist, x=hist.index, y="Close")
            fig.update_layout(
                template=None,
                plot_bgcolor="#0a0c10",
                paper_bgcolor="#0a0c10",
                font=dict(color="#64748b"),
                margin=dict(l=50, r=20, t=40, b=40),
                title=dict(text=research_symbol, x=0.02, xanchor="left",
                           font=dict(color="#f8fafc", size=16)),
                xaxis=dict(showgrid=False, tickfont=dict(color="#334155")),
                yaxis=dict(gridcolor="#111318", zeroline=False,
                           tickfont=dict(color="#334155")),
            )
            fig.update_traces(line=dict(color="#3b82f6", width=2),
                              hovertemplate="$%{y:.2f}<extra></extra>")
            r1.plotly_chart(fig, use_container_width=True)
        else:
            r1.markdown("<div style='color:#ef4444;font-size:13px;'>No data available.</div>",
                        unsafe_allow_html=True)

        info = ticker.info
        if info:
            st.divider()
            st.markdown("<div style='font-size:11px;color:#475569;letter-spacing:1px;text-transform:uppercase;margin-bottom:12px;'>Fundamentals</div>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            mc  = info.get("marketCap")
            avg = info.get("averageVolume")
            c1.metric("Market Cap",  f"${mc:,}"  if isinstance(mc,  int) else "N/A")
            c1.metric("P/E",         str(info.get("trailingPE",  "N/A")))
            c1.metric("Forward P/E", str(info.get("forwardPE",   "N/A")))
            c2.metric("EPS",         str(info.get("trailingEps", "N/A")))
            c2.metric("Forward EPS", str(info.get("forwardEps",  "N/A")))
            c2.metric("Avg Volume",  f"{avg:,}"  if isinstance(avg, int) else "N/A")
            c3.metric("Div. Yield",  str(info.get("dividendYield", "N/A")))
            c3.markdown(f"<div style='font-size:13px;color:#94a3b8;margin-top:8px;'>Sector: <span style='color:#f1f5f9;'>{info.get('sector','N/A')}</span></div>", unsafe_allow_html=True)
            c3.markdown(f"<div style='font-size:13px;color:#94a3b8;margin-top:4px;'>Industry: <span style='color:#f1f5f9;'>{info.get('industry','N/A')}</span></div>", unsafe_allow_html=True)