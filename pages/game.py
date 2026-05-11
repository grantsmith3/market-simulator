import plotly.express as px
import streamlit as st
import numpy as np
import random
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from streamlit.components.v1 import html

st.set_page_config(layout="wide", page_title="Market Simulator")
html("""
<script>
const doc = window.parent.document;

// ── Spacebar play/pause ────────────────────────────────────────────────────
doc.addEventListener('keydown', function(e) {
    if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
        e.preventDefault();
        const buttons = Array.from(doc.querySelectorAll('button'));
        const pauseBtn = buttons.find(el => el.innerText === '▶' || el.innerText === '⏸');
        if (pauseBtn) pauseBtn.click();
    }
});

// ── Tab persistence ────────────────────────────────────────────────────────
// Remember which tab was last clicked and re-click it after Streamlit rerenders.
let activeTabIdx = 0;

function getTabs() {
    return Array.from(doc.querySelectorAll('button[data-baseweb="tab"]'));
}

function restoreTab() {
    const tabs = getTabs();
    if (tabs.length > activeTabIdx) {
        // Only re-click if it's not already selected (avoid infinite loop)
        if (tabs[activeTabIdx].getAttribute('aria-selected') !== 'true') {
            tabs[activeTabIdx].click();
        }
    }
}

// Track user tab clicks
doc.addEventListener('click', function(e) {
    const tab = e.target.closest('button[data-baseweb="tab"]');
    if (tab) {
        const tabs = getTabs();
        const idx = tabs.indexOf(tab);
        if (idx !== -1) activeTabIdx = idx;
    }
});

// After each Streamlit rerender, restore the active tab.
// Streamlit signals rerenders by updating the DOM — watch for it.
const observer = new MutationObserver(function() {
    restoreTab();
});
observer.observe(doc.body, { childList: true, subtree: true });
</script>
""", height=0)
st.markdown("""
<style>

/* ===== Sidebar ===== */
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

/* ===== Base App Background ===== */
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
[data-testid="stVerticalBlock"] {
    background-color: #0a0c10;
}

/* ===== Text (TARGETED — no wildcard) ===== */
[data-testid="stMarkdownContainer"],
[data-testid="stText"],
[data-testid="stCaptionContainer"],
label, p, span {
    color: #e2e8f0 !important;
    font-family: 'Inter', -apple-system, sans-serif;
}

/* Headings */
h1, h2, h3 {
    color: #f8fafc !important;
}

/* ===== Metric Cards ===== */
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

/* ===== Tabs ===== */
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

/* ===== Inputs ===== */
input, textarea, select {
    background-color: #111318 !important;
    color: #f8fafc !important;
    border-radius: 8px !important;
    border: 1px solid #1e2330 !important;
}

/* ===== Buttons ===== */
div.stButton button {
    background-color: #111318;
    color: #e2e8f0;
    border: 1px solid #1e2330;
    border-radius: 8px;
    height: 40px;
    font-size: 13px;
}

/* ===== Divider ===== */
hr {
    border-color: #1e2330 !important;
}

/* ===== Sidebar Arrow Fix ===== */
button[kind="header"] {
    display: flex !important;
    align-items: center;
    justify-content: center;
}

/* Force icon visible */
button[kind="header"] svg {
    display: block !important;
    visibility: visible !important;
}

/* Hide fallback text ONLY inside toggle */
button[kind="header"] span {
    display: none !important;
}

</style>
""", unsafe_allow_html=True)

SECTORS = {
    "Tech": ["AAPL", "MSFT", "GOOG", "NVDA", "AMD", "ORCL", "META", "INTC", "TSLA", "ADBE"],
    "Energy": ["XOM", "CVX", "BP", "COP", "SLB", "HAL", "MRO", "PSX", "VLO", "OXY"],
    "Finance": ["JPM", "BAC", "GS", "MS", "C", "WFC", "BLK", "AXP", "SCHW", "USB"],
}


def load_game():
    st.session_state.stocks = {}
    for sec, tickers in SECTORS.items():
        for t in tickers:
            st.session_state.stocks[t] = {
                'sector': sec,
                'prices': [round(random.uniform(50, 400), 2)],
                'vol': random.uniform(0.001, 0.003),
                'event_smooth': 0.0,
            }
    st.session_state.sector_history = {s: [] for s in SECTORS}


ALL_SYMS = [s for t in SECTORS.values() for s in t]

MARKET_OPEN = 9 * 60 + 30
MARKET_CLOSE = 16 * 60

SPEEDS = {
    "1x":  0.4,   # 1 tick/sec  → 0.4 ticks per 400ms frame
    "2x":  0.8,
    "5x":  2.0,
    "10x": 4.0,
    "20x": 8.0,
    "60x": 24.0,
}

FILLER_NEWS = [
    "Equities drift lower as investors await Fed minutes.",
    "Options activity elevated ahead of quarterly expiration.",
    "Volatility index ticks up amid macro uncertainty.",
    "Institutional flows favour defensive names today.",
    "Rotation out of growth into value continues intraday.",
    "Bond yields edge higher; equities trade mixed.",
    "Low-volume session as European markets head to close.",
    "Risk appetite muted following overnight Asia weakness.",
    "Sector dispersion widens; no clear leadership emerging.",
    "Breadth deteriorates despite headline index stability.",
    "Short interest rising across small-cap tech names.",
    "Corporate buyback activity picks up after earnings blackout ends.",
    "Credit spreads hold steady; no signs of stress.",
    "Commodity prices steady; energy complex quiet.",
    "Thin tape conditions amplify intraday swings.",
    "Analysts revise Q3 EPS estimates modestly lower.",
    "IPO pipeline building; several filings expected this week.",
    "Momentum factor underperforms; value screens outpacing.",
    "Market-on-close imbalances lean to the buy side.",
    "Dealers report hedging flows dominating morning session.",
    "Macro calendar light today; market self-directed.",
    "Passive fund rebalancing likely ahead of month-end.",
    "Dollar softens slightly; multinationals catch a bid.",
    "Put/call ratio elevated, suggesting cautious sentiment.",
    "Earnings season winding down; focus shifts to guidance.",
]

EVENTS = [
    # ── Tech positive ──
    {"msg": "AI infrastructure spending accelerates; hyperscalers raise capex guidance", "Tech": 0.07, "Energy": 0.01, "Finance": 0.02, "duration": 20},
    {"msg": "Semiconductor cycle turns; foundry utilisation hits 18-month high", "Tech": 0.06, "Energy": 0, "Finance": 0.01, "duration": 18},
    {"msg": "Cloud migration wave drives software ARR growth to record levels", "Tech": 0.05, "Energy": 0, "Finance": 0.02, "duration": 16},
    {"msg": "Tech earnings season opens with broad beats; guidance raised across board", "Tech": 0.08, "Energy": 0, "Finance": 0.02, "duration": 15},
    {"msg": "Enterprise software spending rebounds as IT budgets unfrozen", "Tech": 0.04, "Energy": 0, "Finance": 0.01, "duration": 14},
    {"msg": "Autonomous vehicle milestone achieved; sector rerated higher", "Tech": 0.05, "Energy": -0.02, "Finance": 0.01, "duration": 16},
    # ── Tech negative ──
    {"msg": "EU antitrust regulators open sweeping probe into big tech platforms", "Tech": -0.06, "Energy": 0, "Finance": -0.01, "duration": 20},
    {"msg": "Chip export restrictions tightened; Asia supply chain disruption feared", "Tech": -0.07, "Energy": 0, "Finance": -0.01, "duration": 22},
    {"msg": "Cybersecurity incident exposes data of 200 million users; sector under pressure", "Tech": -0.06, "Energy": 0, "Finance": -0.02, "duration": 20},
    {"msg": "Tech layoffs accelerate; headcount reductions signal demand slowdown", "Tech": -0.04, "Energy": 0, "Finance": -0.01, "duration": 16},
    {"msg": "AI regulation bill advances in Congress; compliance costs seen rising sharply", "Tech": -0.05, "Energy": 0, "Finance": -0.01, "duration": 18},
    {"msg": "DRAM oversupply worsens; memory chip prices fall to multi-year lows", "Tech": -0.05, "Energy": 0, "Finance": 0, "duration": 16},
    # ── Energy positive ──
    {"msg": "OPEC+ agrees surprise production cut of 1.5 million barrels per day", "Tech": -0.01, "Energy": 0.09, "Finance": 0.01, "duration": 22},
    {"msg": "Geopolitical tensions in Strait of Hormuz spike crude premium", "Tech": -0.01, "Energy": 0.08, "Finance": -0.01, "duration": 20},
    {"msg": "Natural gas supply disruption in Europe pushes LNG prices to record", "Tech": 0, "Energy": 0.07, "Finance": 0, "duration": 18},
    {"msg": "Inventory draw larger than expected; crude rallies on supply tightness", "Tech": 0, "Energy": 0.05, "Finance": 0.01, "duration": 14},
    {"msg": "Energy sector posts best quarterly earnings in three years", "Tech": 0.01, "Energy": 0.06, "Finance": 0.01, "duration": 15},
    {"msg": "Cold snap drives heating demand surge; utilities and energy rally in tandem", "Tech": 0, "Energy": 0.05, "Finance": 0, "duration": 14},
    # ── Energy negative ──
    {"msg": "Global recession fears deepen; oil demand outlook cut by IEA", "Tech": -0.02, "Energy": -0.08, "Finance": -0.03, "duration": 22},
    {"msg": "OPEC+ compliance breaks down; Saudi Arabia floods market with crude", "Tech": 0, "Energy": -0.09, "Finance": -0.01, "duration": 22},
    {"msg": "Electric vehicle adoption hits inflection; long-term oil demand forecast cut", "Tech": 0.03, "Energy": -0.06, "Finance": 0, "duration": 20},
    {"msg": "US shale output hits record high; WTI slumps on supply glut", "Tech": 0, "Energy": -0.06, "Finance": 0, "duration": 18},
    {"msg": "Warm winter forecast slashes natural gas demand outlook", "Tech": 0, "Energy": -0.05, "Finance": 0, "duration": 16},
    # ── Finance positive ──
    {"msg": "Fed signals end of rate-hiking cycle; financial conditions ease sharply", "Tech": 0.04, "Energy": 0.01, "Finance": 0.08, "duration": 22},
    {"msg": "Bank stress tests pass with wide capital cushions; buybacks greenlit", "Tech": 0, "Energy": 0, "Finance": 0.07, "duration": 18},
    {"msg": "M&A volumes surge as deal-making thaws after prolonged drought", "Tech": 0.02, "Energy": 0.01, "Finance": 0.06, "duration": 18},
    {"msg": "Investment banking fee revenue hits two-year high on IPO and bond issuance", "Tech": 0.01, "Energy": 0, "Finance": 0.07, "duration": 16},
    {"msg": "Consumer credit quality improves; delinquency rates fall to cycle lows", "Tech": 0, "Energy": 0, "Finance": 0.05, "duration": 14},
    {"msg": "Yield curve steepens; net interest margin expansion boosts bank outlook", "Tech": 0, "Energy": 0, "Finance": 0.06, "duration": 16},
    # ── Finance negative ──
    {"msg": "Regional bank liquidity fears resurface; deposit outflows reported", "Tech": -0.02, "Energy": 0, "Finance": -0.09, "duration": 24},
    {"msg": "Fed delivers hawkish surprise; rate path re-priced aggressively higher", "Tech": -0.03, "Energy": -0.01, "Finance": -0.07, "duration": 22},
    {"msg": "Commercial real estate losses force major lender to raise emergency capital", "Tech": -0.01, "Energy": 0, "Finance": -0.08, "duration": 22},
    {"msg": "Credit card charge-off rates spike; consumer health concerns intensify", "Tech": -0.01, "Energy": 0, "Finance": -0.06, "duration": 18},
    {"msg": "Regulators propose strict new capital requirements under Basel IV revision", "Tech": -0.01, "Energy": 0, "Finance": -0.06, "duration": 20},
    {"msg": "Sovereign debt concerns reignite; spreads on peripheral bonds widen sharply", "Tech": -0.02, "Energy": -0.01, "Finance": -0.07, "duration": 20},
    # ── Macro / cross-sector ──
    {"msg": "CPI prints above consensus for third consecutive month; stagflation fears grow", "Tech": -0.04, "Energy": 0.02, "Finance": -0.05, "duration": 22},
    {"msg": "Unemployment rate falls to 50-year low; soft landing narrative gains traction", "Tech": 0.03, "Energy": 0.02, "Finance": 0.04, "duration": 18},
    {"msg": "GDP growth revised sharply higher; cyclicals broadly outperform", "Tech": 0.03, "Energy": 0.03, "Finance": 0.05, "duration": 18},
    {"msg": "Recession confirmed by two consecutive quarters of negative GDP", "Tech": -0.05, "Energy": -0.04, "Finance": -0.07, "duration": 24},
    {"msg": "Government shutdown looms; defence and federal contractor stocks sold", "Tech": -0.02, "Energy": -0.01, "Finance": -0.03, "duration": 18},
    {"msg": "Trade war escalates; broad tariff announcement roils equities", "Tech": -0.05, "Energy": -0.02, "Finance": -0.04, "duration": 22},
    {"msg": "Landmark trade deal signed; risk assets rally across the board", "Tech": 0.04, "Energy": 0.03, "Finance": 0.04, "duration": 18},
    {"msg": "Dollar surges to multi-decade high; multinationals face FX headwinds", "Tech": -0.03, "Energy": -0.01, "Finance": 0.01, "duration": 18},
]

COMPANY_EVENTS = [
    {"sym": "AAPL", "msg": "Apple launches new iPhone", "impact": 0.04, "competitors": {"MSFT": -0.02, "GOOG": -0.01},
     "duration": 12},
    {"sym": "AAPL", "msg": "Apple faces supply chain issues", "impact": -0.04,
     "competitors": {"MSFT": 0.01, "GOOG": 0.01}, "duration": 12},
    {"sym": "AAPL", "msg": "Apple posts record earnings", "impact": 0.03,
     "competitors": {"MSFT": -0.01, "GOOG": -0.005}, "duration": 12},

    {"sym": "MSFT", "msg": "Microsoft releases major software update", "impact": 0.04,
     "competitors": {"AAPL": -0.01, "GOOG": -0.01}, "duration": 12},
    {"sym": "MSFT", "msg": "Microsoft faces security breach", "impact": -0.05,
     "competitors": {"AAPL": 0.01, "GOOG": 0.005}, "duration": 12},
    {"sym": "MSFT", "msg": "Microsoft acquires AI startup", "impact": 0.03,
     "competitors": {"AAPL": -0.005, "GOOG": -0.01}, "duration": 12},

    {"sym": "GOOG", "msg": "Google wins major government contract", "impact": 0.04,
     "competitors": {"MSFT": -0.015, "AAPL": -0.005}, "duration": 12},
    {"sym": "GOOG", "msg": "Google fined for antitrust violation", "impact": -0.05,
     "competitors": {"MSFT": 0.01, "AAPL": 0.005}, "duration": 12},
    {"sym": "GOOG", "msg": "Google acquires AI startup", "impact": 0.03, "competitors": {"MSFT": -0.01, "AAPL": -0.005},
     "duration": 12},

    {"sym": "NVDA", "msg": "NVIDIA announces new GPU", "impact": 0.04, "competitors": {"AMD": -0.02}, "duration": 12},
    {"sym": "NVDA", "msg": "NVIDIA faces chip shortage", "impact": -0.05, "competitors": {"AMD": 0.01}, "duration": 12},
    {"sym": "NVDA", "msg": "NVIDIA beats earnings expectations", "impact": 0.04, "competitors": {"AMD": -0.01},
     "duration": 12},

    {"sym": "AMD", "msg": "AMD releases next-gen CPU", "impact": 0.04, "competitors": {"NVDA": -0.02}, "duration": 12},
    {"sym": "AMD", "msg": "AMD factory shutdown", "impact": -0.04, "competitors": {"NVDA": 0.01}, "duration": 12},
    {"sym": "AMD", "msg": "AMD posts strong earnings", "impact": 0.03, "competitors": {"NVDA": -0.01}, "duration": 12},

    {"sym": "ORCL", "msg": "Oracle wins cloud contract", "impact": 0.03, "competitors": {"MSFT": -0.01},
     "duration": 12},
    {"sym": "ORCL", "msg": "Oracle faces software lawsuit", "impact": -0.04, "competitors": {"MSFT": 0.01},
     "duration": 12},
    {"sym": "ORCL", "msg": "Oracle launches new cloud service", "impact": 0.05, "competitors": {"MSFT": -0.01},
     "duration": 12},

    {"sym": "META", "msg": "Meta launches new VR device", "impact": 0.04, "competitors": {"AAPL": -0.02},
     "duration": 12},
    {"sym": "META", "msg": "Meta faces ad revenue drop", "impact": -0.04, "competitors": {"GOOG": 0.01},
     "duration": 12},
    {"sym": "META", "msg": "Meta reports user growth surge", "impact": 0.03, "competitors": {"AAPL": -0.005},
     "duration": 12},

    {"sym": "INTC", "msg": "Intel announces new chip line", "impact": 0.04, "competitors": {"AMD": -0.02},
     "duration": 12},
    {"sym": "INTC", "msg": "Intel delays chip production", "impact": -0.05, "competitors": {"AMD": 0.01},
     "duration": 12},
    {"sym": "INTC", "msg": "Intel posts strong earnings", "impact": 0.03, "competitors": {"AMD": -0.01},
     "duration": 12},

    {"sym": "TSLA", "msg": "Tesla announces new EV model", "impact": 0.04, "competitors": {"GM": -0.02, "F": -0.01},
     "duration": 12},
    {"sym": "TSLA", "msg": "Tesla recalls vehicles", "impact": -0.05, "competitors": {"GM": 0.02, "F": 0.01},
     "duration": 12},
    {"sym": "TSLA", "msg": "Tesla expands production", "impact": 0.04, "competitors": {"GM": -0.01, "F": -0.005},
     "duration": 12},

    {"sym": "ADBE", "msg": "Adobe releases new creative suite", "impact": 0.04, "competitors": {"ORCL": -0.01},
     "duration": 12},
    {"sym": "ADBE", "msg": "Adobe faces software bug backlash", "impact": -0.04, "competitors": {"ORCL": 0.01},
     "duration": 12},
    {"sym": "ADBE", "msg": "Adobe posts record subscription growth", "impact": 0.03, "competitors": {"ORCL": -0.005},
     "duration": 12},

    {"sym": "XOM", "msg": "Exxon announces oil discovery", "impact": 0.04, "competitors": {"CVX": -0.02},
     "duration": 12},
    {"sym": "XOM", "msg": "Exxon faces environmental lawsuit", "impact": -0.04, "competitors": {"CVX": 0.01},
     "duration": 12},
    {"sym": "XOM", "msg": "Exxon posts strong earnings", "impact": 0.03, "competitors": {"CVX": -0.01}, "duration": 12},

    {"sym": "CVX", "msg": "Chevron discovers new oil field", "impact": 0.04, "competitors": {"XOM": -0.02},
     "duration": 12},
    {"sym": "CVX", "msg": "Chevron fined for spill", "impact": -0.04, "competitors": {"XOM": 0.01}, "duration": 12},
    {"sym": "CVX", "msg": "Chevron reports record profits", "impact": 0.03, "competitors": {"XOM": -0.01},
     "duration": 12},

    {"sym": "BP", "msg": "BP expands renewable energy", "impact": 0.04, "competitors": {"XOM": -0.01}, "duration": 12},
    {"sym": "BP", "msg": "BP pipeline leak reported", "impact": -0.05, "competitors": {"XOM": 0.01}, "duration": 12},
    {"sym": "BP", "msg": "BP earnings beat expectations", "impact": 0.03, "competitors": {"XOM": -0.005},
     "duration": 12},

    {"sym": "COP", "msg": "ConocoPhillips boosts production", "impact": 0.04, "competitors": {"XOM": -0.01},
     "duration": 12},
    {"sym": "COP", "msg": "ConocoPhillips faces drilling ban", "impact": -0.04, "competitors": {"XOM": 0.01},
     "duration": 12},
    {"sym": "COP", "msg": "ConocoPhillips posts strong profits", "impact": 0.03, "competitors": {"XOM": -0.005},
     "duration": 12},

    {"sym": "SLB", "msg": "Schlumberger wins major contract", "impact": 0.04, "competitors": {"HAL": -0.02},
     "duration": 12},
    {"sym": "SLB", "msg": "Schlumberger faces equipment issues", "impact": -0.05, "competitors": {"HAL": 0.01},
     "duration": 12},
    {"sym": "SLB", "msg": "Schlumberger reports earnings beat", "impact": 0.03, "competitors": {"HAL": -0.01},
     "duration": 12},

    {"sym": "HAL", "msg": "Halliburton secures oil drilling deal", "impact": 0.04, "competitors": {"SLB": -0.02},
     "duration": 12},
    {"sym": "HAL", "msg": "Halliburton faces labor strike", "impact": -0.05, "competitors": {"SLB": 0.01},
     "duration": 12},
    {"sym": "HAL", "msg": "Halliburton posts record earnings", "impact": 0.03, "competitors": {"SLB": -0.01},
     "duration": 12},

    {"sym": "MRO", "msg": "Marathon Oil reports higher output", "impact": 0.04, "competitors": {"OXY": -0.02},
     "duration": 12},
    {"sym": "MRO", "msg": "Marathon Oil fined for spill", "impact": -0.04, "competitors": {"OXY": 0.01},
     "duration": 12},
    {"sym": "MRO", "msg": "Marathon Oil posts strong earnings", "impact": 0.03, "competitors": {"OXY": -0.01},
     "duration": 12},

    {"sym": "PSX", "msg": "Phillips 66 boosts refining capacity", "impact": 0.04, "competitors": {"VLO": -0.01},
     "duration": 12},
    {"sym": "PSX", "msg": "Phillips 66 reports accident at plant", "impact": -0.05, "competitors": {"VLO": 0.01},
     "duration": 12},
    {"sym": "PSX", "msg": "Phillips 66 posts profits above estimates", "impact": 0.03, "competitors": {"VLO": -0.005},
     "duration": 12},

    {"sym": "VLO", "msg": "Valero announces expansion plans", "impact": 0.04, "competitors": {"PSX": -0.01},
     "duration": 12},
    {"sym": "VLO", "msg": "Valero faces supply disruption", "impact": -0.04, "competitors": {"PSX": 0.01},
     "duration": 12},
    {"sym": "VLO", "msg": "Valero earnings exceed expectations", "impact": 0.03, "competitors": {"PSX": -0.005},
     "duration": 12},

    {"sym": "OXY", "msg": "Occidental boosts oil production", "impact": 0.04, "competitors": {"MRO": -0.02},
     "duration": 12},
    {"sym": "OXY", "msg": "Occidental faces legal issues", "impact": -0.04, "competitors": {"MRO": 0.01},
     "duration": 12},
    {"sym": "OXY", "msg": "Occidental posts strong earnings", "impact": 0.03, "competitors": {"MRO": -0.01},
     "duration": 12},

    {"sym": "JPM", "msg": "JP Morgan posts record profits", "impact": 0.04, "competitors": {"BAC": -0.01},
     "duration": 12},
    {"sym": "JPM", "msg": "JP Morgan hit by fraud scandal", "impact": -0.05, "competitors": {"BAC": 0.01},
     "duration": 12},
    {"sym": "JPM", "msg": "JP Morgan expands investment banking", "impact": 0.03, "competitors": {"BAC": -0.005},
     "duration": 12},

    {"sym": "BAC", "msg": "Bank of America posts strong earnings", "impact": 0.04, "competitors": {"JPM": -0.01},
     "duration": 12},
    {"sym": "BAC", "msg": "Bank of America fined for compliance issues", "impact": -0.04, "competitors": {"JPM": 0.01},
     "duration": 12},
    {"sym": "BAC", "msg": "Bank of America acquires regional bank", "impact": 0.03, "competitors": {"JPM": -0.005},
     "duration": 12},

    {"sym": "GS", "msg": "Goldman Sachs reports strong trading day", "impact": 0.04, "competitors": {"MS": -0.01},
     "duration": 12},
    {"sym": "GS", "msg": "Goldman Sachs faces regulatory investigation", "impact": -0.05, "competitors": {"MS": 0.01},
     "duration": 12},
    {"sym": "GS", "msg": "Goldman Sachs launches new fund", "impact": 0.03, "competitors": {"MS": -0.005},
     "duration": 12},

    {"sym": "MS", "msg": "Morgan Stanley sees investment surge", "impact": 0.04, "competitors": {"GS": -0.01},
     "duration": 12},
    {"sym": "MS", "msg": "Morgan Stanley fined for trading violation", "impact": -0.05, "competitors": {"GS": 0.01},
     "duration": 12},
    {"sym": "MS", "msg": "Morgan Stanley expands wealth management", "impact": 0.03, "competitors": {"GS": -0.005},
     "duration": 12},

    {"sym": "C", "msg": "Citigroup reports strong earnings", "impact": 0.04, "competitors": {"WFC": -0.01},
     "duration": 12},
    {"sym": "C", "msg": "Citigroup hit by legal settlement", "impact": -0.04, "competitors": {"WFC": 0.01},
     "duration": 12},
    {"sym": "C", "msg": "Citigroup expands credit offerings", "impact": 0.03, "competitors": {"WFC": -0.005},
     "duration": 12},

    {"sym": "WFC", "msg": "Wells Fargo posts profit beat", "impact": 0.04, "competitors": {"C": -0.01}, "duration": 12},
    {"sym": "WFC", "msg": "Wells Fargo faces compliance fines", "impact": -0.04, "competitors": {"C": 0.01},
     "duration": 12},
    {"sym": "WFC", "msg": "Wells Fargo expands mortgage business", "impact": 0.03, "competitors": {"C": -0.005},
     "duration": 12},

    {"sym": "BLK", "msg": "BlackRock sees record fund inflows", "impact": 0.04, "competitors": {"AXP": -0.01},
     "duration": 12},
    {"sym": "BLK", "msg": "BlackRock fined for compliance issues", "impact": -0.04, "competitors": {"AXP": 0.01},
     "duration": 12},
    {"sym": "BLK", "msg": "BlackRock acquires boutique firm", "impact": 0.03, "competitors": {"AXP": -0.005},
     "duration": 12},

    {"sym": "AXP", "msg": "American Express posts strong earnings", "impact": 0.04, "competitors": {"BLK": -0.01},
     "duration": 12},
    {"sym": "AXP", "msg": "American Express hit by fraud investigation", "impact": -0.04, "competitors": {"BLK": 0.01},
     "duration": 12},
    {"sym": "AXP", "msg": "American Express expands credit cards", "impact": 0.03, "competitors": {"BLK": -0.005},
     "duration": 12},

    {"sym": "SCHW", "msg": "Charles Schwab reports strong trading activity", "impact": 0.04,
     "competitors": {"USB": -0.01}, "duration": 12},
    {"sym": "SCHW", "msg": "Charles Schwab faces regulatory issue", "impact": -0.04, "competitors": {"USB": 0.01},
     "duration": 12},
    {"sym": "SCHW", "msg": "Charles Schwab launches new investment tool", "impact": 0.03,
     "competitors": {"USB": -0.005}, "duration": 12},

    {"sym": "USB", "msg": "US Bancorp posts record profits", "impact": 0.04, "competitors": {"SCHW": -0.01},
     "duration": 12},
    {"sym": "USB", "msg": "US Bancorp faces legal settlement", "impact": -0.04, "competitors": {"SCHW": 0.01},
     "duration": 12},
    {"sym": "USB", "msg": "US Bancorp expands consumer banking", "impact": 0.03, "competitors": {"SCHW": -0.005},
     "duration": 12},
]


def generate_company_event():
    event = random.choice(COMPANY_EVENTS)
    return {
        "msg": event["msg"],
        "winners": {event["sym"]: event["impact"]} if event["impact"] > 0 else {},
        "losers": {event["sym"]: event["impact"]} if event["impact"] < 0 else {},
        "competitors": event.get("competitors", {}),
        "duration": event["duration"]
    }


def short_stock(sym, shares):
    price = get_price(sym)
    proceeds = price * shares
    st.session_state.cash += proceeds
    prev_shares = st.session_state.short_positions.get(sym, 0)
    prev_basis  = st.session_state.short_basis.get(sym, 0.0)
    new_shares  = prev_shares + shares
    st.session_state.short_basis[sym]     = (prev_basis * prev_shares + price * shares) / new_shares
    st.session_state.short_positions[sym] = new_shares
    st.session_state.trade_history.insert(0, {'action': 'Short', 'sym': sym, 'shares': shares, 'price': price})
    st.session_state.short_count += 1
    st.session_state.total_trades += 1


def cover_short(sym, shares):
    owed = st.session_state.short_positions.get(sym, 0)
    if owed >= shares:
        price = get_price(sym)
        cost  = price * shares
        if st.session_state.cash >= cost:
            st.session_state.cash -= cost
            basis   = st.session_state.short_basis.get(sym, price)
            pnl     = (basis - price) * shares  # profit when price fell
            if pnl > 0:
                st.session_state.profitable_trades += 1
            elif pnl < 0:
                st.session_state.loss_trades += 1
            remain = owed - shares
            if remain == 0:
                del st.session_state.short_positions[sym]
                st.session_state.short_basis.pop(sym, None)
            else:
                st.session_state.short_positions[sym] = remain
            st.session_state.trade_history.insert(0, {'action': 'Cover', 'sym': sym, 'shares': shares, 'price': price})
            st.session_state.cover_count += 1


def init():
    if "stocks" not in st.session_state:
        stocks = {}
        for sec, tickers in SECTORS.items():
            for t in tickers:
                stocks[t] = {
                    "sector": sec,
                    "prices": [round(random.uniform(50, 400), 2)],
                    "vol": random.uniform(0.20, 0.45),
                    "drift": random.uniform(0.05, 0.15),
                    "event_drift": 0.0,
                    "event_smooth": 0.0
                }
        st.session_state.stocks = stocks

    defaults = {
        "cash": 100000.0,
        "portfolio": {},
        "short_positions": {},
        "cost_basis": {},
        "short_basis": {},
        "trade_history": [],
        "news": [],
        "clock_paused": True,
        "speed": "1x",
        "minute": MARKET_OPEN,
        "min_acc": 0.0,
        "active_event": None,
        "event_ticks_left": 0,
        "company_event": None,
        "company_ticks_left": 0,
        "banner": None,
        "sector_history": {s: [] for s in SECTORS},
        "net_worth_history": [],
        "banner": None,
        "banner_ticks": 0,
        "auto_pause_events": True,
        "bankrupt": False,
        "xp": 0,
        "level": 1,
        "rank": "Trainee",
        "total_trades": 0,
        "short_count": 0,
        "cover_count": 0,
        "profitable_trades": 0,
        "loss_trades": 0,
        "peak_net_worth": 100000.0,
        "sector_profits": {s: 0.0 for s in SECTORS},
        "sector_trades": {s: 0 for s in SECTORS},
        "objectives": [
            # ── Tier 1: Getting Started ──
            {"id":  1, "tier": 1, "task": "Make your first trade",               "target": 1,       "type": "trade_count",    "reward": 100,   "done": False},
            {"id":  2, "tier": 1, "task": "Grow to $105,000",                    "target": 105000,  "type": "net_worth",      "reward": 150,   "done": False},
            {"id":  3, "tier": 1, "task": "Execute 5 trades",                    "target": 5,       "type": "trade_count",    "reward": 200,   "done": False},
            {"id":  4, "tier": 1, "task": "Hold 3 different stocks at once",     "target": 3,       "type": "hold_count",     "reward": 200,   "done": False},
            {"id":  5, "tier": 1, "task": "Reach $110,000 net worth",            "target": 110000,  "type": "net_worth",      "reward": 300,   "done": False},
            {"id":  6, "tier": 1, "task": "Place your first short",              "target": 1,       "type": "short_count",    "reward": 250,   "done": False},
            # ── Tier 2: Building a Book ──
            {"id":  7, "tier": 2, "task": "Reach $150,000 net worth",            "target": 150000,  "type": "net_worth",      "reward": 500,   "done": False},
            {"id":  8, "tier": 2, "task": "Execute 20 trades",                   "target": 20,      "type": "trade_count",    "reward": 400,   "done": False},
            {"id":  9, "tier": 2, "task": "Hold 6 different stocks at once",     "target": 6,       "type": "hold_count",     "reward": 500,   "done": False},
            {"id": 10, "tier": 2, "task": "Profit $2,000 from Tech trades",      "target": 2000,    "type": "sector_profit",  "sector": "Tech",    "reward": 600,   "done": False},
            {"id": 11, "tier": 2, "task": "Profit $2,000 from Energy trades",    "target": 2000,    "type": "sector_profit",  "sector": "Energy",  "reward": 600,   "done": False},
            {"id": 12, "tier": 2, "task": "Reach $200,000 net worth",            "target": 200000,  "type": "net_worth",      "reward": 750,   "done": False},
            {"id": 13, "tier": 2, "task": "Cover 5 short positions",             "target": 5,       "type": "cover_count",    "reward": 500,   "done": False},
            # ── Tier 3: Serious Trader ──
            {"id": 14, "tier": 3, "task": "Reach $500,000 net worth",            "target": 500000,  "type": "net_worth",      "reward": 1500,  "done": False},
            {"id": 15, "tier": 3, "task": "Execute 50 trades",                   "target": 50,      "type": "trade_count",    "reward": 1000,  "done": False},
            {"id": 16, "tier": 3, "task": "Hold 8 different stocks at once",     "target": 8,       "type": "hold_count",     "reward": 1200,  "done": False},
            {"id": 17, "tier": 3, "task": "Profit $20,000 from Tech trades",     "target": 20000,   "type": "sector_profit",  "sector": "Tech",    "reward": 1500,  "done": False},
            {"id": 18, "tier": 3, "task": "Profit $20,000 from Finance trades",  "target": 20000,   "type": "sector_profit",  "sector": "Finance", "reward": 1500,  "done": False},
            {"id": 19, "tier": 3, "task": "Execute 10 short positions",          "target": 10,      "type": "short_count",    "reward": 1200,  "done": False},
            {"id": 20, "tier": 3, "task": "Reach $1,000,000 net worth",          "target": 1000000, "type": "net_worth",      "reward": 3000,  "done": False},
            # ── Tier 4: Market Operator ──
            {"id": 21, "tier": 4, "task": "Reach $2,500,000 net worth",          "target": 2500000, "type": "net_worth",      "reward": 6000,  "done": False},
            {"id": 22, "tier": 4, "task": "Execute 100 trades",                  "target": 100,     "type": "trade_count",    "reward": 4000,  "done": False},
            {"id": 23, "tier": 4, "task": "Profit $100,000 from Tech trades",    "target": 100000,  "type": "sector_profit",  "sector": "Tech",    "reward": 5000,  "done": False},
            {"id": 24, "tier": 4, "task": "Profit $100,000 from Energy trades",  "target": 100000,  "type": "sector_profit",  "sector": "Energy",  "reward": 5000,  "done": False},
            {"id": 25, "tier": 4, "task": "Profit $100,000 from Finance trades", "target": 100000,  "type": "sector_profit",  "sector": "Finance", "reward": 5000,  "done": False},
            {"id": 26, "tier": 4, "task": "Execute 25 short positions",          "target": 25,      "type": "short_count",    "reward": 5000,  "done": False},
            {"id": 27, "tier": 4, "task": "Reach $5,000,000 net worth",          "target": 5000000, "type": "net_worth",      "reward": 10000, "done": False},
            # ── Tier 5: Elite ──
            {"id": 28, "tier": 5, "task": "Reach $10,000,000 net worth",         "target": 10000000,"type": "net_worth",      "reward": 25000, "done": False},
            {"id": 29, "tier": 5, "task": "Execute 250 trades",                  "target": 250,     "type": "trade_count",    "reward": 15000, "done": False},
            {"id": 30, "tier": 5, "task": "Profit $500,000 in a single sector",  "target": 500000,  "type": "any_sector_profit","reward": 20000, "done": False},
            {"id": 31, "tier": 5, "task": "Execute 50 short positions",          "target": 50,      "type": "short_count",    "reward": 20000, "done": False},
            {"id": 32, "tier": 5, "task": "Hold 10 different stocks at once",    "target": 10,      "type": "hold_count",     "reward": 15000, "done": False},
            {"id": 33, "tier": 5, "task": "The Endgame: Reach $25,000,000",      "target": 25000000,"type": "net_worth",      "reward": 50000, "done": False},
        ]
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # Migration: if any stored objective is missing "tier", replace the whole list
    # with the current definition so new fields are present.
    if st.session_state.objectives and "tier" not in st.session_state.objectives[0]:
        st.session_state.objectives = defaults["objectives"]

    # Migration: add any other missing keys added in later versions
    migration_defaults = {
        "cost_basis": {}, "short_basis": {}, "net_worth_history": [],
        "watchlist": [], "price_alerts": [], "auto_pause_events": True,
        "bankrupt": False, "cover_count": 0, "profitable_trades": 0,
        "loss_trades": 0, "peak_net_worth": 100000.0,
        "sector_trades": {s: 0 for s in SECTORS},
        "banner_ticks": 0,
    }
    for key, val in migration_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def buy_stock(sym, shares):
    price = get_price(sym)
    cost = price * shares

    if st.session_state.cash >= cost:
        st.session_state.cash -= cost
        prev_shares = st.session_state.portfolio.get(sym, 0)
        prev_basis  = st.session_state.cost_basis.get(sym, 0.0)
        new_shares  = prev_shares + shares
        # weighted average cost basis
        st.session_state.cost_basis[sym] = (prev_basis * prev_shares + price * shares) / new_shares
        st.session_state.portfolio[sym]  = new_shares
        st.session_state.total_trades += 1
        st.session_state.trade_history.insert(0, {
            "action": "Buy", "sym": sym, "shares": shares, "price": price
        })


# FIX 2: sell_stock had a double-if that could track profits without paying out cash.
# Merged into a single guard so sector_profits, total_trades, and cash update atomically.
def sell_stock(sym, shares):
    if st.session_state.portfolio.get(sym, 0) >= shares:
        price  = get_price(sym)
        sector = st.session_state.stocks[sym]["sector"]
        basis  = st.session_state.cost_basis.get(sym, price)
        pnl    = (price - basis) * shares
        if pnl > 0:
            st.session_state.profitable_trades += 1
        elif pnl < 0:
            st.session_state.loss_trades += 1
        st.session_state.cash += price * shares
        st.session_state.portfolio[sym] -= shares
        if st.session_state.portfolio[sym] == 0:
            del st.session_state.portfolio[sym]
            st.session_state.cost_basis.pop(sym, None)
        st.session_state.sector_profits[sector] += pnl   # actual profit, not gross
        st.session_state.sector_trades[sector]  += 1
        st.session_state.total_trades += 1
        st.session_state.trade_history.insert(0, {
            "action": "Sell", "sym": sym, "shares": shares, "price": price
        })


init()


def fmt(m):
    w = m % 1440
    return f"{w // 60:02d}:{w % 60:02d}"


def is_open(m):
    w = m % 1440
    return MARKET_OPEN <= w < MARKET_CLOSE


def get_price(sym):
    return st.session_state.stocks[sym]["prices"][-1]


def portfolio_value():
    long_val = sum(get_price(s) * q for s, q in st.session_state.portfolio.items())
    short_liab = sum(
        get_price(s) * q for s, q in st.session_state.get("short_positions", {}).items()
    )
    return st.session_state.cash + long_val - short_liab


# FIX 3: update_rank was defined twice; second definition silently overwrote the first.
# Kept one copy only.
def update_rank():
    ranks = ["Trainee","Analyst","Associate","Senior Associate","Vice President",
             "Director","Managing Director","Partner","Market Maker","Legend"]
    idx = min(st.session_state.level - 1, len(ranks) - 1)
    st.session_state.rank = ranks[idx]


def complete_objective(obj):
    if not obj["done"]:
        obj["done"] = True
        st.session_state.xp += obj["reward"]
        xp_needed = st.session_state.level * 2500
        if st.session_state.xp >= xp_needed:
            st.session_state.xp -= xp_needed
            st.session_state.level += 1
            update_rank()


# FIX 5: removed the redundant inner check_objectives() from tick() and the separate
# check_game_logic() call. One unified check_objectives() handles all objective types.
def check_objectives():
    pv = portfolio_value()
    st.session_state.peak_net_worth = max(st.session_state.peak_net_worth, pv)
    holdings = len(st.session_state.portfolio) + len(st.session_state.short_positions)
    for obj in st.session_state.objectives:
        if not obj["done"]:
            t = obj["type"]
            if t == "net_worth" and pv >= obj["target"]:
                complete_objective(obj)
            elif t == "trade_count" and st.session_state.total_trades >= obj["target"]:
                complete_objective(obj)
            elif t == "short_count" and st.session_state.short_count >= obj["target"]:
                complete_objective(obj)
            elif t == "cover_count" and st.session_state.cover_count >= obj["target"]:
                complete_objective(obj)
            elif t == "hold_count" and holdings >= obj["target"]:
                complete_objective(obj)
            elif t == "sector_profit" and st.session_state.sector_profits[obj["sector"]] >= obj["target"]:
                complete_objective(obj)
            elif t == "any_sector_profit" and any(v >= obj["target"] for v in st.session_state.sector_profits.values()):
                complete_objective(obj)


def tick():
    steps = SPEEDS[st.session_state.speed]
    st.session_state.min_acc += steps

    whole = int(st.session_state.min_acc)
    st.session_state.min_acc -= whole

    DT = 1.0 / 98280.0

    for _ in range(whole):
        st.session_state.minute += 1

        new_sector_event = None
        new_company_event = None

        if random.random() < 0.005:
            ev = random.choice(EVENTS)
            st.session_state.active_event = ev
            st.session_state.event_ticks_left = ev["duration"]
            st.session_state.news.insert(0, ev["msg"])
            st.session_state.banner = ev["msg"]
            st.session_state.banner_ticks = 30
            new_sector_event = ev

        if random.random() < 0.003:
            ce = generate_company_event()
            st.session_state.company_event = ce
            st.session_state.company_ticks_left = ce["duration"]
            st.session_state.news.insert(0, ce["msg"])
            st.session_state.banner = ce["msg"]
            st.session_state.banner_ticks = 30
            new_company_event = ce

        for sym, s in st.session_state.stocks.items():
            last  = s["prices"][-1]
            vol   = s["vol"]
            drift = s["drift"]

            instant_pct = 0.0

            if new_sector_event:
                sector_impact = new_sector_event.get(s["sector"], 0)
                if sector_impact != 0:
                    instant_pct += sector_impact * 0.40
                    s["event_drift"] = s.get("event_drift", 0.0) + sector_impact * 0.012

            if new_company_event:
                sym_impact = (
                    new_company_event.get("winners", {}).get(sym, 0)
                    + new_company_event.get("losers",  {}).get(sym, 0)
                    + new_company_event.get("competitors", {}).get(sym, 0)
                )
                if sym_impact != 0:
                    instant_pct += sym_impact * 0.50
                    s["event_drift"] = s.get("event_drift", 0.0) + sym_impact * 0.018

            Z = np.random.normal(0, 1)
            if random.random() < 0.005:
                Z *= random.uniform(2.0, 3.5)

            gbm_return = (drift - 0.5 * vol ** 2) * DT + vol * np.sqrt(DT) * Z

            event_drift = s.get("event_drift", 0.0)
            event_drift *= 0.92
            s["event_drift"] = event_drift
            drift_contribution = event_drift * DT * 60

            if len(s["prices"]) >= 20:
                ma20 = sum(s["prices"][-20:]) / 20.0
                reversion = -0.003 * (last - ma20) / ma20
            else:
                reversion = 0.0

            gapped_price = last * (1.0 + instant_pct)
            total_log_return = gbm_return + drift_contribution + reversion
            new_price = gapped_price * np.exp(total_log_return)
            s["prices"].append(max(0.01, round(float(new_price), 4)))
            # Cap price history to last 2000 ticks
            if len(s["prices"]) > 2000:
                s["prices"] = s["prices"][-2000:]

        if random.random() < 0.02:
            st.session_state.news.insert(0, random.choice(FILLER_NEWS))

        if st.session_state.event_ticks_left > 0:
            st.session_state.event_ticks_left -= 1
            if st.session_state.event_ticks_left == 0:
                st.session_state.active_event = None

        if st.session_state.company_ticks_left > 0:
            st.session_state.company_ticks_left -= 1
            if st.session_state.company_ticks_left == 0:
                st.session_state.company_event = None

        if st.session_state.minute % 5 == 0:
            for sector, tickers in SECTORS.items():
                vals = [
                    (st.session_state.stocks[sym]["prices"][-1] - st.session_state.stocks[sym]["prices"][0])
                    / st.session_state.stocks[sym]["prices"][0] * 100
                    for sym in tickers
                ]
                st.session_state.sector_history[sector].append(sum(vals) / len(vals))
            # Cap sector history
            for sector in SECTORS:
                if len(st.session_state.sector_history[sector]) > 2000:
                    st.session_state.sector_history[sector] = st.session_state.sector_history[sector][-2000:]

        # Cap news feed
        if len(st.session_state.news) > 100:
            st.session_state.news = st.session_state.news[:100]

        # Auto-clear banner after 30 ticks
        if st.session_state.banner_ticks > 0:
            st.session_state.banner_ticks -= 1
            if st.session_state.banner_ticks == 0:
                st.session_state.banner = None

        # Sample net worth and check margin every 10 ticks — not every tick
        if st.session_state.minute % 10 == 0:
            pv_now = portfolio_value()
            st.session_state.net_worth_history.append(pv_now)
            if len(st.session_state.net_worth_history) > 2000:
                st.session_state.net_worth_history = st.session_state.net_worth_history[-2000:]
            if pv_now < 10000 and not st.session_state.bankrupt:
                st.session_state.bankrupt = True
                st.session_state.clock_paused = True
                st.session_state.banner = "💀 MARGIN CALL — You have been liquidated."
                st.session_state.news.insert(0, "💀 MARGIN CALL: Net worth fell below $10,000. Game over.")

    # Check objectives once per frame, not per tick
    check_objectives()


st_autorefresh(interval=400, key="auto")
if not st.session_state.clock_paused and not st.session_state.bankrupt:
    tick()

h1, h2, h3 = st.columns([3, 1, 4])

with h1:
    pv = portfolio_value()
    pnl = pv - 100000
    col = "#22c55e" if pnl >= 0 else "#ef4444"
    st.markdown(f"""
    <div>
        <div style='font-size:12px; color:#94a3b8; text-transform:uppercase;'>{st.session_state.rank} | LEVEL {st.session_state.level}</div>
        <span style='font-size:22px; font-weight:600;'>${pv:,.0f}</span>
        <span style='color:{col}; font-size:14px; margin-left:8px;'>{pnl:+,.0f}</span>
    </div>
    """, unsafe_allow_html=True)

with h3:
    cols = st.columns(len(SPEEDS) + 2)
    if cols[0].button("New"):
        st.session_state.clear()
        st.rerun()
    play_disabled = st.session_state.bankrupt
    if cols[1].button("▶" if st.session_state.clock_paused else "⏸", disabled=play_disabled):
        st.session_state.clock_paused = not st.session_state.clock_paused
        if not st.session_state.clock_paused:
            st.session_state.banner = None
    for i, k in enumerate(SPEEDS):
        if cols[i + 2].button(k):
            st.session_state.speed = k

if st.session_state.bankrupt:
    st.markdown("""
    <div style="background:linear-gradient(90deg,#1a0a0a,#2d0f0f);border:1px solid #ef4444;
        padding:16px;border-radius:10px;margin:10px 0 20px 0;color:#f8fafc;font-weight:600;
        font-size:16px;text-align:center;">
        💀 MARGIN CALL — Net worth fell below $10,000. Trading halted. Start a new game.
    </div>
    """, unsafe_allow_html=True)
elif st.session_state.get("banner"):
    st.markdown(f"""
    <div style="background:linear-gradient(90deg,#7f1d1d,#991b1b);border:1px solid #ef4444;
        padding:12px 16px;border-radius:10px;margin:10px 0 20px 0;color:#f8fafc;font-weight:600;
        font-size:14px;display:flex;justify-content:space-between;align-items:center;">
        <span>🔴 BREAKING: {st.session_state.banner}</span>
        <span style="opacity:0.7;font-size:12px;cursor:pointer;" onclick="this.parentElement.style.display='none'">✕</span>
    </div>
    """, unsafe_allow_html=True)
st.divider()

tabs = st.tabs(["Market", "Trade", "Portfolio", "News", "Career", "Instructions"])
with tabs[0]:
    import plotly.graph_objects as go

    sc = st.columns(len(SECTORS))

    for i, sector in enumerate(SECTORS):
        series = st.session_state.sector_history[sector]
        chg = series[-1] if series else 0

        color = "#22c55e" if chg >= 0 else "#ef4444"

        fig = go.Figure(go.Scatter(
            y=series,
            mode="lines",
            line=dict(color=color, width=2),
            fill="tozeroy",
            fillcolor="rgba(34,197,94,0.08)" if chg >= 0 else "rgba(239,68,68,0.08)"
        ))

        fig.update_layout(
            height=120,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="#111318",
            plot_bgcolor="#111318",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )

        with sc[i]:
            st.markdown(f"""
                <div style='background:#111318;border:1px solid #1e2330;border-radius:12px;padding:14px;'>
                    <div style='font-size:11px;color:#475569;text-transform:uppercase;'>{sector}</div>
                    <div style='font-size:22px;font-weight:700;color:{color};'>
                        {chg:+.2f}%
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=f"sector_{sector}")

    for sec, tickers in SECTORS.items():
        st.markdown(f"### {sec}")
        cols = st.columns(len(tickers))
        for i, s in enumerate(tickers):
            p      = get_price(s)
            prices = st.session_state.stocks[s]["prices"]
            chg    = (p - prices[0]) / prices[0] * 100
            c      = "#22c55e" if chg >= 0 else "#ef4444"
            cols[i].markdown(f"""
            <div style='background:#111318;border:1px solid #1e2330;border-radius:8px;padding:10px;'>
                <div style='font-size:12px;color:#94a3b8;'>{s}</div>
                <div style='font-size:16px;font-weight:700;'>${p:.2f}</div>
                <div style='font-size:11px;color:{c};'>{chg:+.1f}%</div>
            </div>
            """, unsafe_allow_html=True)

with tabs[1]:
    left, right = st.columns([2, 1])
    with left:
        sym = st.selectbox("Stock", ALL_SYMS,
                           format_func=lambda s: f"{s}  —  {st.session_state.stocks[s]['sector']}")
        prices = st.session_state.stocks[sym]["prices"]
        p = get_price(sym)
        chg = (p - prices[0]) / prices[0] * 100

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Price", f"${p:.2f}")
        m2.metric("Change", f"{chg:+.2f}%")
        m3.metric("High", f"${max(prices):.2f}")
        m4.metric("Low", f"${min(prices):.2f}")

        speed_val = SPEEDS[st.session_state.speed]
        # At 200ms interval, 5 frames/sec. Window = last N ticks visible at current speed.
        window = max(60, min(len(prices), int(60 * speed_val * 5)))
        prices_view = prices[-window:]

        fig = px.line(pd.DataFrame({"Price": prices_view}), y="Price")
        fig.update_layout(
            template=None, plot_bgcolor="#0a0c10", paper_bgcolor="#0a0c10",
            font=dict(color="#64748b"), margin=dict(l=50, r=20, t=20, b=40),
            xaxis=dict(title="Seconds elapsed", showgrid=False, tickfont=dict(color="#334155")),
            yaxis=dict(gridcolor="#111318", zeroline=False, tickfont=dict(color="#334155")),
        )
        fig.update_traces(line=dict(color="#3b82f6", width=2), hovertemplate="$%{y:.2f}<extra></extra>")
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown(
            "<div style='font-size:11px;color:#475569;letter-spacing:1px;text-transform:uppercase;margin-bottom:12px;'>Place Order</div>",
            unsafe_allow_html=True)
        shares = st.number_input("Shares", min_value=1, value=1, key="trade_shares")
        cost = p * shares
        st.markdown(f"""
        <div style='background:#111318;border:1px solid #1e2330;border-radius:8px;padding:12px;margin-bottom:12px;'>
            <div style='display:flex;justify-content:space-between;margin-bottom:6px;'>
                <span style='color:#475569;font-size:12px;'>Price per share</span>
                <span style='color:#f1f5f9;font-size:13px;font-weight:500;'>${p:.2f}</span>
            </div>
            <div style='display:flex;justify-content:space-between;margin-bottom:6px;'>
                <span style='color:#475569;font-size:12px;'>Total cost</span>
                <span style='color:#f1f5f9;font-size:13px;font-weight:500;'>${cost:,.2f}</span>
            </div>
            <div style='display:flex;justify-content:space-between;'>
                <span style='color:#475569;font-size:12px;'>Cash available</span>
                <span style='color:#f1f5f9;font-size:13px;font-weight:500;'>${st.session_state.cash:,.2f}</span>
            </div>
        </div>""", unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        b3, b4 = st.columns(2)

        if b1.button("Buy", use_container_width=True, type="primary"):
            buy_stock(sym, shares)

        if b2.button("Sell", use_container_width=True):
            sell_stock(sym, shares)

        if b3.button("Short", use_container_width=True):
            short_stock(sym, shares)

        if b4.button("Cover", use_container_width=True):
            cover_short(sym, shares)

        if st.session_state.trade_history:
            st.divider()
            st.markdown(
                "<div style='font-size:11px;color:#475569;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;'>Recent Orders</div>",
                unsafe_allow_html=True)
            for t in st.session_state.trade_history[:6]:
                color = "#22c55e" if t["action"] == "Buy" else "#ef4444"
                st.markdown(f"""
                <div style='display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #1e2330;'>
                    <span style='color:{color};font-size:12px;font-weight:500;'>{t["action"]} {t["shares"]} {t["sym"]}</span>
                    <span style='color:#475569;font-size:12px;'>${t["price"]:.2f}</span>
                </div>""", unsafe_allow_html=True)
with tabs[2]:
    pv = portfolio_value()
    pnl = pv - 100000
    long_val   = sum(get_price(s) * q for s, q in st.session_state.portfolio.items())
    short_liab = sum(get_price(s) * q for s, q in st.session_state.short_positions.items())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Cash",        f"${st.session_state.cash:,.2f}")
    m2.metric("Long Value",  f"${long_val:,.2f}")
    m3.metric("Short Liab.", f"${short_liab:,.2f}")
    m4.metric("Total P&L",   f"${pnl:+,.2f}")

    # Net worth chart
    if len(st.session_state.net_worth_history) > 1:
        nwh = st.session_state.net_worth_history
        nw_color = "#22c55e" if nwh[-1] >= nwh[0] else "#ef4444"
        fill_color = "rgba(34,197,94,0.06)" if nw_color == "#22c55e" else "rgba(239,68,68,0.06)"
        # Pad y-range by 5% so the line doesn't hug the edges
        y_min = min(nwh)
        y_max = max(nwh)
        y_pad = max((y_max - y_min) * 0.05, 50)
        fig_nw = go.Figure(go.Scatter(
            y=nwh, mode="lines",
            line=dict(color=nw_color, width=2),
            fill="tozeroy",
            fillcolor=fill_color,
            hovertemplate="$%{y:,.0f}<extra></extra>",
        ))
        fig_nw.update_layout(
            height=160, margin=dict(l=70, r=20, t=10, b=10),
            plot_bgcolor="#0a0c10", paper_bgcolor="#0a0c10",
            xaxis=dict(visible=False),
            yaxis=dict(
                range=[y_min - y_pad, y_max + y_pad],
                gridcolor="#111318", zeroline=False,
                tickfont=dict(color="#334155"),
                tickprefix="$", tickformat=",.0f",
            ),
        )
        st.markdown("<div style='font-size:11px;color:#475569;letter-spacing:1px;text-transform:uppercase;margin:16px 0 4px 0;'>Net Worth</div>", unsafe_allow_html=True)
        st.plotly_chart(fig_nw, use_container_width=True, config={"displayModeBar": False}, key="nw_chart")

    st.markdown("<br>", unsafe_allow_html=True)

    if st.session_state.portfolio:
        st.markdown("<div style='font-size:11px;color:#475569;letter-spacing:1px;text-transform:uppercase;margin-bottom:12px;'>Long Holdings</div>", unsafe_allow_html=True)
        grid = st.columns(3)
        for i, (sym, sh) in enumerate(st.session_state.portfolio.items()):
            p     = get_price(sym)
            val   = p * sh
            basis = st.session_state.cost_basis.get(sym, p)
            pos_pnl = (p - basis) * sh
            pos_pct = (p - basis) / basis * 100 if basis else 0
            color   = "#22c55e" if pos_pnl >= 0 else "#ef4444"
            grid[i % 3].markdown(f"""
            <div style='background:#111318;padding:16px;border-radius:12px;margin-bottom:12px;border:1px solid #1e2330;'>
                <div style='display:flex;justify-content:space-between;align-items:center;'>
                    <span style='color:#f1f5f9;font-size:16px;font-weight:600;'>{sym}</span>
                    <span style='color:#475569;font-size:12px;'>{sh} shares</span>
                </div>
                <div style='color:#3b82f6;font-size:20px;font-weight:700;margin-top:8px;'>${val:,.2f}</div>
                <div style='display:flex;justify-content:space-between;margin-top:6px;'>
                    <span style='color:#475569;font-size:12px;'>Avg cost ${basis:.2f}</span>
                    <span style='color:{color};font-size:12px;font-weight:500;'>{pos_pct:+.1f}% (${pos_pnl:+,.2f})</span>
                </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown("<div style='color:#334155;padding:20px 0;'>No long positions.</div>", unsafe_allow_html=True)

    if st.session_state.short_positions:
        st.markdown("<div style='font-size:11px;color:#475569;letter-spacing:1px;text-transform:uppercase;margin:8px 0 12px 0;'>Short Positions</div>", unsafe_allow_html=True)
        grid2 = st.columns(3)
        for i, (sym, sh) in enumerate(st.session_state.short_positions.items()):
            p     = get_price(sym)
            liab  = p * sh
            basis = st.session_state.short_basis.get(sym, p)
            pos_pnl = (basis - p) * sh   # profit when price falls
            pos_pct = (basis - p) / basis * 100 if basis else 0
            color   = "#22c55e" if pos_pnl >= 0 else "#ef4444"
            grid2[i % 3].markdown(f"""
            <div style='background:#111318;padding:16px;border-radius:12px;margin-bottom:12px;border:1px solid #2d1f1f;'>
                <div style='display:flex;justify-content:space-between;align-items:center;'>
                    <span style='color:#f1f5f9;font-size:16px;font-weight:600;'>{sym}</span>
                    <span style='color:#f97316;font-size:12px;'>SHORT {sh} shares</span>
                </div>
                <div style='color:#f97316;font-size:20px;font-weight:700;margin-top:8px;'>-${liab:,.2f}</div>
                <div style='display:flex;justify-content:space-between;margin-top:6px;'>
                    <span style='color:#475569;font-size:12px;'>Shorted @ ${basis:.2f}</span>
                    <span style='color:{color};font-size:12px;font-weight:500;'>{pos_pct:+.1f}% (${pos_pnl:+,.2f})</span>
                </div>
            </div>""", unsafe_allow_html=True)

with tabs[3]:
    if not st.session_state.news:
        st.write("No news yet")
    else:
        for n in st.session_state.news[:30]:
            is_alert   = n.startswith("🔔")
            is_margin  = n.startswith("💀")
            is_breaking = not is_alert and not is_margin and not any(n.startswith(f) for f in FILLER_NEWS)
            bg     = "#1a0a0a" if is_margin else "#111318"
            border = "#ef4444" if is_margin else "#f59e0b" if is_breaking else "#1e2330"
            st.markdown(f"""
            <div style='background:{bg};border:1px solid {border};border-radius:8px;padding:10px;margin-bottom:6px;'>
                {n}
            </div>
            """, unsafe_allow_html=True)

with tabs[5]:
    st.markdown("""
    ## Objective
    Increase your starting balance of **$100,000** by trading stocks.

    ## Basic Controls

    - **Buy**: Purchase shares of a stock
    - **Sell**: Sell shares you own
    - **Short**: Sell borrowed shares expecting the price to drop
    - **Cover**: Buy back shorted shares to close the position

    ## Market Controls

    - Play / Pause: Start or pause time (or press Space)
    - Speed buttons: Control how fast time moves (1x to 60x)
    - **New**: Starts a new game

    ## Tabs

    - **Market**: Sector performance and stock prices
    - **Trade**: Buy, sell, short, and cover stocks
    - **Portfolio**: Holdings with cost basis, P&L per position, net worth chart
    - **News**: Market updates and breaking events
    - **Career**: XP, rank progression, stats, and objectives

    ## Rules

    - You start with **$100,000 cash**
    - Prices change continuously during market hours using GBM simulation
    - **Margin call**: net worth below $10,000 halts trading
    - Short proceeds are added to cash immediately but create a liability
    - Cash must be available to buy or cover
    """)

with tabs[4]:
    RANKS = [
        ("Trainee",          1,  0),
        ("Analyst",          2,  1),
        ("Associate",        3,  2),
        ("Senior Associate", 4,  3),
        ("Vice President",   5,  5),
        ("Director",         6,  7),
        ("Managing Director",7,  9),
        ("Partner",          8, 12),
        ("Market Maker",     9, 15),
        ("Legend",          10, 20),
    ]
    current_rank_name = st.session_state.rank
    current_level     = st.session_state.level
    xp_target         = current_level * 2500
    progress          = min(1.0, st.session_state.xp / xp_target)
    pv_career         = portfolio_value()
    pnl_career        = pv_career - 100000
    total             = st.session_state.total_trades
    win_rate          = (st.session_state.profitable_trades / max(1, st.session_state.profitable_trades + st.session_state.loss_trades)) * 100

    # ── Header ─────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style='background:#111318;border:1px solid #1e2330;border-radius:12px;padding:20px;margin-bottom:20px;'>
        <div style='font-size:11px;color:#475569;text-transform:uppercase;letter-spacing:1px;'>Current Rank</div>
        <div style='font-size:28px;font-weight:700;color:#f8fafc;margin-top:4px;'>{current_rank_name}</div>
        <div style='font-size:13px;color:#94a3b8;margin-top:2px;'>Level {current_level} &nbsp;·&nbsp; {st.session_state.xp:,.0f} / {xp_target:,.0f} XP to next level</div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(progress)

    # ── Key Stats ──────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:11px;color:#475569;letter-spacing:1px;text-transform:uppercase;margin-bottom:12px;'>Performance</div>", unsafe_allow_html=True)
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Net Worth",    f"${pv_career:,.0f}")
    k2.metric("Total P&L",    f"${pnl_career:+,.0f}")
    k3.metric("Peak Worth",   f"${st.session_state.peak_net_worth:,.0f}")
    k4.metric("Total Trades", str(total))
    k5.metric("Win Rate",     f"{win_rate:.0f}%")
    k6.metric("Shorts",       str(st.session_state.short_count))

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:11px;color:#475569;letter-spacing:1px;text-transform:uppercase;margin-bottom:12px;'>Sector P&L</div>", unsafe_allow_html=True)
    sc1, sc2, sc3 = st.columns(3)
    for col, sector in zip([sc1, sc2, sc3], SECTORS):
        rev    = st.session_state.sector_profits[sector]
        trades = st.session_state.sector_trades[sector]
        color  = "#22c55e" if rev >= 0 else "#ef4444"
        col.markdown(f"""
        <div style='background:#111318;border:1px solid #1e2330;border-radius:10px;padding:16px;'>
            <div style='font-size:11px;color:#475569;text-transform:uppercase;'>{sector}</div>
            <div style='font-size:20px;font-weight:700;color:{color};margin-top:6px;'>${rev:+,.0f}</div>
            <div style='font-size:12px;color:#475569;margin-top:4px;'>{trades} sells</div>
        </div>""", unsafe_allow_html=True)

    # ── Rank Progression ──────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:11px;color:#475569;letter-spacing:1px;text-transform:uppercase;margin-bottom:12px;'>Rank Progression</div>", unsafe_allow_html=True)
    rank_cols = st.columns(len(RANKS))
    for col, (rname, rlevel, _) in zip(rank_cols, RANKS):
        is_current = rlevel == current_level
        is_done    = rlevel < current_level
        bg    = "#1e3a5f" if is_current else "#111318"
        border= "#3b82f6" if is_current else "#22c55e" if is_done else "#1e2330"
        text  = "#f8fafc" if is_current else "#22c55e" if is_done else "#475569"
        icon  = "●" if is_current else "✓" if is_done else "○"
        col.markdown(f"""
        <div style='background:{bg};border:1px solid {border};border-radius:8px;padding:8px 4px;text-align:center;'>
            <div style='font-size:16px;color:{text};'>{icon}</div>
            <div style='font-size:9px;color:{text};margin-top:2px;line-height:1.2;'>{rname}</div>
        </div>""", unsafe_allow_html=True)

    # ── Objectives by Tier ────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    TIER_NAMES = {1: "Tier 1 — Getting Started", 2: "Tier 2 — Building a Book",
                  3: "Tier 3 — Serious Trader",  4: "Tier 4 — Market Operator",
                  5: "Tier 5 — Elite"}
    TIER_COLORS = {1: "#3b82f6", 2: "#8b5cf6", 3: "#f59e0b", 4: "#ef4444", 5: "#22c55e"}

    for tier in range(1, 6):
        tier_objs   = [o for o in st.session_state.objectives if o["tier"] == tier]
        done_count  = sum(1 for o in tier_objs if o["done"])
        total_count = len(tier_objs)
        tc          = TIER_COLORS[tier]
        st.markdown(f"""
        <div style='display:flex;justify-content:space-between;align-items:center;margin:16px 0 8px 0;'>
            <span style='font-size:13px;font-weight:600;color:#f8fafc;'>{TIER_NAMES[tier]}</span>
            <span style='font-size:12px;color:{tc};'>{done_count}/{total_count}</span>
        </div>""", unsafe_allow_html=True)
        for obj in tier_objs:
            if obj["done"]:
                st.markdown(f"""
                <div style='background:#111318;border-left:4px solid #22c55e;padding:10px 14px;
                            border-radius:4px;margin-bottom:6px;display:flex;justify-content:space-between;opacity:0.55;'>
                    <span style='font-size:13px;color:#94a3b8;'>✓ {obj["task"]}</span>
                    <span style='color:#22c55e;font-size:12px;'>+{obj["reward"]:,} XP</span>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style='background:#111318;border-left:4px solid {tc};padding:10px 14px;
                            border-radius:4px;margin-bottom:6px;display:flex;justify-content:space-between;'>
                    <span style='font-size:13px;color:#f8fafc;'>{obj["task"]}</span>
                    <span style='color:{tc};font-size:12px;'>+{obj["reward"]:,} XP</span>
                </div>""", unsafe_allow_html=True)
