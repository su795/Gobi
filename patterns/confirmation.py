import pandas as pd
import numpy as np

class PostPatternConfirmation:
    """
    [글렌 닐리의 패턴 사후 확증 법칙 (Post-Pattern Implications) v6.0]
    - 일반 충격파동: 5파 소요시간 내에 4파 저점 도달
    - 터미널 충격파동: 1~5파 전체 소요시간의 50% 내에 1파 시작점(100%)까지 폭발적 되돌림!
    - 조정파동: 마지막 파동 소요시간 내에 81% 이상 (삼각형은 100%) 되돌림
    """
    def __init__(self, all_waves):
        self.all_waves = all_waves

    def confirm_impulse(self, impulse_slice, is_terminal=False):
        """충격파동 사후 확증 (일반 vs 터미널 분리)"""
        if not impulse_slice or len(impulse_slice) != 5:
            return False, "잘못된 파동 슬라이스입니다."

        w1, w2, w3, w4, w5 = impulse_slice
        end_idx = w5.index
        if end_idx >= len(self.all_waves) - 1:
            return False, "5파 이후의 미래 데이터 부족으로 검증 보류."

        direction = w5.direction
        accumulated_time = pd.Timedelta(0)
        confirmed = False

        # [신규 탑재]: 터미널 충격파동 전용 가혹한 50% 시간 & 100% 되돌림 법칙!
        if is_terminal or "Terminal" in getattr(impulse_slice[0], 'pattern_name', ''):
            total_time = w5.end_time - w1.start_time
            allowable_time = total_time / 2  # 전체 시간의 딱 50% 내에!
            target_price = w1.start_price    # 1파 시작점까지 100% 완벽히 되돌려야 함!
            
            for next_idx in range(end_idx + 1, len(self.all_waves)):
                next_wave = self.all_waves[next_idx]
                accumulated_time += next_wave.time_length
                
                if (direction == 1 and next_wave.end_price <= target_price) or \
   (direction == -1 and next_wave.end_price >= target_price):
                    confirmed = True
                    break
                if accumulated_time > allowable_time:
                    break
                    
            if confirmed and accumulated_time <= allowable_time:
                return True, f"🔥 터미널 확증 성공: 전체 시간의 50%({allowable_time}) 내인 {accumulated_time} 만에 시작점 100% 되돌림 폭발!"
            else:
                return False, f"❌ 터미널 확증 실패: 50% 시간 내 시작점 도달 실패 (가짜 대각삼각형)."

        # 일반 충격파동 확증 법칙 (5파 시간 내 4파 저점)
        else:
            allowable_time = w5.time_length
            target_price = w4.end_price
            
            for next_idx in range(end_idx + 1, len(self.all_waves)):
                next_wave = self.all_waves[next_idx]
                accumulated_time += next_wave.time_length
                
                if (direction == 1 and next_wave.end_price <= target_price) or \
   (direction == -1 and next_wave.end_price >= target_price):
                    confirmed = True
                    break
                if accumulated_time > allowable_time:
                    break
                    
            if confirmed and accumulated_time <= allowable_time:
                return True, f"✅ 충격파 확증 성공: 5파 시간({allowable_time}) 내에 4파 저점 도달 완료!"
            else:
                return False, f"❌ 충격파 확증 실패: 5파 소요시간 내 속도/비율 미달."

    def confirm_zigzag_or_flat(self, corr_slice, pattern_type="Zigzag"):
        if not corr_slice or len(corr_slice) != 3:
            return False, "잘못된 조정파 슬라이스입니다."
        wC = corr_slice[2]
        end_idx = wC.index
        if end_idx >= len(self.all_waves) - 1:
            return False, "미래 데이터 부족으로 검증 보류."

        allowable_time = wC.time_length
        target_price = (wC.end_price - wC.price_length * 0.81) if wC.direction == 1 else (wC.end_price + wC.price_length * 0.81)
        
        accumulated_time = pd.Timedelta(0)
        confirmed = False
        for next_idx in range(end_idx + 1, len(self.all_waves)):
            next_wave = self.all_waves[next_idx]
            accumulated_time += next_wave.time_length
            if (wC.direction == 1 and next_wave.end_price <= target_price) or \
   (wC.direction == -1 and next_wave.end_price >= target_price):
                confirmed = True
                break
            if accumulated_time > allowable_time:
                break

        return (True, f"✅ 조정파 확증 성공: C파 시간 내 81% 이상 되돌림 완료!") if confirmed else (False, "❌ 조정파 확증 실패: 81% 속도 미달.")

    def confirm_triangle_or_complex(self, corr_slice, pattern_type="Triangle"):
        if not corr_slice: return False, "잘못된 파동 슬라이스입니다."
        last_wave = corr_slice[-1]
        end_idx = last_wave.index
        if end_idx >= len(self.all_waves) - 1: return False, "미래 데이터 부족으로 검증 보류."

        allowable_time = last_wave.time_length
        req_ratio = 1.0 if "Triangle" in pattern_type else 0.81
        target_price = (last_wave.end_price - last_wave.price_length * req_ratio) if last_wave.direction == 1 else (last_wave.end_price + last_wave.price_length * req_ratio)

        accumulated_time = pd.Timedelta(0)
        confirmed = False
        for next_idx in range(end_idx + 1, len(self.all_waves)):
            next_wave = self.all_waves[next_idx]
            accumulated_time += next_wave.time_length
            if (last_wave.direction == 1 and next_wave.end_price <= target_price) or \
   (last_wave.direction == -1 and next_wave.end_price >= target_price):
                confirmed = True
                break
            if accumulated_time > allowable_time:
                break

        return (True, f"✅ [{pattern_type}] 확증 성공: 마지막 파동 시간 내 {req_ratio*100:.0f}% 돌파 완료!") if confirmed else (False, f"❌ [{pattern_type}] 확증 실패: 속도 미달.")