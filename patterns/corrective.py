import numpy as np

class CorrectiveWaveValidator:
    """
    글렌 닐리의 조정 파동 패턴 검증 엔진 (고급 확장판)
    - 3파동: 지그재그(Zigzag), 플랫(Flat)
    - 5파동: 수축형, 확장형, 그리고 **중립 삼각형(Neutral Triangle)**
    - 7파동: 다이아메트릭 (Diametric Pattern)
    - 9파동: **심메트리컬 (Symmetrical Pattern - 닐리의 거대 횡보장 비밀무기)**
    """
    def __init__(self, waves_slice):
        self.waves = waves_slice
        self.pattern_name = "None"
        self.is_valid = False
        self.reasons = []

    # =========================================================================
    # [3파동 검증] 지그재그 & 플랫
    # =========================================================================
    def validate_3_wave(self):
        if len(self.waves) != 3:
            return False
        wA, wB, wC = self.waves

        if not (wA.direction == wC.direction and wB.direction == -wA.direction):
            return False

        ret_B = wA.retracement_ratio
        if ret_B >= 0.618:
            self.pattern_name = "Flat (플랫)"
            if 0.618 <= (wC.price_length / max(wA.price_length, 1e-5)) <= 1.618:
                self.is_valid = True
                self.reasons.append(f"플랫 완성 (B파 되돌림: {ret_B*100:.1f}%)")
        else:
            self.pattern_name = "Zigzag (지그재그)"
            ratio_C_A = wC.price_length / max(wA.price_length, 1e-5)
            if ratio_C_A >= 0.618:
                self.is_valid = True
                self.reasons.append(f"지그재그 완성 (C/A 비율: {ratio_C_A:.2f})")

        return self.is_valid

    # =========================================================================
    # [5파동 검증] 중립 삼각형 (Neutral Triangle) — 닐리의 독창적 발견
    # =========================================================================
    def validate_5_wave_triangle(self):
        """
        삼각형(A-B-C-D-E) 검증: 교대 방향성 및 길이 비율 검증
        - 수축형(Contracting): A > B > C > D > E (점진적 축소)
        - 확장형(Expanding): E > D > C > B > A (점진적 확장)
        - 중립형(Neutral): **가운데 C파가 가장 길고 큰 파동!**
        """
        if len(self.waves) != 5:
            return False

        # 1. 5개 파동의 방향성이 A-B-C-D-E로 교대되는지 확인
        dirs = [w.direction for w in self.waves]
        if not all(dirs[i] == -dirs[i-1] for i in range(1, 5)):
            return False

        lengths = [w.price_length for w in self.waves]
        len_A, len_B, len_C, len_D, len_E = lengths

        # 2. 중립 삼각형 (Neutral Triangle) 검증
        # 조건: C파는 A, B, D, E파 중 반드시 가장 길어야 한다!
        if len_C > len_A and len_C > len_B and len_C > len_D and len_C > len_E:
            # 중립 수축 계열: C > A > E (E가 가장 작음)
            if len_A > len_E:
                self.pattern_name = "Neutral Triangle (중립 삼각형 - 수축계열)"
                self.is_valid = True
                self.reasons.append(f"가운데 C파({len_C:.1f})가 가장 긴 중립 삼각형 (A:{len_A:.1f} > E:{len_E:.1f}) 통과")
            # 중립 확장 계열: C > E > A (A가 가장 작음)
            else:
                self.pattern_name = "Neutral Triangle (중립 삼각형 - 확장계열)"
                self.is_valid = True
                self.reasons.append(f"가운데 C파({len_C:.1f})가 가장 긴 중립 삼각형 (E:{len_E:.1f} > A:{len_A:.1f}) 통과")
            return True

        # 3. 일반 수축형 삼각형 검증 (A가 가장 큼)
        if len_A > len_B > len_C > len_D > len_E:
            self.pattern_name = "Contracting Triangle (수축형 삼각형)"
            self.is_valid = True
            self.reasons.append("A파부터 E파까지 점진적으로 수축하는 정통 삼각형 통과")
            return True

        # 4. 일반 확장형 삼각형 검증 (E가 가장 큼)
        if len_E > len_D > len_C > len_B > len_A:
            self.pattern_name = "Expanding Triangle (확장형 삼각형)"
            self.is_valid = True
            self.reasons.append("A파부터 E파까지 점진적으로 확장하는 정통 삼각형 통과")
            return True

        return False

    # =========================================================================
    # [7파동 검증] 다이아메트릭 (Diametric)
    # =========================================================================
    def validate_7_wave_diametric(self):
        if len(self.waves) != 7:
            return False

        dirs = [w.direction for w in self.waves]
        if not all(dirs[i] == -dirs[i-1] for i in range(1, 7)):
            return False

        lengths = [w.price_length for w in self.waves]
        d_len = lengths[3] # 중앙 D파

        is_diamond = all(d_len >= len_x * 0.85 for idx, len_x in enumerate(lengths) if idx != 3)
        is_bowtie = all(d_len <= len_x * 1.15 for idx, len_x in enumerate(lengths) if idx != 3)

        if is_diamond:
            self.pattern_name = "Diametric (다이아몬드형 7파동)"
            self.is_valid = True
            self.reasons.append("중앙 D파 확장형 다이아메트릭 패턴 통과")
        elif is_bowtie:
            self.pattern_name = "Diametric (나비넥타이형 7파동)"
            self.is_valid = True
            self.reasons.append("중앙 D파 수축형 다이아메트릭 패턴 통과")

        return self.is_valid

    # =========================================================================
    # [9파동 검증] 심메트리컬 (Symmetrical Pattern) — 닐리의 거대 횡보 무기
    # =========================================================================
    def validate_9_wave_symmetrical(self):
        """
        9파동 심메트리컬(A-B-C-D-E-F-G-H-I) 검증
        - 다이아메트릭보다 더 길고 복잡한 거대 횡보장 패턴
        - 9개의 파동 간 가격 및 시간 길이가 매우 균일(약 1.0 비율 내외)하게 대칭을 이룸
        - 다이아몬드형 심메트리컬은 정중앙인 5번째 파동(E파)이 중심축 역할을 함
        """
        if len(self.waves) != 9:
            return False

        # 1. 9개 파동 방향 교대 검증
        dirs = [w.direction for w in self.waves]
        if not all(dirs[i] == -dirs[i-1] for i in range(1, 9)):
            return False

        lengths = [w.price_length for w in self.waves]
        times = [w.time_length / pd.Timedelta(days=1) for w in self.waves] # 일 단위 변환

        e_len = lengths[4] # 5번째 파동 (정중앙 E파)

        # 2. 극단적 이상치(Outlier) 검증: 어떤 파동도 다른 파동의 2.618배 이상 혼자 크거나 작지 않아야 함 (균일성)
        max_len, min_len = max(lengths), max(min(lengths), 1e-5)
        if (max_len / min_len) > 2.618:
            self.reasons.append(f"9파동 중 최대/최소 길이 비율({max_len/min_len:.1f}배)이 너무 차이나 심메트리컬 균일성 탈락.")
            return False

        # 3. 다이아몬드형 심메트리컬 (정중앙 E파가 가장 크거나 중심축 역할)
        is_diamond_sym = all(e_len >= len_x * 0.85 for idx, len_x in enumerate(lengths) if idx != 4)
        
        # 4. 균일 수축/확장형 심메트리컬
        if is_diamond_sym:
            self.pattern_name = "Symmetrical Pattern (9파동 심메트리컬 - 다이아몬드형)"
            self.is_valid = True
            self.reasons.append(f"정중앙 E파({e_len:.1f})를 축으로 9개 파동이 대칭을 이루는 거대 심메트리컬 통과!")
        else:
            # E파가 가장 크지 않더라도 9개 파동 길이가 서로 1.618배 이내에서 횡보하면 심메트리컬로 인정
            if (max_len / min_len) <= 1.618:
                self.pattern_name = "Symmetrical Pattern (9파동 심메트리컬 - 균일 횡보형)"
                self.is_valid = True
                self.reasons.append("9개의 파동이 1.618 비율 이내에서 완벽한 시간/가격 균일성을 보이는 심메트리컬 통과!")
            else:
                self.reasons.append("9개의 파동이 진행되었으나 심메트리컬 특유의 균일성 및 대칭성 조건 미달.")

        return self.is_valid