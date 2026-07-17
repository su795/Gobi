import numpy as np
import pandas as pd  # 💡 [핵심 해결] NameError 방지를 위해 pandas를 명시적으로 임포트!

class ImpulseWaveValidator:
    """
    글렌 닐리의 5파동 충격파(Impulse Wave) 필수 법칙 및 교대의 법칙(Rule of Alternation) 검증기
    """
    def __init__(self, waves: list):
        self.waves = waves
        self.impulse_type = ""
        self.reasons = []

    def validate(self) -> bool:
        if len(self.waves) != 5:
            self.reasons.append("파동의 수가 5개가 아닙니다.")
            return False

        w1, w2, w3, w4, w5 = self.waves

        # --- 1. 방향성 교대 법칙 (1,3,5는 같은 방향 / 2,4는 반대 방향) ---
        if not (w1.direction == w3.direction == w5.direction):
            self.reasons.append("1, 3, 5파의 방향이 일치하지 않습니다.")
            return False
        if not (w2.direction == w4.direction):
            self.reasons.append("2, 4파의 방향이 일치하지 않습니다.")
            return False
        if w1.direction == w2.direction:
            self.reasons.append("충격파와 조정파의 방향이 교대되지 않습니다.")
            return False

        # --- 2. 2파 되돌림 한계 법칙 (1파 시작점을 100% 이상 되돌릴 수 없음) ---
        if w2.price_length >= w1.price_length:
            self.reasons.append("2파가 1파 길이의 100% 이상을 되돌렸습니다.")
            return False

        # --- 3. 3파 길이 절대 법칙 (3파는 절대 가장 짧은 파동일 수 없음) ---
        len1, len3, len5 = w1.price_length, w3.price_length, w5.price_length
        if len3 <= min(len1, len5):
            self.reasons.append("3파가 1, 3, 5파 중 가장 짧은 파동입니다 (엘리어트 절대 법칙 위배).")
            return False

        # --- 4. 4파 되돌림 한계 및 중첩 법칙 ---
        if w4.price_length >= w3.price_length:
            self.reasons.append("4파가 3파 길이의 100% 이상을 되돌렸습니다.")
            return False

        # 터미널 충격파(Terminal Impulse) vs 일반 충격파(Trending Impulse) 구분
        is_overlap = False
        if w1.direction == 1:  # 상승 충격파
            if w4.low_price <= w1.high_price:
                is_overlap = True
        else:                  # 하락 충격파
            if w4.high_price >= w1.low_price:
                is_overlap = True

        if is_overlap:
            self.impulse_type = "Terminal Impulse Wave (엔딩/리딩 다이아고널)"
        else:
            self.impulse_type = "Trending Impulse Wave (일반 추세 충격파)"

        # --- 5. 💡 [오류 해결 부분] 2파와 4파의 교대의 법칙 (시간/가격 길이) ---
        try:
            # 타임델타 연산 오류 방지를 위한 초(Seconds) 단위 변환 안전 로직
            w2_time = w2.time_length.total_seconds() if hasattr(w2.time_length, 'total_seconds') else float(w2.time_length)
            w4_time = w4.time_length.total_seconds() if hasattr(w4.time_length, 'total_seconds') else float(w4.time_length)
            
            time_diff_ratio = abs(w2_time - w4_time) / max(w2_time, w4_time, 1.0)
            price_diff_ratio = abs(w2.price_length - w4.price_length) / max(w2.price_length, w4.price_length, 1e-5)

            # 시간이나 가격 중 하나는 최소 30% 이상 모양이나 크기가 달라야 교대의 법칙 성립
            if time_diff_ratio < 0.2 and price_diff_ratio < 0.2:
                self.reasons.append("2파와 4파 간의 교대의 법칙(시간 및 가격 길이의 차별성)이 부족합니다.")
                return False
        except Exception:
            # 시간 연산에서 예외가 발생하더라도 전체 알고리즘이 멈추지 않고 가격 교대 법칙으로 대체 검증
            if abs(w2.price_length - w4.price_length) / max(w2.price_length, w4.price_length, 1e-5) < 0.2:
                self.reasons.append("2파와 4파 간의 가격 교대의 법칙이 부족합니다.")
                return False

        # --- 6. 연장파(Extension) 판별 ---
        if len3 >= len1 * 1.618 and len3 >= len5 * 1.618:
            self.impulse_type += " (3파 연장)"
        elif len5 >= len1 * 1.618 and len5 >= len3 * 1.618:
            self.impulse_type += " (5파 연장)"
        elif len1 >= len3 * 1.618 and len1 >= len5 * 1.618:
            self.impulse_type += " (1파 연장)"

        return True