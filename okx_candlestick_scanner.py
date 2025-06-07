
import streamlit as st
import requests
import pandas as pd
import talib
from datetime import datetime, timedelta
import time

OKX_BASE_URL = "https://www.okx.com"

@st.cache_data
def get_all_symbols():
    response = requests.get(f"{OKX_BASE_URL}/api/v5/public/instruments?instType=SPOT")
    if response.status_code == 200:
        data = response.json()
        return [item['instId'] for item in data['data']]
    return []

@st.cache_data
def get_ohlcv(symbol, timeframe, limit=100):
    response = requests.get(
        f"{OKX_BASE_URL}/api/v5/market/candles?instId={symbol}&bar={timeframe}&limit={limit}"
    )
    if response.status_code == 200:
        raw_data = response.json()['data']
        df = pd.DataFrame(raw_data, columns=[
            'ts', 'open', 'high', 'low', 'close', 'volume'
        ])
        df = df.astype({
            'open': 'float', 'high': 'float', 'low': 'float', 'close': 'float'
        })
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        df = df.sort_values('ts').reset_index(drop=True)
        return df
    return pd.DataFrame()

def detect_patterns(df, pattern_func):
    try:
        result = pattern_func(
            df['open'], df['high'], df['low'], df['close']
        )
        last_index = result[result != 0].index
        if not last_index.empty:
            last_signal_index = last_index[-1]
            candles_ago = len(df) - 1 - last_signal_index
            if candles_ago <= max_signal_age:
                return candles_ago
        return None
    except Exception:
        return None

st.title("📈 OKX Candlestick Pattern Scanner")

with st.sidebar:
    selected_patterns = st.multiselect(
        "Выбери свечные паттерны:",
        options=[p for p in dir(talib) if p.startswith("CDL")],
        default=["CDLENGULFING", "CDLHAMMER", "CDLSHOOTINGSTAR"]
    )
    timeframe = st.selectbox(
        "Таймфрейм:",
        options=["1m", "5m", "15m", "1h", "4h", "1d"],
        index=3
    )
    max_signal_age = st.slider("Макс. возраст сигнала (в свечах):", 0, 10, 2)

st.write(f"🔍 Поиск сигналов на всех монетах OKX за таймфрейм `{timeframe}`...")

symbols = get_all_symbols()
results = []

for symbol in symbols:
    df = get_ohlcv(symbol, timeframe)
    if df.empty or len(df) < 10:
        continue

    for pattern in selected_patterns:
        func = getattr(talib, pattern)
        signal_age = detect_patterns(df, func)
        if signal_age is not None:
            results.append({
                "Symbol": symbol,
                "Pattern": pattern,
                "Candles ago": signal_age
            })

if results:
    st.success(f"✅ Найдено {len(results)} сигналов:")
    st.dataframe(pd.DataFrame(results))
else:
    st.warning("❌ Сигналы не найдены.")
