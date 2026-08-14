import yfinance as yf
import pandas as pd
import json
import argparse
from datetime import datetime, timedelta
import pytz

# 설정
TICKERS = {
    "QLD": "ProShares Ultra QQQ (2x)",
    "SSO": "ProShares Ultra S&P500 (2x)",
    "USD": "ProShares Ultra Semiconductors (2x)"
}

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_stage(price, sma20, sma60, sma120, rsi):
    if price < sma120 and rsi < 35:
        return 4, "4단계 (강력 매수)", "red", "남은 투자금 전액을 5일간 분할 매수하세요."
    elif price < sma120:
        return 3, "3단계 (주황)", "orange", "남은 투자금의 50%를 5일간 분할 매수하세요."
    elif price < sma60:
        return 2, "2단계 (노랑)", "yellow", "남은 투자금의 50%를 2~3일간 분할 매수하세요."
    elif price < sma20:
        return 1, "1단계 (초록)", "green", "투자금액의 5~10% 매수 1회 실시하세요."
    else:
        return 0, "관망 (회색)", "gray", "매수 타이밍이 아닙니다. 관망을 유지하세요."

def collect_data(mode):
    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(kst)
    
    session_name = "아침 장마감 확정" if mode == 'morning' else "밤 장시작 실시간 참고"
    
    results = []
    
    for ticker_symbol, name in TICKERS.items():
        ticker = yf.Ticker(ticker_symbol)
        # 충분한 데이터를 가져와서 이평선 계산 (120일선 필요하므로 최소 150일치)
        df = ticker.history(period="1y")
        
        if df.empty:
            continue
            
        # 실시간 가격 (밤 모드일 경우)
        if mode == 'night':
            # yfinance의 fast_info나 current_price 사용 시도
            current_price = ticker.basic_info.last_price if hasattr(ticker, 'basic_info') else df['Close'].iloc[-1]
        else:
            current_price = df['Close'].iloc[-1]
            
        # 전일 종가 기준 지표 계산
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        df['SMA60'] = df['Close'].rolling(window=60).mean()
        df['SMA120'] = df['Close'].rolling(window=120).mean()
        df['RSI'] = calculate_rsi(df['Close'])
        
        last_row = df.iloc[-1]
        
        # 지표 값
        sma20 = last_row['SMA20']
        sma60 = last_row['SMA60']
        sma120 = last_row['SMA120']
        rsi = last_row['RSI']
        
        # 이격도 (%)
        sma20_diff = ((current_price - sma20) / sma20) * 100
        sma60_diff = ((current_price - sma60) / sma60) * 100
        sma120_diff = ((current_price - sma120) / sma120) * 100
        
        # 전일 대비 등락률
        prev_close = df['Close'].iloc[-2]
        change_rate = ((current_price - prev_close) / prev_close) * 100
        
        # 단계 판정 (아침 모드에서는 확정, 밤 모드에서는 지표 업데이트 시 참고용으로 유지하되 로직은 동일하게 적용)
        # 단, 요구사항에 따라 밤 모드에서는 아침에 확정된 신호를 유지하는 것이 좋지만, 
        # collector.py가 독립적으로 실행될 때 이전 상태를 모른다면 현재 지표로 계산함.
        # 프론트엔드에서 아침에 확정된 상태를 보여주는 것이 핵심.
        stage_code, stage_name, badge_color, action_guide = get_stage(current_price, sma20, sma60, sma120, rsi)
        
        results.append({
            "ticker": ticker_symbol,
            "name": name,
            "current_price": round(current_price, 2),
            "change_rate": round(change_rate, 2),
            "sma20": round(sma20, 2),
            "sma60": round(sma60, 2),
            "sma120": round(sma120, 2),
            "rsi": round(rsi, 2),
            "sma20_diff": round(sma20_diff, 2),
            "sma60_diff": round(sma60_diff, 2),
            "sma120_diff": round(sma120_diff, 2),
            "stage_code": stage_code,
            "stage_name": stage_name,
            "badge_color": badge_color,
            "action_guide": action_guide
        })
        
    data = {
        "last_updated": now_kst.strftime("%Y-%m-%d %H:%M:%S"),
        "session_type": mode,
        "session_name": session_name,
        "stocks": results
    }
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print(f"Successfully updated data.json in {mode} mode.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', type=str, default='morning', choices=['morning', 'night'])
    args = parser.parse_args()
    
    collect_data(args.mode)
