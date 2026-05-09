import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# ページの設定は一番最初に書く必要があります
st.set_page_config(page_title="ETF監視アプリ", layout="wide")

# ---- パスワード認証機能 ----
def check_password():
    # まだパスワードが入力されていない、または間違っている場合
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.title("🔒 ログイン")
        password = st.text_input("パスワードを入力してください", type="password")
        if password:
            # Streamlitの裏側の設定（Secrets）と照合する
            if password == st.secrets["password"]:
                st.session_state["password_correct"] = True
                st.rerun() # 画面を再読み込みしてメイン画面へ
            else:
                st.error("パスワードが違います")
        return False
    return True

# ---- メインのETF監視アプリ ----
# パスワードが合っている場合のみ、以下のコードが実行されます
if check_password():
    st.title("📈 国内不動産ETF 監視ダッシュボード")

    # 監視対象の10銘柄
    tickers = {
        "2566.T": "One ETF ログ(物流)", "2515.T": "外国REIT", "2845.T": "豪州REIT",
        "1345.T": "隔月分配REIT", "2555.T": "SMTAM(年4回)",
        "1343.T": "NEXT FUNDS REIT", "1476.T": "iシェアーズ", "1597.T": "MAXIS",
        "2556.T": "One ETF", "1488.T": "ダイワREIT"
    }

    def get_data(ticker):
        df = yf.download(ticker, period="1y")
        if df.empty: return None
        
        # ゴールデンクロス用 (5日と25日移動平均)
        df['SMA5'] = df['Close'].rolling(window=5).mean()
        df['SMA25'] = df['Close'].rolling(window=25).mean()
        
        # RSI (14日)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        return df.tail(5)

    st.write("### 現在のアラート状況")

    for ticker, name in tickers.items():
        df = get_data(ticker)
        if df is not None:
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            rsi_alert = "⚠️ 買い時 (RSI30以下)" if latest['RSI'] < 30 else "待機"
            gc_alert = "🔥 GC発生!" if (prev['SMA5'] <= prev['SMA25']) and (latest['SMA5'] > latest['SMA25']) else "待機"
            
            current_month = datetime.now().month
            drop_alert = "待機"
            if ticker == "1345.T" and current_month in [1, 3, 5, 7, 9, 11]:
                drop_alert = "📅 権利落ち警戒月"
            elif ticker == "2555.T" and current_month in [2, 5, 8, 11]:
                drop_alert = "📅 権利落ち警戒月"
                
            with st.expander(f"{ticker[:4]} - {name}"):
                st.write(f"**現在値:** {latest['Close']:.1f} 円")
                st.write(f"**RSI指標:** {rsi_alert} (現在: {latest['RSI']:.1f}%)")
                st.write(f"**トレンド:** {gc_alert}")
                st.write(f"**権利落ち:** {drop_alert}")
