import streamlit as st
import pandas as pd
import yfinance as yf
import sqlite3
from datetime import datetime, timedelta

# 1. INITIAL SETUP & 20 COMPULSORY TICKERS
st.set_page_config(page_title="FinPulse Dashboard", layout="wide")
st.title("📊 FinPulse: Stock Market Monitoring Platform")

TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "BHARTIARTL.NS", "SBIN.NS", "LTIM.NS", "ITC.NS", "HINDUNILVR.NS",
    "LT.NS", "BAJFINANCE.NS", "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS",
    "KOTAKBANK.NS", "TITAN.NS", "AXISBANK.NS", "ADANIENT.NS", "ULTRACEMCO.NS"
]

# 2. DATABASE INITIALIZATION (SQLite)
def init_db():
    conn = sqlite3.connect("finpulse.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            ticker TEXT PRIMARY KEY,
            price REAL,
            market_cap REAL,
            pe_ratio REAL,
            eps REAL,
            last_updated TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# 3. DATA REFRESH FUNCTION (Fetches from yFinance & Stores in Database)
def refresh_market_data():
    conn = sqlite3.connect("finpulse.db")
    cursor = conn.cursor()
    
    with st.spinner("Fetching fresh market data from yFinance..."):
        for ticker in TICKERS:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                price = info.get("currentPrice", info.get("previousClose", 0.0))
                market_cap = info.get("marketCap", 0.0)
                pe_ratio = info.get("trailingPE", 0.0)
                eps = info.get("trailingEps", 0.0)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                cursor.execute("""
                    INSERT OR REPLACE INTO stocks (ticker, price, market_cap, pe_ratio, eps, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (ticker, price, market_cap, pe_ratio, eps, timestamp))
            except Exception as e:
                continue
    conn.commit()
    conn.close()

# Sidebar Control
st.sidebar.header("Data Controls")
if st.sidebar.button("🔄 Sync Database with Live Market"):
    refresh_market_data()
    st.sidebar.success("Database updated successfully!")

# Load Data from Database
def get_stored_data():
    conn = sqlite3.connect("finpulse.db")
    df = pd.read_sql_query("SELECT * FROM stocks", conn)
    conn.close()
    return df

db_data = get_stored_data()

# Auto-populate database if empty on first run
if db_data.empty:
    refresh_market_data()
    db_data = get_stored_data()

# 4. REQUIRED REST API ENDPOINTS COMPONENT (Simulated UI Gateway)
st.sidebar.markdown("---")
st.sidebar.header("📡 Live REST API Endpoints")
api_selection = st.sidebar.selectbox("Test Endpoint JSON Output:", ["Select Endpoint", "/stocks", "/stocks/{ticker}", "/market-summary"])

if api_selection == "/stocks":
    st.sidebar.json(db_data.to_dict(orient="records"))
elif api_selection == "/stocks/{ticker}":
    target_tick = st.sidebar.selectbox("Choose Ticker for API:", TICKERS)
    filtered = db_data[db_data['ticker'] == target_tick]
    st.sidebar.json(filtered.to_dict(orient="records")[0] if not filtered.empty else {})
elif api_selection == "/market-summary":
    summary = {
        "total_tracked_companies": len(db_data),
        "average_pe_ratio": float(db_data['pe_ratio'].mean()) if not db_data.empty else 0,
        "total_market_cap_monitored": float(db_data['market_cap'].sum()) if not db_data.empty else 0,
        "status": "Operational"
    }
    st.sidebar.json(summary)

# 5. DASHBOARD VISUALIZATION
if not db_data.empty:
    # Metric Row
    m1, m2, m3 = st.columns(3)
    m1.metric("Companies Monitored", f"{len(db_data)} / 20")
    m2.metric("Top Valued Ticker", db_data.loc[db_data['market_cap'].idxmax(), 'ticker'] if 'market_cap' in db_data else "N/A")
    m3.metric("Avg P/E Ratio", f"{db_data['pe_ratio'].mean():.2f}")
    
    st.markdown("---")
    
    # Stock Selection for Analysis
    selected_stock = st.selectbox("🎯 Select a Company for Technical & Fundamental Analysis:", TICKERS)
    
    # Layout Split
    left_col, right_col = st.columns([2, 1])
    
    with left_col:
        st.subheader(f"📈 Historical Price Movement: {selected_stock}")
        # Fetching historical chart data dynamically
     hist_df = yf.download(selected_stock, start=(datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'))
if not hist_df.empty:
    # Flatten multi-index columns if they exist so Streamlit can read it
    if isinstance(hist_df.columns, pd.MultiIndex):
        hist_df.columns = hist_df.columns.get_level_values(0)
    st.line_chart(hist_df['Close'])
            
    with right_col:
        st.subheader("📋 Core Fundamentals (Database Records)")
        stock_row = db_data[db_data['ticker'] == selected_stock]
        if not stock_row.empty:
            st.write(f"**Current Price:** ₹{stock_row.iloc[0]['price']:,}")
            st.write(f"**Market Cap:** ₹{stock_row.iloc[0]['market_cap']/10000000:.2f} Cr")
            st.write(f"**P/E Ratio:** {stock_row.iloc[0]['pe_ratio']:.2f}")
            st.write(f"**Earnings Per Share (EPS):** ₹{stock_row.iloc[0]['eps']:.2f}")
            st.caption(f"Last DB Update: {stock_row.iloc[0]['last_updated']}")

    st.markdown("---")
    st.subheader("📊 Cross-Company Peer Comparison")
    st.dataframe(db_data, use_container_width=True)
else:
    st.warning("Please click 'Sync Database with Live Market' in the sidebar to populate data.")
