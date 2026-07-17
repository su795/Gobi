import pandas as pd
import numpy as np

class Monowave:
    """단일 모노파동(Monowave)의 정보를 담는 클래스"""
    def __init__(self, index, start_time, end_time, start_price, end_price):
        self.index = index                      
        self.start_time = start_time
        self.end_time = end_time
        self.start_price = start_price
        self.end_price = end_price
        
        self.price_length = abs(end_price - start_price)
        self.time_length = (end_time - start_time)
        self.direction = 1 if end_price > start_price else -1
        
        self.retracement_ratio = 0.0            
        self.structure_labels = []              
        
    def __repr__(self):
        dir_str = "▲" if self.direction == 1 else "▼"
        return (f"[Wave {self.index:02d}] {dir_str} | Length: {self.price_length:.2f} | "
                f"Retracement: {self.retracement_ratio*100:.1f}% | Labels: {self.structure_labels}")


class MonowaveBuilder:
    """OHLC 데이터에서 글렌 닐리의 '중립의 법칙'을 적용해 모노파동을 추출하는 엔진"""
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.monowaves = []

    def build_neowave_monowaves(self):
        """
        [글렌 닐리의 중립의 법칙 (Rule of Neutrality) 탑재]
        단순 종가 연결이 아닌, High/Low 극점을 활용하여 방향 전환을 추적하며
        아웃사이드 바(Outside Bar) 발생 시 이전 추세 방향의 극점을 먼저 반영합니다.
        """
        waves = []
        df = self.df.reset_index(drop=True)
        if len(df) < 2:
            return waves

        # 극점 추적을 위한 초기화
        times = df['Date'].values
        highs = df['High'].values
        lows = df['Low'].values
        
        # 0번 바와 1번 바를 비교하여 초기 추세 설정
        current_dir = 1 if highs[1] > highs[0] else -1
        start_idx = 0
        wave_idx = 0
        
        last_extreme_time = times[0]
        last_extreme_price = lows[0] if current_dir == 1 else highs[0]

        for i in range(1, len(df)):
            # 현재 바가 이전 극점을 경신했는지 확인
            made_new_high = highs[i] > highs[i-1]
            made_new_low = lows[i] < lows[i-1]

            # [중립의 법칙 적용]: 고점과 저점을 동시에 갱신한 아웃사이드 바(Outside Bar) 발생 시
            if made_new_high and made_new_low:
                if current_dir == 1:
                    # 상승 추세 중이었으므로 High를 먼저 방문한 것으로 판정 후 하락 전환!
                    waves.append(Monowave(wave_idx, last_extreme_time, times[i], last_extreme_price, highs[i]))
                    wave_idx += 1
                    last_extreme_time, last_extreme_price = times[i], highs[i]
                    current_dir = -1
                else:
                    # 하락 추세 중이었으므로 Low를 먼저 방문한 것으로 판정 후 상승 전환!
                    waves.append(Monowave(wave_idx, last_extreme_time, times[i], last_extreme_price, lows[i]))
                    wave_idx += 1
                    last_extreme_time, last_extreme_price = times[i], lows[i]
                    current_dir = 1
                continue

            # 일반적인 방향 전환 판별
            if current_dir == 1: # 상승 진행 중
                if highs[i] >= last_extreme_price:
                    last_extreme_time, last_extreme_price = times[i], highs[i]
                elif made_new_low and not made_new_high:
                    # 고점 경신 실패 & 저점 이탈 -> 하락 파동 전환 확정
                    waves.append(Monowave(wave_idx, times[start_idx], last_extreme_time, lows[start_idx], last_extreme_price))
                    wave_idx += 1
                    start_idx = i
                    last_extreme_time, last_extreme_price = times[i], lows[i]
                    current_dir = -1
            else: # 하락 진행 중
                if lows[i] <= last_extreme_price:
                    last_extreme_time, last_extreme_price = times[i], lows[i]
                elif made_new_high and not made_new_low:
                    # 저점 갱신 실패 & 고점 돌파 -> 상승 파동 전환 확정
                    waves.append(Monowave(wave_idx, times[start_idx], last_extreme_time, highs[start_idx], last_extreme_price))
                    wave_idx += 1
                    start_idx = i
                    last_extreme_time, last_extreme_price = times[i], highs[i]
                    current_dir = 1

        # 마지막 파동 처리
        if start_idx < len(df) - 1:
            end_price = highs[-1] if current_dir == 1 else lows[-1]
            waves.append(Monowave(wave_idx, times[start_idx], times[-1], 
                                  lows[start_idx] if current_dir == 1 else highs[start_idx], end_price))

        self.monowaves = waves
        self._calculate_retracements()
        return self.monowaves

    def build_simple_monowaves(self):
        """종가(Close) 기준 단순 모노파동 추출 (호환성 유지용)"""
        waves = []
        prices = self.df['Close'].values
        times = self.df['Date'].values
        if len(prices) < 2: return waves

        current_dir = 1 if prices[1] > prices[0] else -1
        start_idx = 0
        wave_idx = 0

        for i in range(1, len(prices)):
            new_dir = 1 if prices[i] > prices[i-1] else -1
            if new_dir != current_dir and prices[i] != prices[i-1]:
                waves.append(Monowave(wave_idx, times[start_idx], times[i-1], prices[start_idx], prices[i-1]))
                wave_idx += 1
                start_idx = i - 1
                current_dir = new_dir

        if start_idx < len(prices) - 1:
            waves.append(Monowave(wave_idx, times[start_idx], times[-1], prices[start_idx], prices[-1]))

        self.monowaves = waves
        self._calculate_retracements()
        return self.monowaves

    def _calculate_retracements(self):
        for i in range(len(self.monowaves) - 1):
            m0, m1 = self.monowaves[i], self.monowaves[i+1]
            m0.retracement_ratio = (m1.price_length / m0.price_length) if m0.price_length > 0 else 0.0