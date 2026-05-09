import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="ETF監視アプリ", layout="wide")

# ---- パスワード認証機能 ----
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.title("🔒 ログイン")
        password = st.text_input("パスワードを入力してください", type="password")
        if password:
            if password == st.secrets["password"]:
                st.session_state["password_correct"] = True
                st.rerun() 
            else:
                st.error("パスワードが違います")
        return False
    return True

# ---- データ取得関数（高速化のためキャッシュ化） ----
@st.cache_data(ttl=3600) # 1時間データを保持して読み込みを早くする
def get_data_and_signals(ticker):
    ticker_data = yf.Ticker(ticker)
    df = ticker_data.history(period="1y")
    
    if df.empty: return None
    
    df['SMA5'] = df['Close'].rolling(window=5).mean()
    df['SMA25'] = df['Close'].rolling(window=25).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    rsi_val = float(latest['RSI'])
    sma5_prev = float(prev['SMA5'])
    sma25_prev = float(prev['SMA25'])
    sma5_latest = float(latest['SMA5'])
    sma25_latest = float(latest['SMA25'])
    
    # シグナル判定
    is_rsi_buy = rsi_val < 30
    is_gc_buy = (sma5_prev <= sma25_prev) and (sma5_latest > sma25_latest)
    
    # 優先度づけ（1: RSI買い, 2: GC発生, 3: 待機）
    if is_rsi_buy:
        priority = 1
    elif is_gc_buy:
        priority = 2
    else:
        priority = 3
        
    return {
        "ticker": ticker,
        "close": float(latest['Close']),
        "rsi": rsi_val,
        "is_rsi_buy": is_rsi_buy,
        "is_gc_buy": is_gc_buy,
        "priority": priority
    }


# ---- メインのETF監視アプリ ----
if check_password():
    st.title("📈 国内不動産ETF 買い時ランキング")
    st.write("※RSI30以下、またはゴールデンクロスが発生している銘柄が一番上に表示されます。")

    tickers = {
        "1343.T": "NEXT FUNDS REIT", "1476.T": "iシェアーズ", "1597.T": "MAXIS",
        "2556.T": "One ETF", "1488.T": "ダイワREIT", "2566.T": "One ETF ログ(物流)", 
        "2515.T": "外国REIT", "2845.T": "豪州REIT", "1345.T": "隔月分配REIT", "2555.T": "SMTAM(年4回)"
    }

    # データの収集
    results = []
    with st.spinner("最新の市場データを計算中..."):
        for ticker, name in tickers.items():
            res = get_data_and_signals(ticker)
            if res is not None:
                res["name"] = name
                
                # 権利落ち判定
                current_month = datetime.now().month
                drop_alert = "なし"
                if ticker == "1345.T" and current_month in [1, 3, 5, 7, 9, 11]:
                    drop_alert = "⚠️ 今月は権利落ち月"
                elif ticker == "2555.T" and current_month in [2, 5, 8, 11]:
                    drop_alert = "⚠️ 今月は権利落ち月"
                res["drop_alert"] = drop_alert
                
                results.append(res)

    # 優先度（優先1→2→3）と、RSIの低さ（低いほど買い時）で並べ替え
    results.sort(key=lambda x: (x['priority'], x['rsi']))

    st.markdown("---")

    # 画面への表示（リスト化）
    for res in results:
        code = res['ticker'][:4]
        
        # 優先度1: RSI売られすぎ（最も強い買いサイン）
        if res['priority'] == 1:
            st.error(f"## 🚨 【超・買い時】 {res['name']} ({code})")
            st.write(f"**現在値:** {res['close']:,.1f} 円 ｜ **RSI:** 📉 {res['rsi']:.1f}% (売られすぎ水準)")
            st.write(f"**特記事項:** {res['drop_alert']}")
            
        # 優先度2: ゴールデンクロス（上昇トレンド転換サイン）
        elif res['priority'] == 2:
            st.success(f"## 🔥 【上昇トレンド】 {res['name']} ({code})")
            st.write(f"**現在値:** {res['close']:,.1f} 円 ｜ ゴールデンクロス発生！")
            st.write(f"**特記事項:** {res['drop_alert']}")
            
        # 優先度3: サインなし（待機）
        else:
            with st.expander(f"⏸️ 待機中： {res['name']} ({code}) - RSI: {res['rsi']:.1f}%"):
                st.write(f"**現在値:** {res['close']:,.1f} 円")
                st.write(f"**RSI:** {res['rsi']:.1f}%")
                st.write(f"**特記事項:** {res['drop_alert']}")
