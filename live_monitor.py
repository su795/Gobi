import time
import datetime
import pandas as pd
import ccxt
import yfinance as yf

# 우리가 구축한 네오웨이브 v6.0 얼티밋 엔진 모듈들
from core.monowave import MonowaveBuilder
from core.retracement import RetracementAnalyzer
from core.compounding import WaveCompoundingEngine
from patterns.impulse import ImpulseWaveValidator
from patterns.corrective import CorrectiveWaveValidator
from patterns.confirmation import PostPatternConfirmation

class LiveNeoWaveMonitor:
    """
    실시간 시장 데이터를 자동으로 불러와 네오웨이브 파이프라인을 24/7 구동하고,
    안전한 진입가(Entry), 손절가(SL), 익절가(TP), 손익비(R:R)를 자동 계산하는 실전 트레이딩 엔진
    """
    def __init__(self, target_assets: list, timeframe: str = "4h", limit: int = 150):
        self.target_assets = target_assets
        self.timeframe = timeframe
        self.limit = limit
        self.binance = ccxt.binance()

    def fetch_live_data(self, symbol: str) -> pd.DataFrame:
        try:
            if "/" in symbol:
                ohlcv = self.binance.fetch_ohlcv(symbol, timeframe=self.timeframe, limit=self.limit)
                df = pd.DataFrame(ohlcv, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
                df['Date'] = pd.to_datetime(df['Date'], unit='ms')
            else:
                yf_interval = "1d" if self.timeframe == "1d" else "1h"
                df = yf.download(symbol, period="3mo", interval=yf_interval, progress=False)
                df = df.reset_index()
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df.rename(columns={'index': 'Date', 'Datetime': 'Date'}, inplace=True)
                df = df.tail(self.limit)
            return df
        except Exception as e:
            print(f" ⚠️ [{symbol}] 데이터 페치 중 오류 발생: {e}")
            return pd.DataFrame()

    # =========================================================================
    # 🎯 [신규 탑재]: 글렌 닐리 매매 공식 기반 진입/손절/익절 타점 자동 계산 엔진
    # =========================================================================
    def calculate_trading_setups(self, symbol: str, pattern_info: dict, monowaves: list):
        p_type = pattern_info['pattern_type']
        slice_waves = pattern_info['slice']
        
        # 마지막 파동(예: 5파 또는 C파) 정보 추출
        last_wave = slice_waves[-1]
        first_wave = slice_waves[0]
        
        # 방향성 판별 (1: 상승 완료 후 하락 반전 노림 -> Short, -1: 하락 완료 후 상승 반전 노림 -> Long)
        trade_dir = "🔴 Short (매도/공매도 진입)" if last_wave.direction == 1 else "🟢 Long (매수 진입)"
        is_short = last_wave.direction == 1
        
        # 1. 절대 손절선 (Stop Loss): 파동의 극점 가격 + 0.2% 버퍼 (휩소 방어 및 닐리 100% 폐기 기준)
        buffer = 0.002
        if is_short:
            sl_price = last_wave.end_price * (1 + buffer)
        else:
            sl_price = last_wave.end_price * (1 - buffer)
            
        # 2. 진입 타점 (Entry): 마지막 파동 길이의 38.2% ~ 50% 되돌림 부근 (안전 진입 타점)
        # 이미 사후 확증이 떴으므로 현재가 또는 조정 눌림목에서 분할 진입
        entry_price = last_wave.end_price - (last_wave.price_length * 0.382) if is_short else last_wave.end_price + (last_wave.price_length * 0.382)
        
        # 3. 목표 익절선 (Take Profit) 계산
        tp1_price, tp2_price = 0.0, 0.0
        tp1_desc, tp2_desc = "", ""
        
        # [A] 충격파동 5파 완료 시: 1차 목표는 4파 저점, 2차 목표는 3파 시작점
        if "Impulse" in p_type:
            w4 = slice_waves[3] # 4번 파동
            tp1_price = w4.end_price # 5파의 시작점(즉, 4파의 종점)
            tp1_desc = "4파 종점 (1차 되돌림 목표)"
            
            w3 = slice_waves[2] # 3번 파동
            tp2_price = w3.start_price # 3파의 시작점
            tp2_desc = "3파 시작점 (2차 강력 되돌림 목표)"
            
            # 터미널 충격파동은 1파 시작점까지 100% 되돌리므로 TP2를 100% 지점으로 업그레이드!
            if "Terminal" in p_type:
                tp2_price = first_wave.start_price
                tp2_desc = "터미널 100% 되돌림 (1파 시작점 극점)"
                
        # [B] 조정파동 (지그재그/플랫) C파 완료 시: 1차는 81% 되돌림, 2차는 A파 시작점(100% 되돌림)
        else:
            tp1_price = last_wave.end_price - (last_wave.price_length * 0.81) if is_short else last_wave.end_price + (last_wave.price_length * 0.81)
            tp1_desc = "C파 길이의 81% 사후 확증 목표가"
            
            tp2_price = first_wave.start_price # A파의 시작점
            tp2_desc = "조정 패턴 시작점 (100% 되돌림)"

        # 4. 손익비 (Risk-Reward Ratio) 계산 -> (목표가 - 진입가) / (손절가 - 진입가)
        risk = abs(sl_price - entry_price)
        reward1 = abs(tp1_price - entry_price)
        reward2 = abs(tp2_price - entry_price)
        
        rr1 = reward1 / max(risk, 1e-5)
        rr2 = reward2 / max(risk, 1e-5)
        
        # --- 계산 결과 예쁘게 출력 ---
        print(f"    🎯 [글렌 닐리 매매 셋업 자동 계산] ──────────────────────────")
        print(f"       • 추천 포지션 : {trade_dir}")
        print(f"       • 진입 타점   : {entry_price:,.2f} USD (마지막 파동 38.2% 안전 눌림목)")
        print(f"       • ⛔ 손절선(SL) : {sl_price:,.2f} USD (패턴 극점 이탈 시 닐리 카운팅 100% 폐기)")
        print(f"       • 🎯 1차 익절(TP1): {tp1_price:,.2f} USD [{tp1_desc}] ── 손익비(R:R) {rr1:.1f}:1")
        print(f"       • 🚀 2차 익절(TP2): {tp2_price:,.2f} USD [{tp2_desc}] ── 손익비(R:R) {rr2:.1f}:1")
        
        if rr1 < 1.5:
            print(f"       ⚠️ [트레이딩 팁]: 1차 손익비가 1.5 미만입니다. 진입가를 더 유리한 눌림목(50%~61.8% 되돌림)으로 낮추거나 패스를 권장합니다.")
        else:
            print(f"       🔥 [트레이딩 팁]: 손익비가 매우 우수한 셋업입니다! 1차 TP 도달 시 절반 익절 후 SL을 본절(Entry)로 이동하세요.")
        print(f"    ─────────────────────────────────────────────────────────────")

    def analyze_asset(self, symbol: str, df: pd.DataFrame):
        if df.empty or len(df) < 20: return

        builder = MonowaveBuilder(df)
        monowaves = builder.build_neowave_monowaves()
        analyzer = RetracementAnalyzer(monowaves)
        analyzer.analyze_all_waves()

        confirmed_patterns_log = []
        confirmer = PostPatternConfirmation(monowaves)

        # 충격파동 스캔
        for i in range(len(monowaves) - 4):
            slice_5 = monowaves[i:i+5]
            val = ImpulseWaveValidator(slice_5)
            if val.validate():
                is_term = "Terminal" in val.impulse_type
                is_conf, msg = confirmer.confirm_impulse(slice_5, is_terminal=is_term)
                if is_conf:
                    confirmed_patterns_log.append({
                        'start_idx': i, 'end_idx': i+4,
                        'pattern_type': val.impulse_type, 'degree': 'Polywave',
                        'conf_msg': msg, 'slice': slice_5
                    })

        # 조정파동 스캔
        for i in range(len(monowaves) - 2):
            if any(p['start_idx'] <= i <= p['end_idx'] for p in confirmed_patterns_log): continue
            slice_3 = monowaves[i:i+3]
            val = CorrectiveWaveValidator(slice_3)
            if val.validate_3_wave():
                is_conf, msg = confirmer.confirm_zigzag_or_flat(slice_3, val.pattern_name)
                if is_conf:
                    confirmed_patterns_log.append({
                        'start_idx': i, 'end_idx': i+2,
                        'pattern_type': val.pattern_name, 'degree': 'Polywave',
                        'conf_msg': msg, 'slice': slice_3
                    })

        compounding_engine = WaveCompoundingEngine(monowaves)
        polywaves = compounding_engine.compound_to_polywaves(confirmed_patterns_log)
        multiwaves = compounding_engine.scan_and_compound_complex_corrective(polywaves)

        current_price = df['Close'].iloc[-1]
        print(f" 🟢 [{symbol}] 현재가: {current_price:,.2f} | 캔들: {len(df)}개 | 모노파동: {len(monowaves)}개")
        
        if confirmed_patterns_log:
            latest_pat = confirmed_patterns_log[-1]
            p_name = latest_pat['pattern_type']
            w_start = monowaves[latest_pat['start_idx']].start_time.strftime('%Y-%m-%d %H:%M')
            w_end   = monowaves[latest_pat['end_idx']].end_time.strftime('%Y-%m-%d %H:%M')
            
            print(f"    └─ 🔥 [매매 시그널 포착!] 가장 최근 확증 패턴: {p_name}")
            print(f"       • 발생 영역 : {w_start} ~ {w_end}")
            print(f"       • 검증 결과 : {latest_pat['conf_msg']}")
            
            # ⭐ [여기서 매매 셋업 및 손익비 자동 계산 엔진 즉시 가동!]
            self.calculate_trading_setups(symbol, latest_pat, monowaves)
        else:
            print(f"    └─ ⏳ 현재 확증(Confirmed)을 완벽히 통과한 패턴은 없습니다. 파동 형성 진행 중...")
        print("-" * 75)

    def run_loop(self, interval_seconds: int = 3600):
        print("====================================================================================")
        print(f" 🚀 [Live NeoWave Monitor v6.5] 실시간 데이터 자동 페치 & 매매 타점/손익비 자동 계산")
        print(f" • 감시 종목 : {self.target_assets}")
        print(f" • 타임프레임 : {self.timeframe} | 갱신 주기: {interval_seconds//60}분마다")
        print("====================================================================================\n")

        while True:
            now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f" ⏰ [스캔 주기 시작] {now_str} — 실시간 데이터 페치 중...")
            
            for symbol in self.target_assets:
                df = self.fetch_live_data(symbol)
                self.analyze_asset(symbol, df)
                time.sleep(1)

            print(f" 💤 [스캔 완료] 다음 데이터 갱신까지 {interval_seconds//60}분 대기합니다...\n")
            time.sleep(interval_seconds)


if __name__ == "__main__":
    WATCH_LIST = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "QQQ"]
    monitor = LiveNeoWaveMonitor(target_assets=WATCH_LIST, timeframe="4h", limit=150)
    monitor.run_loop(interval_seconds=60)