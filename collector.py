import yfinance as yf
import pandas as pd
import json
import argparse
import math
import os
from datetime import datetime
import pytz

# 설정 종목 리스트
TICKERS = {
    "QLD": "ProShares Ultra QQQ (2x)",
    "SSO": "ProShares Ultra S&P500 (2x)",
    "USD": "ProShares Ultra Semiconductors (2x)"
}

def safe_float(val, default=0.0):
    """NaN, None, inf를 방어하여 안전한 float 값 반환"""
    try:
        if val is None or pd.isna(val) or math.isnan(val) or math.isinf(val):
            return default
        return round(float(val), 2)
    except Exception:
        return default

def calculate_rsi(data, window=14):
    """RSI 지표 계산"""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / (loss.replace(0, 0.00001))
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_stage(price, sma20, sma60, sma120, rsi):
    """2X ETF 분할 매수 단계 판정"""
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

def fetch_realtime_price(ticker, fallback_price):
    """
    밤(실시간) 모드 시 현재 거래 중인 미국 본장 실시간 체결가를 다단계로 안전하게 조회
    """
    # 1. fast_info 시도 (최신 yfinance 정식 실시간 API)
    try:
        fast = getattr(ticker, 'fast_info', None)
        if fast is not None:
            price = getattr(fast, 'last_price', None) or getattr(fast, 'lastPrice', None)
            if price is not None and not pd.isna(price) and float(price) > 0:
                return float(price)
    except Exception:
        pass

    # 2. 1일 1분봉 데이터로 실시간 최신 체결가 확인
    try:
        intra_df = ticker.history(period="1d", interval="1m")
        if not intra_df.empty and 'Close' in intra_df.columns:
            valid_closes = intra_df['Close'].dropna()
            if not valid_closes.empty and valid_closes.iloc[-1] > 0:
                return float(valid_closes.iloc[-1])
    except Exception:
        pass

    # 3. info 딕셔너리 시도
    try:
        info = ticker.info
        for key in ['regularMarketPrice', 'currentPrice', 'ask', 'bid']:
            val = info.get(key)
            if val is not None and not pd.isna(val) and float(val) > 0:
                return float(val)
    except Exception:
        pass

    # 4. 조회 실패 시 직전 종가 반환 (시스템 크래시 방지)
    return fallback_price

def determine_mode(user_mode, now_kst):
    """auto 모드일 경우 KST 시간에 맞춰 morning / night 자동 결정"""
    if user_mode in ['morning', 'night']:
        return user_mode
    # 아침 05:00 ~ 14:00 KST는 morning (장 마감 확정치)
    # 그 외 시간 (밤 14:00 ~ 익일 05:00 KST)은 night (실시간 장중 참고)
    hour = now_kst.hour
    if 5 <= hour < 14:
        return 'morning'
    else:
        return 'night'

def collect_data(requested_mode='auto'):
    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(kst)
    
    mode = determine_mode(requested_mode, now_kst)
    session_name = "아침 장마감 확정" if mode == 'morning' else "밤 본장 실시간 시세"
    
    print(f"[{now_kst.strftime('%Y-%m-%d %H:%M:%S')} KST] Collecting data in '{mode}' mode ({session_name})...")
    
    results = []
    
    for ticker_symbol, name in TICKERS.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            # 이평선(120일선) 및 RSI 계산을 위해 1년치 일봉 데이터 조회
            df = ticker.history(period="1y")
            
            if df.empty or len(df) < 30:
                print(f"Warning: Insufficient data for {ticker_symbol}")
                continue

            # 지표 계산을 위한 종가 시리즈
            close_series = df['Close'].dropna()
            if len(close_series) < 30:
                continue

            latest_close = float(close_series.iloc[-1])
            prev_close = float(close_series.iloc[-2]) if len(close_series) >= 2 else latest_close

            # 실시간 밤 모드일 경우 실시간 체결가 조회
            if mode == 'night':
                current_price = fetch_realtime_price(ticker, fallback_price=latest_close)
                # 실시간 가격과 전일 종가(기준가) 비교
                # 만약 당일 캔들이 이미 df에 포함된 경우라면 iloc[-2]가 전일 종가, 아니라면 iloc[-1]이 전일 종가
                base_close = prev_close if len(close_series) >= 2 else latest_close
                change_rate = ((current_price - base_close) / base_close) * 100 if base_close > 0 else 0.0
            else:
                current_price = latest_close
                change_rate = ((latest_close - prev_close) / prev_close) * 100 if prev_close > 0 else 0.0

            # 이평선 및 RSI 계산
            sma20 = float(close_series.rolling(window=20).mean().iloc[-1])
            sma60 = float(close_series.rolling(window=60).mean().iloc[-1])
            sma120 = float(close_series.rolling(window=120).mean().iloc[-1]) if len(close_series) >= 120 else sma60
            
            rsi_series = calculate_rsi(close_series)
            rsi = float(rsi_series.dropna().iloc[-1]) if not rsi_series.dropna().empty else 50.0

            # 이격도 (%)
            sma20_diff = ((current_price - sma20) / sma20) * 100 if sma20 > 0 else 0.0
            sma60_diff = ((current_price - sma60) / sma60) * 100 if sma60 > 0 else 0.0
            sma120_diff = ((current_price - sma120) / sma120) * 100 if sma120 > 0 else 0.0

            # 단계 판정
            stage_code, stage_name, badge_color, action_guide = get_stage(
                current_price, sma20, sma60, sma120, rsi
            )

            # 모든 수치는 safe_float로 NaN/None 원천 차단
            results.append({
                "ticker": ticker_symbol,
                "name": name,
                "current_price": safe_float(current_price),
                "change_rate": safe_float(change_rate),
                "sma20": safe_float(sma20),
                "sma60": safe_float(sma60),
                "sma120": safe_float(sma120),
                "rsi": safe_float(rsi),
                "sma20_diff": safe_float(sma20_diff),
                "sma60_diff": safe_float(sma60_diff),
                "sma120_diff": safe_float(sma120_diff),
                "stage_code": stage_code,
                "stage_name": stage_name,
                "badge_color": badge_color,
                "action_guide": action_guide
            })
            print(f"[{ticker_symbol}] Price: ${safe_float(current_price)} ({safe_float(change_rate):+0.2f}%), Stage: {stage_name}")
            
        except Exception as e:
            print(f"Error processing {ticker_symbol}: {e}")
            continue

    # 데이터 안전성 검증: 수집된 종목이 0개면 기존 data.json을 유지하여 서비스 먹통 방지
    if len(results) == 0:
        print("Warning: No ticker data was collected. Keeping previous data.json to prevent service outage.")
        return

    data = {
        "last_updated": now_kst.strftime("%Y-%m-%d %H:%M:%S"),
        "session_type": mode,
        "session_name": session_name,
        "stocks": results
    }

    # allow_nan=False로 설정하여 혹시 모를 비표준 NaN 유입을 엄격하게 차단
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4, allow_nan=False)

    print(f"Successfully updated data.json with {len(results)} stocks in {mode} mode.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', type=str, default='auto', choices=['auto', 'morning', 'night'])
    args = parser.parse_args()

    collect_data(args.mode)
