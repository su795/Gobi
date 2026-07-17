import streamlit as st
import pandas as pd
import numpy as np
import ccxt
import yfinance as yf
import plotly.graph_objects as go
import time

# --- 1. Streamlit 페이지 및 탭 레이아웃 설정 ---
st.set_page_config(
    page_title="NeoWave AI Master Analyzer v7.0",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# [선택] 300초(5분)마다 웹 페이지만 자동 새로고침하여 최신 캔들 렌더링
if 'last_update' not in st.session_state:
    st.session_state.last_update = time.time()
if time.time() - st.session_state.last_update > 300:
    st.session_state.last_update = time.time()
    st.rerun()

# 우리가 직접 만든 네오웨이브 얼티밋 엔진 모듈들
from core.monowave import MonowaveBuilder
from core.retracement import RetracementAnalyzer
from core.visualizer import NeoWaveVisualizer
from core.compounding import WaveCompoundingEngine
from patterns.impulse import ImpulseWaveValidator
from patterns.corrective import CorrectiveWaveValidator
from patterns.confirmation import PostPatternConfirmation

# --- 2. 데이터 로드 함수 (클라우드 차단 원천 봉쇄) ---
@st.cache_data(ttl=180)
def fetch_live_data(symbol="BTC/USDT", timeframe="4h", limit=150):
    try:
        # 무조건 yfinance를 사용하여 데이터를 가져옵니다 (IP 차단 문제 없음)
        # 바이낸스 심볼 예: "BTC/USDT" -> "BTC-USD"
        yf_symbol = symbol.replace("/", "-").replace("USDT", "USD")
        
        # timeframe 매핑
        interval = "1h" if timeframe in ["1h", "4h"] else "1d"
        
        df = yf.download(yf_symbol, period="3mo", interval=interval, progress=False)
        df = df.reset_index()
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
        
        # 컬럼 이름 맞추기
        if 'Datetime' in df.columns: df.rename(columns={'Datetime': 'Date'}, inplace=True)
        elif 'index' in df.columns: df.rename(columns={'index': 'Date'}, inplace=True)
        
        return df.tail(limit)
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return pd.DataFrame()

# --- 3. 🎯 글렌 닐리 매매 셋업 계산 엔진 (UI 데이터 반환) ---
def compute_trade_setup(pattern_info: dict):
    p_type = pattern_info['pattern_type']
    slice_waves = pattern_info['slice']
    last_wave = slice_waves[-1]
    first_wave = slice_waves[0]
    
    is_short = last_wave.direction == 1
    trade_dir = "🔴 Short (매도/공매도 진입)" if is_short else "🟢 Long (매수 진입)"
    
    # 1. 절대 손절선 (Stop Loss: 극점 + 0.2% 버퍼)
    buffer = 0.002
    sl_price = last_wave.end_price * (1 + buffer) if is_short else last_wave.end_price * (1 - buffer)
    
    # 2. 진입 타점 (Entry: 38.2% 안전 눌림목)
    entry_price = last_wave.end_price - (last_wave.price_length * 0.382) if is_short else last_wave.end_price + (last_wave.price_length * 0.382)
    
    # 3. 목표 익절선 (Take Profit)
    tp1_price, tp2_price = 0.0, 0.0
    tp1_desc, tp2_desc = "", ""
    
    if "Impulse" in p_type:
        w4, w3 = slice_waves[3], slice_waves[2]
        tp1_price, tp1_desc = w4.end_price, "4파 종점 (1차 목표)"
        tp2_price, tp2_desc = w3.start_price, "3파 시작점 (2차 목표)"
        if "Terminal" in p_type:
            tp2_price, tp2_desc = first_wave.start_price, "터미널 100% 되돌림 (1파 시작점)"
    else:
        tp1_price = last_wave.end_price - (last_wave.price_length * 0.81) if is_short else last_wave.end_price + (last_wave.price_length * 0.81)
        tp1_desc = "C파 길이 81% 확증 목표가"
        tp2_price, tp2_desc = first_wave.start_price, "조정 패턴 시작점 (100% 되돌림)"
        
    # 4. 손익비 (Risk-Reward)
    risk = abs(sl_price - entry_price)
    rr1 = abs(tp1_price - entry_price) / max(risk, 1e-5)
    rr2 = abs(tp2_price - entry_price) / max(risk, 1e-5)
    
    return {
        "dir": trade_dir, "is_short": is_short,
        "entry": entry_price, "sl": sl_price,
        "tp1": tp1_price, "tp1_desc": tp1_desc, "rr1": rr1,
        "tp2": tp2_price, "tp2_desc": tp2_desc, "rr2": rr2
    }

# --- 4. 사이드바 UI 컨트롤 ---
st.sidebar.image("https://img.icons8.com/fluency/96/bullish.png", width=70)
st.sidebar.title("📈 NeoWave AI Controls")
st.sidebar.markdown("---")

# asset_type = st.sidebar.radio("자산군 선택", ["암호화폐 (Binance)", "미국/한국 주식 (yfinance)"])
# if asset_type == "암호화폐 (Binance)":
#     symbol = st.sidebar.selectbox("종목 선택", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "BNB/USDT"])
#     timeframe = st.sidebar.selectbox("타임프레임", ["1h", "4h", "1d", "1w"], index=1)
# else:
#     symbol = st.sidebar.selectbox("종목 선택", ["QQQ", "SPY", "NVDA", "TSLA", "AAPL", "005930.KS"])
#     timeframe = st.sidebar.selectbox("타임프레임", ["1h", "1d"], index=1)

asset_type = st.sidebar.radio("자산군 선택", ["금융 데이터 (Yahoo Finance)"])
symbol = st.sidebar.selectbox("종목 선택", ["BTC-USD", "ETH-USD", "QQQ", "SPY", "NVDA", "TSLA"])
timeframe = st.sidebar.selectbox("타임프레임", ["1h", "1d"], index=0)


limit = st.sidebar.slider("캔들 수 (Limit)", min_value=80, max_value=300, value=150, step=10)
show_labels = st.sidebar.checkbox("차트에 모노파동 기호(:3, :5 등) 표시", value=True)
st.sidebar.button("🚀 즉시 재분석 가동", type="primary", use_container_width=True)

# --- 5. 메인 헤더 ---
st.title("🛡️ Glenn Neely's NeoWave Master AI Dashboard")
st.markdown(f"**현재 종목:** `{symbol}` | **타임프레임:** `{timeframe}` | **분석 엔진:** `v7.0 (Trading Setups & Compounding)`")
st.markdown("---")

# --- 6. 파이프라인 가동 ---
df = fetch_live_data(symbol, timeframe, limit)

if df.empty:
    st.warning("불러온 주가 데이터가 없습니다. 사이드바 설정을 확인해 주세요.")
else:
    # 모노파동 작도 및 1~7 법칙 분석
    builder = MonowaveBuilder(df)
    monowaves = builder.build_neowave_monowaves()
    analyzer = RetracementAnalyzer(monowaves)
    analyzer.analyze_all_waves()
    
    # 충격파/조정파 패턴 스캔 및 사후 확증
    confirmed_patterns_log = []
    confirmer = PostPatternConfirmation(monowaves)
    
    for i in range(len(monowaves) - 4):
        slice_5 = monowaves[i:i+5]
        val = ImpulseWaveValidator(slice_5)
        if val.validate():
            is_term = "Terminal" in val.impulse_type
            is_conf, msg = confirmer.confirm_impulse(slice_5, is_terminal=is_term)
            if is_conf:
                confirmed_patterns_log.append({
                    'start_idx': i, 'end_idx': i+4, 'pattern_type': val.impulse_type,
                    'degree': 'Polywave', 'conf_msg': msg, 'slice': slice_5
                })
                
    for i in range(len(monowaves) - 2):
        if any(p['start_idx'] <= i <= p['end_idx'] for p in confirmed_patterns_log): continue
        slice_3 = monowaves[i:i+3]
        val = CorrectiveWaveValidator(slice_3)
        if val.validate_3_wave():
            is_conf, msg = confirmer.confirm_zigzag_or_flat(slice_3, val.pattern_name)
            if is_conf:
                confirmed_patterns_log.append({
                    'start_idx': i, 'end_idx': i+2, 'pattern_type': val.pattern_name,
                    'degree': 'Polywave', 'conf_msg': msg, 'slice': slice_3
                })
                
    # 파동 병합 (Compounding)
    compounding_engine = WaveCompoundingEngine(monowaves)
    polywaves = compounding_engine.compound_to_polywaves(confirmed_patterns_log)
    multiwaves = compounding_engine.scan_and_compound_complex_corrective(polywaves)
    
    # --- 7. 4개 탭 레이아웃 렌더링 ---
    tab_setup, tab_chart, tab_summary, tab_logs = st.tabs([
        "🎯 실전 매매 셋업 (Entry/SL/TP)", "📊 인터랙티브 차트", "🏆 병합(Compounding) 요약", "📑 모노파동 상세 로그"
    ])
    
    # =========================================================================
    # [TAB 1] 🎯 글렌 닐리 실전 매매 셋업 카드 UI
    # =========================================================================
    with tab_setup:
        st.subheader("💡 실시간 네오웨이브 사후 확증(Confirmed) 기반 매매 전략")
        
        if not confirmed_patterns_log:
            st.info("⏳ 현재 화면의 캔들 프레임 내에서 사후 확증(Confirmed)을 완벽히 마친 패턴이 없습니다. 파동이 진행 중이거나, 사이드바에서 타임프레임/캔들 수를 변경해 보세요.")
        else:
            latest_pat = confirmed_patterns_log[-1]
            setup = compute_trade_setup(latest_pat)
            
            # 패턴 포착 배지
            st.success(f"🔥 **[매매 시그널 포착!] 가장 최근 확증 패턴:** `{latest_pat['pattern_type']}`")
            st.markdown(f"**검증 결과:** {latest_pat['conf_msg']}")
            st.markdown("---")
            
            # 포지션 추천 배지
            if setup['is_short']:
                st.markdown(f"### 추천 포지션: :red[{setup['dir']}]")
            else:
                st.markdown(f"### 추천 포지션: :green[{setup['dir']}]")
                
            # 4대 핵심 매매 타점 메트릭 카드 렌더링
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("⚡ 진입 타점 (Entry)", f"{setup['entry']:,.2f}", "38.2% 안전 눌림목", delta_color="off")
            c2.metric("⛔ 절대 손절선 (SL)", f"{setup['sl']:,.2f}", "극점 ±0.2% 이탈 시 폐기", delta_color="inverse")
            c3.metric("🎯 1차 익절 (TP1)", f"{setup['tp1']:,.2f}", f"R:R {setup['rr1']:.1f}:1 ({setup['tp1_desc']})")
            c4.metric("🚀 2차 익절 (TP2)", f"{setup['tp2']:,.2f}", f"R:R {setup['rr2']:.1f}:1 ({setup['tp2_desc']})")
            
            st.markdown("---")
            
            # 손익비(R:R) 평가에 따른 트레이딩 어드바이스 카드
            if setup['rr1'] < 1.5:
                st.warning("⚠️ **[트레이딩 팁]:** 1차 손익비(Risk-Reward)가 1.5:1 미만으로 낮습니다. 현재가 추격 매수를 피하고, 진입 타점을 50%~61.8% 더 깊은 눌림목으로 낮추어 진입하거나 이번 시그널은 패스하는 것을 권장합니다.")
            else:
                st.info("🔥 **[트레이딩 팁]:** 손익비가 매우 우수한 황금 셋업입니다! 1차 목표가(TP1) 도달 시 물량의 50%를 익절하고, 나머지 물량의 손절선(SL)을 본절(Entry Price)로 이동하여 리스크 제로 매매를 완성하세요.")

    # =========================================================================
    # [TAB 2] 📊 Plotly 인터랙티브 차트 렌더링
    # =========================================================================
    with tab_chart:
        vis = NeoWaveVisualizer(df, monowaves)
        vis.create_chart(f"NeoWave Analysis — {symbol} ({timeframe})")
        
        if not show_labels:
            for trace in vis.fig.data:
                if trace.name == 'Monowave (m0)': trace.mode = 'lines'
                    
        for mw in multiwaves:
            if hasattr(mw, 'sub_waves') and len(mw.sub_waves) >= 3:
                start_idx = mw.index
                end_idx = min(start_idx + sum([getattr(sw, 'wave_count', 1) for sw in mw.sub_waves]) - 1, len(monowaves) - 1)
                
                if "Impulse" in mw.pattern_name: color, border = 'rgba(0, 255, 100, 0.15)', '#00ff66'
                elif "Double" in mw.pattern_name or "Complex" in mw.pattern_name: color, border = 'rgba(255, 0, 255, 0.15)', '#ff00ff'
                else: color, border = 'rgba(0, 200, 255, 0.15)', '#00c8ff'
                
                vis.highlight_pattern(start_idx, end_idx, f"<b>{mw.degree_level}:</b><br>{mw.pattern_name}", color=color, border_color=border)
                
        # [신규 추가]: 탭 1에서 도출된 매매 셋업이 있으면 차트 위에도 Entry, SL, TP 수평선을 그려줌!
        if confirmed_patterns_log:
            setup = compute_trade_setup(confirmed_patterns_log[-1])
            vis.fig.add_hline(y=setup['entry'], line_dash="dot", line_color="#00ffff", annotation_text="Entry (진입)")
            vis.fig.add_hline(y=setup['sl'], line_dash="dash", line_color="#ff0000", annotation_text="SL (손절)")
            vis.fig.add_hline(y=setup['tp1'], line_dash="solid", line_color="#00ff00", annotation_text="TP1 (1차 익절)")
            
        st.plotly_chart(vis.fig, use_container_width=True, height=650)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📊 캔들 수", f"{len(df)} 개")
        c2.metric("🌊 1단계 모노파동", f"{len(monowaves)} 개")
        c3.metric("🔄 2단계 폴리파동", f"{len(polywaves)} 개")
        c4.metric("⭐ 3단계 멀티파동", f"{len(multiwaves)} 개", delta=f"{len(monowaves)-len(multiwaves)}개 압축됨")

    # =========================================================================
    # [TAB 3] 🏆 병합(Compounding) 요약
    # =========================================================================
    with tab_summary:
        st.subheader("🏆 최종 조립된 상위 차수 파동 (Multiwave Hierarchy)")
        summary_data = []
        for mw in multiwaves:
            # [안전장치] 어떤 타입이든 datetime으로 변환하여 strftime 오류 원천 차단
            start_t = pd.to_datetime(mw.start_time)
            end_t = pd.to_datetime(mw.end_time)
            
            summary_data.append({
                "차수": getattr(mw, 'degree_level', 'Monowave'),
                "방향": "🟢 상승" if mw.direction == 1 else "🔴 하락",
                "패턴명": getattr(mw, 'pattern_name', 'Single Monowave'),
                "기간": f"{start_t.strftime('%Y-%m-%d')} ~ {end_t.strftime('%Y-%m-%d')}",
                "가격 변동": f"{mw.start_price:,.1f} → {mw.end_price:,.1f}",
                "하위 파동": f"{getattr(mw, 'wave_count', 1)}개"
            })
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)

    # =========================================================================
    # [TAB 4] 📑 모노파동 상세 로그
    # =========================================================================
    with tab_logs:
        st.subheader("📑 개별 모노파동(Monowave) 및 되돌림 비율(Rule 1~7) 로그")
        log_data = []
        for w in monowaves:
            log_data.append({
                "Wave #": f"Wave {w.index:02d}",
                "방향": "▲ 상승" if w.direction == 1 else "▼ 하락",
                "시작 일시": w.start_time.strftime('%Y-%m-%d %H:%M'),
                "종료 일시": w.end_time.strftime('%Y-%m-%d %H:%M'),
                "길이": round(w.price_length, 2),
                "m1 되돌림": f"{w.retracement_ratio*100:.1f}%",
                "구조 기호": ", ".join(w.structure_labels) if w.structure_labels else "[-] "
            })
        st.dataframe(pd.DataFrame(log_data), use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("⚡ Powered by Glenn Neely's NeoWave Algorithmic Engine v7.0 | Designed with Streamlit & Plotly in VS Code")