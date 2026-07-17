import numpy as np

class RetracementAnalyzer:
    """
    글렌 닐리의 되돌림 법칙 1~7을 적용하여 
    각 모노파동(m0)에 수학적으로 유효한 구조 기호(Structure Labels)를 부여하는 클래스
    """
    def __init__(self, monowaves):
        self.waves = monowaves
        self.num_waves = len(monowaves)

    def analyze_all_waves(self):
        """전체 파동 리스트를 순회하며 법칙 1~7을 적용합니다."""
        # 닐리 분석은 최소 전후 1~2개의 파동을 비교해야 하므로 안전한 인덱스 범위에서 실행
        for i in range(self.num_waves):
            m0 = self.waves[i]
            
            # 다음 파동(m1)이 없으면 되돌림 비율을 알 수 없으므로 분석 불가
            if i >= self.num_waves - 1:
                continue
                
            m1 = self.waves[i+1]
            ratio = m0.retracement_ratio
            
            # --- 닐리의 피보나치 되돌림 법칙 1 ~ 7 대분류 ---
            if ratio < 0.382:
                self._apply_rule_1(i)
            elif 0.382 <= ratio < 0.618:
                self._apply_rule_2(i)
            elif 0.618 <= ratio < 1.0:
                self._apply_rule_3(i)
            elif 1.0 <= ratio < 1.618:
                # 닐리 원서에서는 100% 정확히 되돌린 경우(Rule 4)와 161.8% 미만(Rule 5)을 분리하거나 병합 처리
                self._apply_rule_4_and_5(i)
            elif 1.618 <= ratio < 2.618:
                self._apply_rule_6(i)
            else: # ratio >= 2.618
                self._apply_rule_7(i)

    def _get_len(self, index):
        """안전하게 파동 길이를 가져오는 헬퍼 함수 (인덱스 벗어나면 0 반환)"""
        if 0 <= index < self.num_waves:
            return self.waves[index].price_length
        return 0.0

    # =========================================================================
    # [법칙 1] m1이 m0의 38.2% 미만 되돌림 (강한 추세 파동 중)
    # =========================================================================
    def _apply_rule_1(self, i):
        m_neg1 = self._get_len(i - 1) # m(-1): 직전 파동
        m0 = self._get_len(i)         # m0: 분석 대상 기준 파동
        m1 = self._get_len(i + 1)     # m1: 직후 파동
        m2 = self._get_len(i + 2)     # m2: 그 다음 파동

        labels = set()
        
        # 조건 (a): m(-1)이 m0보다 짧고, m2가 m1보다 길 때 -> 강력한 충격파동(1파 또는 3파)의 가능성
        if m_neg1 < m0 and m2 > m1:
            labels.add(":5") # 충격파동 기호 부여
            labels.add(":3") # 복합 조정의 일부분일 가능성도 상존
            
        # 조건 (b): m0가 매우 길고(연장 파동), m1과 m2가 짧을 때
        elif m0 > (1.618 * m_neg1) and m0 > (1.618 * m2):
            labels.add(":L5") # 연장된 3파 또는 5파 후 추세 종료 가능성
            labels.add(":5")
            
        else:
            # 기본적으로 되돌림이 38.2% 미만이면 추세성이 강하므로 :5 와 :3 을 기본 부여
            labels.add(":5")
            labels.add(":3")

        self.waves[i].structure_labels = sorted(list(labels))

    # =========================================================================
    # [법칙 2] m1이 m0의 38.2% ~ 61.8% 미만 되돌림
    # =========================================================================
    def _apply_rule_2(self, i):
        m_neg1 = self._get_len(i - 1)
        m0 = self._get_len(i)
        m1 = self._get_len(i + 1)
        m2 = self._get_len(i + 2)
        m3 = self._get_len(i + 3)

        labels = set()

        # 조건: m1이 m0를 61.8% 미만으로 되돌렸는데, m2가 m0의 고/저점을 강하게 돌파하는 경우
        if m2 >= m0:
            labels.add(":5")  # 충격파동 1파 또는 3파
            labels.add(":c3") # 삼각형의 중심 파동 가능성
        
        # 조건: m1이 짧고 m2도 짧아 횡보하는 경우 (복잡한 조정 파동 진행)
        if m2 < m1:
            labels.add(":3")
            if m3 > m2:
                labels.add("x:c3") # X파동 가능성 추가
                
        if not labels:
            labels = {":3", ":5"}

        self.waves[i].structure_labels = sorted(list(labels))

    # =========================================================================
    # [법칙 3] m1이 m0의 61.8% ~ 100% 미만 되돌림 (가장 빈번한 조정 비율)
    # =========================================================================
    def _apply_rule_3(self, i):
        m_neg1 = self._get_len(i - 1)
        m0 = self._get_len(i)
        m1 = self._get_len(i + 1)
        m2 = self._get_len(i + 2)

        labels = set()

        # 조건 (a): m0가 이전 파동(m(-1))보다 길고, 다음 파동(m1, m2)에 의해 빠르게 되돌려질 때
        if m0 > m_neg1 and m2 > m1:
            labels.add(":sL3") # 지그재그나 플랫의 마지막 파동 (C파)
            labels.add(":5")   # 터미널 충격파동(대각삼각형)의 일부 가능성
            
        # 조건 (b): m0가 m(-1)보다 작거나 비슷할 때 (삼각형이나 다이아메트릭 내부 파동)
        elif m0 <= m_neg1:
            labels.add(":c3")  # 중심 조정 파동
            labels.add(":3")
            if m1 > (0.81 * m0):
                labels.add(":L3") # 삼각형의 마지막 E파 가능성

        if not labels:
            labels = {":3", ":c3"}

        self.waves[i].structure_labels = sorted(list(labels))

    # =========================================================================
    # [법칙 4 & 5] m1이 m0의 100% ~ 161.8% 미만 되돌림 (플랫 B파, 불규칙 조정)
    # =========================================================================
    def _apply_rule_4_and_5(self, i):
        m_neg2 = self._get_len(i - 2)
        m_neg1 = self._get_len(i - 1)
        m0 = self._get_len(i)
        m1 = self._get_len(i + 1)
        m2 = self._get_len(i + 2)

        labels = set()

        # m1이 m0를 100% 이상 되돌린다는 것은 m0가 조정 파동의 A파 또는 B파라는 결정적 증거
        # 조건: m0가 m(-1)보다 작고 m1이 m0를 완전히 되돌렸다면 -> 플랫/지그재그의 B파 역할
        if m0 < m_neg1 and m1 >= m0:
            labels.add(":c3") # 플랫 B파
            labels.add(":3")
            
        # 조건: 불규칙 플랫(Irregular Flat) 또는 확장 삼각형의 초입
        if m1 > (1.236 * m0):
            labels.add(":c3")
            labels.add("x:c3") # 확장성 X파동
            
        # m0가 충격파동의 5파(마지막)였고, 이후 강하게 100% 이상 되돌려지는 경우
        if m0 > m_neg1 and m0 > m_neg2 and m1 >= m0:
            labels.add(":L5")  # 충격파동 종료
            labels.add(":sL3") # 조정 패턴 종료
            
        if not labels:
            labels = {":3", ":c3", ":L5"}

        self.waves[i].structure_labels = sorted(list(labels))

    # =========================================================================
    # [법칙 6 & 7] m1이 m0의 161.8% 이상 되돌림 (강한 추세 전환, 마지막 조정파)
    # =========================================================================
    def _apply_rule_6(self, i):
        # 161.8% ~ 261.8% 되돌림: m0는 큰 충격파동 직전의 작은 조정파(2파 또는 4파)이거나 B파
        self.waves[i].structure_labels = [":3", ":c3", ":L3"]

    def _apply_rule_7(self, i):
        # 261.8% 이상 폭발적 되돌림: m0는 추세 전환 직전의 아주 작은 불규칙 조정의 끝
        self.waves[i].structure_labels = [":L3", ":L5", ":sL3"]