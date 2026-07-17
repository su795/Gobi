import numpy as np

class ImpulseWaveValidator:
    """
    글렌 닐리의 네오웨이브 충격파동(Impulse Wave) 엄격 검증 엔진
    - 연장의 법칙 (Rule of Extension)
    - 교대의 법칙 (Rule of Alternation)
    - 가격 중첩 법칙 (Overlap Rule - 터미널 충격파동 구분)
    - 5파 미달 (Truncation) 조건 검증
    """
    def __init__(self, waves_slice):
        # 정확히 5개의 연속된 파동(1, 2, 3, 4, 5파 후보)을 입력받음
        self.waves = waves_slice
        self.is_valid = False
        self.impulse_type = "None"  # "Normal", "Terminal", "Truncated", "None"
        self.extended_wave = 0      # 연장된 파동 번호 (1, 3, 5 중 하나)
        self.reasons = []           # 탈락 또는 통과 사유 기록

    def validate(self):
        if len(self.waves) != 5:
            self.reasons.append("파동 개수가 5개가 아닙니다.")
            return False

        w1, w2, w3, w4, w5 = self.waves
        
        # 0. 방향성 검증 (1, 3, 5파는 같은 방향, 2, 4파는 반대 방향이어야 함)
        if not (w1.direction == w3.direction == w5.direction and w2.direction == w4.direction == -w1.direction):
            self.reasons.append("1,3,5파와 2,4파의 방향이 교대로 진행되지 않았습니다.")
            return False

        # 1. 연장의 법칙 검증 (1, 3, 5파 중 하나는 반드시 가장 길고, 다음 긴 파동의 1.618배 이상이어야 함)
        len_1, len_3, len_5 = w1.price_length, w3.price_length, w5.price_length
        motive_lengths = {1: len_1, 3: len_3, 5: len_5}
        sorted_motive = sorted(motive_lengths.items(), key=lambda item: item[1], reverse=True)
        
        longest_wave_idx, longest_len = sorted_motive[0]
        second_len = sorted_motive[1][1]

        # 3파는 절대 가장 짧을 수 없음 (엘리어트 절대 법칙)
        if len_3 == sorted_motive[2][1]:
            self.reasons.append("3파가 1,3,5파 중 가장 짧으므로 충격파동 탈락.")
            return False

        # 닐리의 엄격한 연장 조건: 가장 긴 파동이 두 번째로 긴 파동보다 최소 1.618배 이상 (또는 최소 1.382배 이상 예외 허용)
        if longest_len < (1.618 * second_len):
            self.reasons.append(f"{longest_wave_idx}파가 가장 길지만, 2위 파동 대비 1.618배 미만으로 연장의 법칙 탈락.")
            return False
        else:
            self.extended_wave = longest_wave_idx

        # 2. 터미널 충격파동(대각삼각형) 여부 및 4파-1파 중첩 검증
        # 1파 고점/저점과 4파 저점/고점이 겹치는지 확인
        overlap = False
        if w1.direction == 1: # 상승 충격파동
            if w4.end_price <= w1.end_price:
                overlap = True
        else: # 하락 충격파동
            if w4.end_price >= w1.end_price:
                overlap = True

        if overlap:
            # 터미널 충격파동은 모든 내부 파동이 :3 (조정 속성) 구조를 가져야 함
            if all(":3" in w.structure_labels or ":c3" in w.structure_labels for w in self.waves):
                self.impulse_type = "Terminal (터미널 충격파동)"
            else:
                self.reasons.append("1파와 4파가 중첩되었으나 내부 파동 기호가 전부 :3이 아니므로 탈락.")
                return False
        else:
            self.impulse_type = "Normal Impulse (일반 충격파동)"

        # 3. 5파 미달 (Truncation) 검증
        if w5.price_length < w4.price_length:
            # 5파 미달은 오직 3파가 아주 강력하게 연장되었을 때만 허용됨
            if self.extended_wave == 3:
                self.impulse_type += " with Truncated 5th (5파 미달)"
            else:
                self.reasons.append("5파가 3파 고점을 넘지 못하는 미달이 발생했으나, 3파 연장이 아니므로 탈락.")
                return False

        # 4. 2파와 4파의 교대의 법칙 (Alternation) 검증
        # 시간, 가격(비율), 되돌림 깊이 중 하나 이상은 반드시 확연히 달라야 함
        time_diff = abs(w2.time_length - w4.time_length) / max(w2.time_length, w4.time_length, pd.Timedelta(seconds=1))
        price_diff = abs(w2.price_length - w4.price_length) / max(w2.price_length, w4.price_length, 1e-5)
        
        if time_diff < 0.3 and price_diff < 0.3:
            self.reasons.append("2파와 4파의 시간 및 가격 비율이 너무 유사하여 교대의 법칙 탈락.")
            return False

        # 모든 검증 통과!
        self.is_valid = True
        self.reasons.append(f"검증 성공! [{self.extended_wave}파 연장] {self.impulse_type}")
        return True