import streamlit as st
import yfinance as yf
import pandas as pd
import sqlite3
import pandas_ta as ta
import plotly.graph_objs as go
from datetime import datetime, timedelta

# ================== PAGE CONFIG ==================
st.set_page_config(page_title="Stock Analyzer Pro", layout="wide")

# ================== DATABASE FUNCTIONS ==================
def save_to_db(symbol, data):
    """Save intraday stock data to SQLite database"""
    conn = sqlite3.connect('stocks.db')
    try:
        data = data.reset_index().rename(columns={
            'Datetime': 'date',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Adj Close': 'adj_close',
            'Volume': 'volume'
        })
        data = data[['date', 'open', 'high', 'low', 'close', 'adj_close', 'volume']]
        data['symbol'] = symbol.strip().upper()
        data.to_sql('stocks', conn, if_exists='append', index=False)
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")
    finally:
        conn.close()

def load_from_db(symbol):
    """Load intraday stock data from SQLite database"""
    conn = sqlite3.connect('stocks.db')
    try:
        df = pd.read_sql(
            f"SELECT * FROM stocks WHERE symbol = '{symbol.strip().upper()}'",
            conn,
            parse_dates=['date']
        )
        if not df.empty:
            df = df.set_index('date').sort_index()
            df = df[~df.index.duplicated(keep='first')]  # Remove duplicate timestamps
        return df
    except Exception as e:
        return pd.DataFrame()
    finally:
        conn.close()

# ================== UI COMPONENTS ==================
st.title("📈 Intraday Stock Analyzer")

# Data Feed Section
with st.expander("🔌 Intraday Data Feed", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        symbols = st.text_input("Enter symbols (e.g., NVDA,AAPL)", "NVDA")
    with col2:
        days_back = st.number_input("Days to fetch", 1, 7, 1, 
                                   help="YFinance allows max 7 days for 1m data")
    with col3:
        if st.button("⏳ Feed 1-Minute Data"):
            for symbol in symbols.split(','):
                symbol = symbol.strip()
                if symbol:
                    data = yf.download(
                        symbol,
                        period=f"{days_back}d",
                        interval="1m",
                        progress=False
                    )
                    save_to_db(symbol, data)
            st.success(f"Fetched {days_back} day(s) of 1-minute data!")

# Main Display
selected_symbol = st.selectbox("Select Stock", options=[s.strip() for s in symbols.split(',')])
df = load_from_db(selected_symbol)

if not df.empty:
    # Intraday Header
    latest = df.iloc[-1]
    prev_close = df.iloc[-2]['close'] if len(df) > 1 else latest['close']
    price_change = latest['close'] - prev_close
    pct_change = (price_change / prev_close) * 100

    col1, col2, col3 = st.columns(3)
    col1.subheader(f"{selected_symbol}")
    col2.metric("Latest Price", f"{latest['close']:.2f} USD")
    col3.metric("1-Min Change", f"{price_change:.2f}", f"{pct_change:.2f}%")

    # Timeframe Selection
    timeframe_options = ["1D", "5D", "1W", "All"]
    selected_tf = st.session_state.get("selected_tf", "1D")
    
    cols = st.columns(len(timeframe_options))
    for i, tf in enumerate(timeframe_options):
        with cols[i]:
            if st.button(tf, key=f"tf_{tf}", 
                        type="primary" if tf == selected_tf else "secondary"):
                selected_tf = tf
                st.session_state.selected_tf = tf

    # Filter data based on selection
    tf_mapping = {
        "1D": timedelta(days=1),
        "5D": timedelta(days=5),
        "1W": timedelta(weeks=1),
        "All": None
    }
    
    if selected_tf != "All":
        filtered_df = df[df.index >= (datetime.now() - tf_mapping[selected_tf])]
    else:
        filtered_df = df

    # Intraday Chart
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=filtered_df.index,
        open=filtered_df['open'],
        high=filtered_df['high'],
        low=filtered_df['low'],
        close=filtered_df['close'],
        name='Price'
    ))
    fig.update_layout(
        height=500,
        xaxis_rangeslider_visible=False,
        xaxis_title="Time",
        yaxis_title="Price (USD)",
        margin=dict(t=30),
        xaxis=dict(
            type='date',
            tickformat='%H:%M'
        )
    )
    st.plotly_chart(fig, use_container_width=True)

    # Intraday Statistics
    st.subheader("📊 Intraday Metrics")
    
    today = datetime.now().date()
    today_data = df[df.index.date == today]
    
    if not today_data.empty:
        vol_today = today_data['volume'].sum()
        high_today = today_data['high'].max()
        low_today = today_data['low'].min()
        range_today = high_today - low_today
    else:
        vol_today = high_today = low_today = range_today = 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Today's High", f"{high_today:.2f}")
    col2.metric("Today's Low", f"{low_today:.2f}")
    col3.metric("Daily Range", f"{range_today:.2f}")
    col4.metric("Volume Today", f"{vol_today:,}")

else:
    st.warning("No intraday data available. Feed data first!")

# ================== RUN INSTRUCTIONS ==================
# 1. pip install -r requirements.txt
# 2. Create database: python -c "import sqlite3; conn = sqlite3.connect('stocks.db'); conn.close()"
# 3. streamlit run app.py