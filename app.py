import streamlit as st
import pandas as pd
import yfinance as yf
import sqlite3
from datetime import datetime, timedelta

st.set_page_config(page_title="FinPulse MVP", layout="wide")
st.title("📈 FinPulse: Core Market Tracker")

TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", 
    "BHARTIARTL.NS", "SBIN.NS", "LTIM.NS", "ITC.NS", "HINDUNILVR.NS",
    "LT.NS", "BAJFINANCE.NS", "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS", 
    "KOTAKBANK.NS", "TITAN.NS", "AXISBANK.NS", "ADANIENT.NS", "ULTRACEMCO.NS"
]

# 1. DATABASE INITIALIZATION (Fresh v3 Database)
def init_db():
    conn = sqlite3.connect("finpulse_v3.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            ticker TEXT PRIMARY KEY,
            price REAL,
            market_cap REAL,
            pe_ratio REAL,
            eps REAL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# 2. BULLETPROOF SYNC LOGIC
def sync_data():
    conn = sqlite3.connect("finpulse_v3.db")
    cursor = conn.cursor()
    with st.spinner("Syncing with Yahoo Finance ..."):
        for t in TICKERS:
            try:
                # Use safer history call to guarantee price data
                stock = yf.Ticker(t)
                hist = stock.history(period="1d")
                price = float(hist['Close'].iloc[-1]) if not hist.empty else 0.0
                
                # Wrap .info in its own try block since it is strictly rate-limited
                try:
                    info = stock.info
                    mcap = info.get("marketCap", 0.0)
                    pe = info.get("trailingPE", 0.0)
                    eps = info.get("trailingEps", 0.0)
                except:
                    mcap, pe, eps = 0.0, 0.0, 0.0
                
                cursor.execute("INSERT OR REPLACE INTO stocks VALUES (?, ?, ?, ?, ?)", 
                               (t, price, mcap, pe, eps))
            except:
                # Absolute fallback: if everything fails, insert zeroes so UI never breaks
                cursor.execute("INSERT OR REPLACE INTO stocks VALUES (?, ?, ?, ?, ?)", 
                               (t, 0.0, 0.0, 0.0, 0.0))
    conn.commit()
    conn.close()
    st.sidebar.success("Sync Complete!")

if st.sidebar.button("🔄 Sync Live Data"):
    sync_data()

# 3. LOAD DATA
conn = sqlite3.connect("finpulse_v3.db")
df = pd.read_sql_query("SELECT * FROM stocks", conn)
conn.close()

# 4. API ENDPOINTS
st.sidebar.markdown("---")
st.sidebar.header("📡 API Endpoints")
api_choice = st.sidebar.selectbox("Test Endpoint:", ["None", "/stocks", "/stocks/{ticker}", "/market-summary"])

if api_choice == "/stocks":
    st.sidebar.json(df.to_dict(orient="records"))
elif api_choice == "/stocks/{ticker}":
    tick = st.sidebar.selectbox("Select Ticker:", TICKERS)
    filtered = df[df['ticker'] == tick]
    st.sidebar.json(filtered.to_dict(orient="records") if not filtered.empty else {})
elif api_choice == "/market-summary":
    st.sidebar.json({
        "total_companies": len(df),
        "avg_pe": float(df['pe_ratio'].mean()) if not df.empty else 0.0,
        "total_market_cap": float(df['market_cap'].sum()) if not df.empty else 0.0
    })

# 5. USER INTERFACE
selected = st.selectbox("Select Company to Analyze:", TICKERS)

if not df.empty:
    stock_data = df[df['ticker'] == selected]
    
    if not stock_data.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Current Price", f"₹{stock_data['price'].values[0]:,.2f}")
        c2.metric("P/E Ratio", f"{stock_data['pe_ratio'].values[0]:.2f}")
        c3.metric("EPS", f"₹{stock_data['eps'].values[0]:.2f}")
        c4.metric("Market Cap (Cr)", f"₹{stock_data['market_cap'].values[0]/10000000:,.2f}")
        
        st.markdown("---")
        st.subheader(f"Historical 1-Year Chart: {selected}")
        try:
            chart_data = yf.download(selected, start=(datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'), progress=False)
            if not chart_data.empty:
                if isinstance(chart_data.columns, pd.MultiIndex):
                    chart_data.columns = chart_data.columns.get_level_values(0)
                st.line_chart(chart_data['Close'])
            else:
                st.warning("Chart data temporarily unavailable from Yahoo Finance.")
        except:
            st.warning("Chart data temporarily unavailable from Yahoo Finance.")
        
        st.markdown("---")
        st.subheader("Raw Database View")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning(f"Data for {selected} is missing. Please click 'Sync Live Data' again.")
else:
    st.info("👈 Click 'Sync Live Data' in the sidebar to populate the dashboard.")
