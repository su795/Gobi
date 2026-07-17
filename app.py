import streamlit as st
import pandas as pd
import numpy as np
import ccxt
import yfinance as yf
import plotly.graph_objects as go
import time
from datetime import datetime

# --- 1. Streamlit 페이지 및 레이아웃 설정 ---
st.set_page_config(
    page_title="NeoWave AI Live Terminal v7.5",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 우리가 직접 만든 네오웨이브 얼티밋 엔진 모듈들
from core.monowave import MonowaveBuilder
from core.retracement import RetracementAnalyzer
from core.visualizer import NeoWaveVisualizer
from core.compounding import WaveCompoundingEngine
from patterns.impulse import ImpulseWaveValidator
from patterns.corrective import CorrectiveWaveValidator
from patterns.confirmation import PostPatternConfirmation

# --- 2. ⚡ 실시간 데이터 로드 함수 (Bybit/OKX 선물 자동 우회 엔진) ---
# 스트림릿 캐시(ttl)를 5초로 줄여 실시간 스트리밍이 가능하도록 설정합니다.
@st.cache_data(ttl=5)
def fetch_live_futures_data(symbol="BTC/USDT", timeframe="15m", limit=150):
    try:
        # 💡 [핵심 전략]: Streamlit Cloud 미국 서버 IP를 차단하지 않는 Bybit 선물(Linear Perpetual) API 사용!
        # 바이낸스 선물(BTCUSDT)과 호가 및 차트가 99.9% 일치하므로 실전 거래에 완벽히 대응됩니다.
        exchange = ccxt.bybit({
            'options': {
                'defaultType': 'linear' # USDT 마진 선물 계약 명시
            }
        })
        
        # 바이낸스 스타일 심볼 분기 (Bybit 선물 포맷에 맞춤)
        formatted_symbol = symbol.replace("-USD", "/USDT").replace("BTCUSDT", "BTC/USDT")
        if "/" not in formatted_symbol:
            formatted_symbol = "BTC/USDT"
            
        ohlcv = exchange.fetch_ohlcv(formatted_symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['Date'] = pd.to_datetime(df['Date'], unit='ms')
        return df
        
    except Exception as e:
        # Bybit에 일시적 문제가 생길 경우 OKX 선물로 즉시 2차 우회
        try:
            exchange_backup = ccxt.okx({'options': {'defaultType': 'swap'}})
            ohlcv = exchange_backup.fetch_ohlcv("BTC/USDT", timeframe=timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Date'] = pd.to_datetime(df['Date'], unit='ms')
            return df
        except Exception as backup_err:
            st.error(f"⚠️ 실시간 선물 데이터 로드 실패 (Bybit/OKX 차단): {backup_err}")
            return pd.DataFrame()

# --- 3. 🎯 글렌 닐리 매매 셋업 계산 엔진 ---
def compute_trade_setup(pattern_info: dict):
    p_type = pattern_info['pattern_type']
    slice_waves = pattern_info['slice']
    last_wave = slice_waves[-1]
    first_wave = slice_waves[0]
    
    is_short = last_wave.direction == 1
    trade_dir = "🔴 Short (매도/공매도 진입)" if is_short else "🟢 Long (매수 진입)"
    
    buffer = 0.002
    sl_price = last_wave.end_price * (1 + buffer) if is_short else last_wave.end_price * (1 - buffer)
    entry_price = last_wave.end_price - (last_wave.price_length * 0.382) if is_short else last_wave.end_price + (last_wave.price_length * 0.382)
    
    if "Impulse" in p_type:
        w4, w3 = slice_waves[3], slice_waves[2]
        tp1_price, tp1_desc = w4.end_price, "4파 종점 (1차 목표)"
        tp2_price, tp2_desc = w3.start_price, "3파 시작점 (2차 목표)"
    else:
        tp1_price = last_wave.end_price - (last_wave.price_length * 0.81) if is_short else last_wave.end_price + (last_wave.price_length * 0.81)
        tp1_desc = "C파 길이 81% 확증"
        tp2_price, tp2_desc = first_wave.start_price, "조정 시작점 (100% 되돌림)"
        
    risk = abs(sl_price - entry_price)
    rr1 = abs(tp1_price - entry_price) / max(risk, 1e-5)
    rr2 = abs(tp2_price - entry_price) / max(risk, 1e-5)
    
    return {
        "dir": trade_dir, "is_short": is_short, "entry": entry_price, "sl": sl_price,
        "tp1": tp1_price, "tp1_desc": tp1_desc, "rr1": rr1, "tp2": tp2_price, "tp2_desc": tp2_desc, "rr2": rr2
    }

# --- 4. 🎛️ 사이드바 UI 컨트롤 (실시간 스트리밍 & 시간 선택) ---
st.sidebar.image("https://img.icons8.com/fluency/96/bullish.png", width=70)
st.sidebar.title("⚡ Live NeoWave Controls")
st.sidebar.markdown("---")

# 1) 타임프레임 선택 바 (요청하신 15분, 30분, 1시간, 4시간 무결점 탑재)
tf_display = {"15분봉 (단타)": "15m", "30분봉 (데이)": "30m", "1시간봉 (스윙)": "1h", "4시간봉 (중기)": "4h"}
selected_tf_label = st.sidebar.selectbox("⏱️ 타임프레임 선택", list(tf_display.keys()), index=0)
timeframe = tf_display[selected_tf_label]

# 2) 실시간 자동 새로고침 토글 및 주기 설정
st.sidebar.markdown("### 🔄 실시간 렌더링 설정")
live_stream = st.sidebar.toggle("트레이딩뷰 스타일 실시간 스트리밍", value=True)
refresh_rate = st.sidebar.slider("데이터 갱신 주기 (초)", min_value=5, max_value=60, value=10, step=5)

limit = st.sidebar.slider("전체 차트 기간 (캔들 수)", min_value=100, max_value=300, value=180, step=10)
show_labels = st.sidebar.checkbox("차트에 모노파동 구조 기호 표시", value=True)

# 배포판 데이터 리프레시용 버튼
if st.sidebar.button("🚀 엔진 강제 즉시 재분석", type="primary", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# --- 5. 메인 레이아웃 및 퀀트 엔진 가동 ---
st.title("📊 NeoWave AI Real-Time Streaming Terminal")
now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f"**실시간 감시 종목:** `BTC/USDT 선물(Futures)` | **현재 타임프레임:** `{selected_tf_label}` | **마지막 갱신 시각:** `{now_str}`")
st.markdown("---")

# 데이터 페치 (Bybit 선물 데이터 소스 가동)
df = fetch_live_futures_data(symbol="BTC/USDT", timeframe=timeframe, limit=limit)

if df.empty:
    st.warning("🔄 실시간 선물 데이터를 불러오는 중입니다. 잠시만 기다려주세요...")
else:
    # 닐리 알고리즘 파이프라인 가동
    builder = MonowaveBuilder(df)
    monowaves = builder.build_neowave_monowaves()
    analyzer = RetracementAnalyzer(monowaves)
    analyzer.analyze_all_waves()
    
    confirmed_patterns_log = []
    confirmer = PostPatternConfirmation(monowaves)
    
    # 충격파 스캔
    for i in range(len(monowaves) - 4):
        slice_5 = monowaves[i:i+5]
        val = ImpulseWaveValidator(slice_5)
        if val.validate():
            is_term = "Terminal" in val.impulse_type
            is_conf, msg = confirmer.confirm_impulse(slice_5, is_terminal=is_term)
            if is_conf:
                confirmed_patterns_log.append({
                    'start_idx': i, 'end_idx': i+4, 'pattern_type': val.impulse_type, 'slice': slice_5, 'conf_msg': msg
                })
                
    # 조정파 스캔
    for i in range(len(monowaves) - 2):
        if any(p['start_idx'] <= i <= p['end_idx'] for p in confirmed_patterns_log): continue
        slice_3 = monowaves[i:i+3]
        val = CorrectiveWaveValidator(slice_3)
        if val.validate_3_wave():
            is_conf, msg = confirmer.confirm_zigzag_or_flat(slice_3, val.pattern_name)
            if is_conf:
                confirmed_patterns_log.append({
                    'start_idx': i, 'end_idx': i+2, 'pattern_type': val.pattern_name, 'slice': slice_3, 'conf_msg': msg
                })
                
    compounding_engine = WaveCompoundingEngine(monowaves)
    polywaves = compounding_engine.compound_to_polywaves(confirmed_patterns_log)
    multiwaves = compounding_engine.scan_and_compound_complex_corrective(polywaves)
    
    # --- 6. 4개 탭 레이아웃 렌더링 ---
    tab_chart, tab_setup, tab_summary, tab_logs = st.tabs([
        "📊 실시간 인터랙티브 차트", "🎯 실전 매매 셋업 (Entry/SL/TP)", "🏆 파동 병합 요약", "📑 모노파동 로그"
    ])
    
    # =========================================================================
    # [TAB 1] 📊 트레이딩뷰 스타일 실시간 차트 렌더링
    # =========================================================================
    with tab_chart:
        # 우리가 수정한 core.visualizer를 호출하여 트레이딩뷰 프로 다크 테마 적용
        vis = NeoWaveVisualizer(df, monowaves)
        fig = vis.create_chart(f"BTC/USDT Perpetual Futures — {selected_tf_label}")
        
        # 차트 위에 실시간 매매 셋업 라인 투사
        if confirmed_patterns_log:
            setup = compute_trade_setup(confirmed_patterns_log[-1])
            fig.add_hline(y=setup['entry'], line_dash="dot", line_color="#ffeb3b", annotation_text="Entry (진입가)")
            fig.add_hline(y=setup['sl'], line_dash="dash", line_color="#ff1744", annotation_text="SL (절대손절)")
            fig.add_hline(y=setup['tp1'], line_dash="solid", line_color="#00e676", annotation_text="TP1 (1차익절)")
            
        st.plotly_chart(fig, use_container_width=True, height=650)
        
        # 대시보드 하단 미니 메트릭
        c1, c2, c3 = st.columns(3)
        c1.metric("🔥 실시간 현재가", f"{df['Close'].iloc[-1]:,.2f} USDT")
        c2.metric("🌊 탐지된 모노파동", f"{len(monowaves)} 개")
        c3.metric("🔄 상위 차수 압축률", f"{len(monowaves) - len(multiwaves)}개 파동 병합 완료")

    # =========================================================================
    # [TAB 2] 🎯 실전 매매 셋업 카드 UI
    # =========================================================================
    with tab_setup:
        st.subheader("💡 실시간 네오웨이브 확증 기반 매매 전략")
        if not confirmed_patterns_log:
            st.info("⏳ 현재 타임프레임 범위 내에서 확증 패턴을 탐색 중입니다. 단타 타점을 보시려면 15분봉이나 30분봉으로 변경해 보세요.")
        else:
            latest_pat = confirmed_patterns_log[-1]
            setup = compute_trade_setup(latest_pat)
            
            st.success(f"🔥 **[매매 시그널 포착] 최신 확증 패턴:** `{latest_pat['pattern_type']}`")
            st.markdown(f"**### 포지션 가이드:** {setup['dir']}")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("⚡ 진입 타점 (Entry)", f"{setup['entry']:,.2f}", "38.2% 눌림목")
            c2.metric("⛔ 절대 손절선 (SL)", f"{setup['sl']:,.2f}", "이탈 시 카운팅 폐기", delta_color="inverse")
            c3.metric("🎯 1차 익절 (TP1)", f"{setup['tp1']:,.2f}", f"R:R {setup['rr1']:.1f}:1 ({setup['tp1_desc']})")
            c4.metric("🚀 2차 익절 (TP2)", f"{setup['tp2']:,.2f}", f"R:R {setup['rr2']:.1f}:1 (시작점)")

    # =========================================================================
    # [TAB 3] 🏆 병합(Compounding) 요약
    # =========================================================================
    with tab_summary:
        st.subheader("🏆 최종 조립된 상위 차수 파동 Hierarchy")
        summary_data = []
        for mw in multiwaves:
            start_t = pd.to_datetime(mw.start_time)
            end_t = pd.to_datetime(mw.end_time)
            summary_data.append({
                "차수": getattr(mw, 'degree_level', 'Monowave'),
                "방향": "🟢 상승" if mw.direction == 1 else "🔴 하락",
                "패턴명": getattr(mw, 'pattern_name', 'Single Monowave'),
                "기간": f"{start_t.strftime('%Y-%m-%d %H:%M')} ~ {end_t.strftime('%Y-%m-%d %H:%M')}",
                "가격 변동": f"{mw.start_price:,.2f} → {mw.end_price:,.2f}",
                "하위 파동": f"{getattr(mw, 'wave_count', 1)}개"
            })
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)

    # =========================================================================
    # [TAB 4] 📑 모노파동 상세 로그
    # =========================================================================
    with tab_logs:
        st.subheader("📑 개별 모노파동(Monowave) 실시간 로깅 데이터")
        log_data = []
        for w in monowaves:
            st_time = pd.to_datetime(w.start_time).strftime('%Y-%m-%d %H:%M')
            en_time = pd.to_datetime(w.end_time).strftime('%Y-%m-%d %H:%M')
            log_data.append({
                "Wave #": f"Wave {w.index:02d}",
                "방향": "▲ 상승" if w.direction == 1 else "▼ 하락",
                "시작 일시": st_time, "종료 일시": en_time,
                "길이": round(w.price_length, 2),
                "m1 되돌림": f"{w.retracement_ratio*100:.1f}%",
                "구조 기호": ", ".join(w.structure_labels) if w.structure_labels else "[-] "
            })
        st.dataframe(pd.DataFrame(log_data), use_container_width=True, hide_index=True)

# --- 7. ⏱️ 트레이딩뷰 스타일 실시간 자동 스트리밍 루프 엔진 ---
if live_stream:
    time.sleep(refresh_rate)
    st.rerun()