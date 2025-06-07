import streamlit as st
import pandas as pd
import requests
from candlestick import candlestick
import time
from datetime import datetime

# --- Настройки ---
TIMEFRAMES = ['1m', '5m', '15m', '1H', '4H', '1D']
PATTERN_FUNCTIONS = {
    'hammer': candlestick.hammer,
    'engulfing': candlestick.engulfing,
    'doji': candlestick.doji,
    'shooting_star': candlestick.shooting_star,
    'hanging_man': candlestick.hanging_man,
    'inverted_hammer': candlestick.inverted_hammer,
    'morning_star': candlestick.morning_star,
    'evening_star': candlestick.evening_star
}

# --- Получение данных с OKX ---
@st.cache_data(ttl=3600)
def get_okx_symbols():
    url = "https://www.okx.com/api/v5/public/instruments?instType=SPOT"
    res = requests.get(url)
    data = res.json()['data']
    return [d['instId'] for d in data if d['instId'].endswith('USDT')]

def get_ohlcv(symbol, timeframe, limit=100):
    url = "https://www.okx.com/api/v5/market/candles"
    params = {'instId': symbol, 'bar': timeframe, 'limit': limit}
    res = requests.get(url, params=params)
    if res.status_code != 200 or 'data' not in res.json():
        return None

    raw = res.json()['data']
    df = pd.DataFrame(raw, columns=[
        'ts', 'open', 'high', 'low', 'close', 'volume', 'volCcy', 'volCcyQuote', 'confirm'
    ])
    df = df.iloc[::-1]
    df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].astype(float)
    df['timestamp'] = pd.to_datetime(df['ts'], unit='ms')
    return df

def process_symbol(symbol, timeframe, pattern_list):
    df = get_ohlcv(symbol, timeframe)
    if df is None or df.empty:
        return []

    results = []
    for pattern_name in pattern_list:
        try:
            func = PATTERN_FUNCTIONS[pattern_name]
            df_copy = df.copy()
            func(df_copy)
            col = f'{pattern_name}_bar_num'
            if col in df_copy.columns and not df_copy[col].isna().all():
                if df_copy[col].iloc[-1] == 0:
                    ts = df_copy['timestamp'].iloc[-1]
                    age_min = round((datetime.utcnow() - ts.to_pydatetime()).total_seconds() / 60)
                    results.append({
                        'symbol': symbol,
                        'pattern': pattern_name,
                        'timeframe': timeframe,
                        'timestamp': ts,
                        'age_min': age_min
                    })
        except:
            continue
    return results

# --- Интерфейс Streamlit ---
st.title("📊 OKX Candlestick Scanner")

selected_tf = st.selectbox("Выберите таймфрейм:", TIMEFRAMES)
selected_patterns = st.multiselect(
    "Выберите паттерны:", list(PATTERN_FUNCTIONS.keys()),
    default=["hammer", "engulfing", "doji"]
)

max_age = st.slider("Максимальный возраст сигнала (в минутах):", 0, 240, 30, step=5)

if st.button("🔍 Начать сканирование"):
    with st.spinner("Загружаем данные и ищем сигналы..."):
        symbols = get_okx_symbols()
        results = []
        for i, symbol in enumerate(symbols):
            st.text(f"[{i+1}/{len(symbols)}] {symbol}")
            signals = process_symbol(symbol, selected_tf, selected_patterns)
            results.extend(signals)
            time.sleep(0.15)

    if results:
        df_results = pd.DataFrame(results)
        df_filtered = df_results[df_results["age_min"] <= max_age]
        if df_filtered.empty:
            st.warning(f"❌ Нет сигналов моложе {max_age} мин.")
        else:
            st.success(f"✅ Найдено {len(df_filtered)} сигналов младше {max_age} мин.")
            st.dataframe(df_filtered)
    else:
        st.warning("❌ Паттерны не найдены.")
