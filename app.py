import streamlit as st
import yfinance as yf
import pandas as pd
import sqlite3
import pandas_ta as ta
import plotly.graph_objs as go
from datetime import datetime, timedelta

# Database functions
def save_to_db(symbol, data):
    conn = sqlite3.connect('stocks.db')
    try:
        data = data.reset_index().rename(columns={
            'Date': 'date',
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
    conn = sqlite3.connect('stocks.db')
    try:
        df = pd.read_sql(
            f"SELECT * FROM stocks WHERE symbol = '{symbol.strip().upper()}'",
            conn,
            parse_dates=['date']
        )
        df = df.set_index('date')
        return df
    finally:
        conn.close()

# UI Configuration
st.set_page_config(layout="wide")
st.title("Stock Pattern Analyzer")

# Data Feed Section
with st.expander("Data Feed Controls"):
    col1, col2 = st.columns(2)
    with col1:
        symbols = st.text_input("Enter Nasdaq symbols (comma-separated)", "AAPL,MSFT")
    with col2:
        if st.button("Feed Data"):
            for symbol in symbols.split(','):
                symbol = symbol.strip()
                data = yf.download(symbol, period="1y")
                save_to_db(symbol, data)
            st.success("Data loaded to database!")
            # Add to your app.py
st.write("Database contents sample:", load_from_db(symbols.split(',')[0].strip()).head())

# Main Display Area
col_main, col_indicators = st.columns([3, 1])

with col_main:
    # Stock Selection & Timeframe
    selected_symbol = st.selectbox("Select Stock", options=symbols.split(','))
    timeframe = st.selectbox("Timeframe", ["1d", "1h", "15m", "1m"], index=1)

    # Load Data
    df = load_from_db(selected_symbol)
    if not df.empty:
        df = df.resample(timeframe).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })

        # Main Price Chart
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Price'
        ))
        fig.update_layout(
            height=600,
            title=f"{selected_symbol} Price Chart",
            xaxis_rangeslider_visible=False
        )
        st.plotly_chart(fig, use_container_width=True)

with col_indicators:
    # Technical Indicators Controls
    st.subheader("Technical Indicators")
    indicators = st.multiselect(
        "Select Indicators",
        ["RSI", "MACD", "SMA 50", "SMA 200", "Volume"],
        default=["RSI", "MACD"]
    )

    # Calculate and Plot Indicators
    if indicators:
        indicator_fig = go.Figure()
        
        if "RSI" in indicators:
            df['RSI'] = ta.rsi(df.close)
            indicator_fig.add_trace(go.Scatter(
                x=df.index, y=df['RSI'],
                name='RSI', line=dict(color='purple')
            ))
            indicator_fig.add_hline(y=30, line_dash="dot", line_color="gray")
            indicator_fig.add_hline(y=70, line_dash="dot", line_color="gray")

        if "MACD" in indicators:
            macd = ta.macd(df.close)
            df = pd.concat([df, macd], axis=1)
            indicator_fig.add_trace(go.Scatter(
                x=df.index, y=df['MACD_12_26_9'],
                name='MACD', line=dict(color='blue')
            ))
            indicator_fig.add_trace(go.Scatter(
                x=df.index, y=df['MACDs_12_26_9'],
                name='Signal', line=dict(color='orange')
            ))

        if "Volume" in indicators:
            indicator_fig.add_trace(go.Bar(
                x=df.index, y=df['volume'],
                name='Volume', marker_color='gray'
            ))

        indicator_fig.update_layout(
            height=400,
            title="Indicators",
            showlegend=True
        )
        st.plotly_chart(indicator_fig, use_container_width=True)