import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz
import ta
from ta.trend import SMAIndicator, EMAIndicator

# Fetch stock data
def fetch_stock_data(ticker, period, interval):
    end_date = datetime.now()
    if period == '1wk':
        start_date = end_date - timedelta(days=7)
        data = yf.download(ticker, start=start_date, end=end_date, interval=interval, auto_adjust=False)
    else:
        data = yf.download(ticker, period=period, interval=interval, auto_adjust=False)

    # Flatten columns: use only first level (e.g., 'Close') instead of ('Close', 'ADBE')
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    return data


# Format and localize datetime
def process_data(data):
    if data.index.tzinfo is None:
        data.index = data.index.tz_localize('UTC')
    data.index = data.index.tz_convert('US/Eastern')
    data.reset_index(inplace=True)
    data.rename(columns={'Date': 'Datetime'}, inplace=True)
    return data

# Calculate stock metrics
def calculate_metrics(data):
    last_close = data['Close'].iloc[-1]
    prev_close = data['Close'].iloc[0]
    
    # Ensure scalars
    if isinstance(last_close, pd.Series):
        last_close = last_close.squeeze()
    if isinstance(prev_close, pd.Series):
        prev_close = prev_close.squeeze()

    change = last_close - prev_close
    pct_change = (change / prev_close) * 100

    high = data['High'].max()
    if isinstance(high, pd.Series):
        high = high.squeeze()

    low = data['Low'].min()
    if isinstance(low, pd.Series):
        low = low.squeeze()

    volume = data['Volume'].sum()
    if isinstance(volume, pd.Series):
        volume = volume.squeeze()

    return float(last_close), float(change), float(pct_change), float(high), float(low), float(volume)



# Add SMA and EMA
def add_technical_indicators(data):
    # Make sure 'Close' is a flat 1D Series
    close_series = data['Close']
    
    # If it's 2D, flatten it
    if isinstance(close_series, pd.DataFrame):
        close_series = close_series.squeeze()  # Converts (390,1) -> (390,)
    elif hasattr(close_series, 'values') and close_series.values.ndim > 1:
        close_series = pd.Series(close_series.values.ravel(), index=data.index)

    data['SMA_20'] = SMAIndicator(close=close_series, window=20).sma_indicator()
    data['EMA_20'] = EMAIndicator(close=close_series, window=20).ema_indicator()
    return data

# Set up Streamlit app
st.set_page_config(layout="wide")
st.title('Real Time Stock Dashboard')

# Sidebar inputs
st.sidebar.header('Chart Parameters')
ticker = st.sidebar.text_input('Ticker', 'ADBE')
time_period = st.sidebar.selectbox('Time Period', ['1d', '1wk', '1mo', '1y', 'max'])
chart_type = st.sidebar.selectbox('Chart Type', ['Candlestick', 'Line'])
indicators = st.sidebar.multiselect('Technical Indicators', ['SMA 20', 'EMA 20'])

interval_mapping = {
    '1d': '1m',
    '1wk': '30m',
    '1mo': '1d',
    '1y': '1wk',
    'max': '1wk'
}

# Main chart and metrics
if st.sidebar.button('Update'):
    data = fetch_stock_data(ticker, time_period, interval_mapping[time_period])
    data = process_data(data)
    data = add_technical_indicators(data)

    last_close, change, pct_change, high, low, volume = calculate_metrics(data)

    st.metric(label=f"{ticker} Last Price", value=f"{last_close:.2f} USD", delta=f"{change:.2f} ({pct_change:.2f}%)")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("High", f"{high:.2f} USD")
    col2.metric("Low", f"{low:.2f} USD")
    col3.metric("Volume", f"{volume:,}")

    # Create chart
    if chart_type == 'Candlestick':
        fig = go.Figure(data=[go.Candlestick(
            x=data['Datetime'],
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close']
        )])
    else:
        fig = px.line(data, x='Datetime', y='Close')

    # Add selected indicators
    for indicator in indicators:
        if indicator == 'SMA 20':
            fig.add_trace(go.Scatter(x=data['Datetime'], y=data['SMA_20'], name='SMA 20'))
        elif indicator == 'EMA 20':
            fig.add_trace(go.Scatter(x=data['Datetime'], y=data['EMA_20'], name='EMA 20'))

    fig.update_layout(
        title=f'{ticker} {time_period.upper()} Chart',
        xaxis_title='Time',
        yaxis_title='Price (USD)',
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)

    # Show data tables
    st.subheader('Historical Data')
    st.dataframe(data[['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']])

    st.subheader('Technical Indicators')
    st.dataframe(data[['Datetime', 'SMA_20', 'EMA_20']])

# Sidebar stock tickers
st.sidebar.header('Real-Time Stock Prices')
stock_symbols = ['AAPL', 'GOOGL', 'AMZN', 'MSFT']

for symbol in stock_symbols:
    real_time_data = fetch_stock_data(symbol, '1d', '1m')
    if not real_time_data.empty:
        real_time_data = process_data(real_time_data)
        try:
            last_price = real_time_data['Close'].iloc[-1]
            open_price = real_time_data['Open'].iloc[0]

            # Try to convert to scalar if not already
            if isinstance(last_price, pd.Series):
                last_price = last_price.squeeze()
            if isinstance(open_price, pd.Series):
                open_price = open_price.squeeze()

            # Final check: ensure they are float
            last_price = float(last_price)
            open_price = float(open_price)

            change = last_price - open_price
            pct_change = (change / open_price) * 100

            st.sidebar.metric(f"{symbol}", f"{last_price:.2f} USD", f"{change:.2f} ({pct_change:.2f}%)")

        except Exception as e:
            st.sidebar.write(f"Error processing {symbol}: {e}")



# Sidebar info
st.sidebar.subheader('About')
st.sidebar.info('This dashboard provides stock data and technical indicators. Use the sidebar to customize.')
