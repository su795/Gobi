import pandas as pd
from core.monowave import Monowave

class CompoundWave(Monowave):
    """
    여러 개의 모노파동 또는 하위 파동들을 하나로 병합한 상위 차수 파동 (Polywave, Multiwave 등)
    """
    def __init__(self, degree_level: str, pattern_name: str, sub_waves: list):
        self.degree_level = degree_level      # 차수 이름 ("Polywave", "Multiwave", "Macrowave")
        self.pattern_name = pattern_name      # 내부 패턴 이름 ("Normal Impulse", "Double Zigzag" 등)
        self.sub_waves = sub_waves            # 이 파동을 구성하는 하위 파동 리스트
        
        first_w = sub_waves[0]
        last_w = sub_waves[-1]
        
        super().__init__(
            index=first_w.index,
            start_time=first_w.start_time,
            end_time=last_w.end_time,
            start_price=first_w.start_price,
            end_price=last_w.end_price
        )
        self.wave_count = len(sub_waves)
        
    def __repr__(self):
        dir_str = "▲" if self.direction == 1 else "▼"
        return (f"[{self.degree_level}: {self.pattern_name}] {dir_str} | "
                f"Range: {self.start_time.strftime('%Y-%m-%d')} ~ {self.end_time.strftime('%Y-%m-%d')} | "
                f"Price: {self.start_price:.1f} -> {self.end_price:.1f} (Len: {self.price_length:.1f}) | "
                f"Sub-waves: {self.wave_count}개")


class WaveCompoundingEngine:
    """
    하위 파동 리스트에서 확증된 단순 패턴들을 폴리파동으로 압축하고,
    나아가 X파동으로 연결된 복합 조정 파동(Double Zigzag 등)까지 멀티파동으로 조립하는 빌더 엔진
    """
    def __init__(self, base_waves: list):
        self.base_waves = base_waves
        
    def compound_to_polywaves(self, confirmed_patterns: list):
        """1단계 병합: 확증된 단순 패턴(3파, 5파 등)을 폴리파동으로 압축"""
        polywaves = []
        i = 0
        pattern_map = {p['start_idx']: p for p in confirmed_patterns}
        
        while i < len(self.base_waves):
            if i in pattern_map:
                p_info = pattern_map[i]
                start_idx = p_info['start_idx']
                end_idx = p_info['end_idx']
                slice_waves = self.base_waves[start_idx : end_idx + 1]
                
                poly = CompoundWave(
                    degree_level=p_info.get('degree', 'Polywave'),
                    pattern_name=p_info['pattern_type'],
                    sub_waves=slice_waves
                )
                polywaves.append(poly)
                i = end_idx + 1
            else:
                polywaves.append(self.base_waves[i])
                i += 1
                
        self._recalculate_retracements(polywaves)
        return polywaves

    def scan_and_compound_complex_corrective(self, polywaves: list):
        """
        2단계 병합 (신규 추가!): 폴리파동 리스트를 스캔하여
        [조정파동] + [X파동] + [조정파동] 구조를 찾아내어 복합 조정 파동(Multiwave)으로 압축!
        """
        multiwaves = []
        i = 0
        
        while i < len(polywaves):
            # 최소 3개의 파동(조정파1 + X파동 + 조정파2)이 연속으로 존재해야 복합 조정 검증 가능
            if i <= len(polywaves) - 3:
                w_corr1 = polywaves[i]
                w_x     = polywaves[i+1]
                w_corr2 = polywaves[i+2]
                
                # 1. 첫 번째 파동과 세 번째 파동이 확증된 조정 파동(Zigzag, Flat, Triangle 등)인지 확인
                is_corr1 = isinstance(w_corr1, CompoundWave) and any(c in w_corr1.pattern_name for c in ["Zigzag", "Flat", "Triangle", "Diametric"])
                is_corr2 = isinstance(w_corr2, CompoundWave) and any(c in w_corr2.pattern_name for c in ["Zigzag", "Flat", "Triangle", "Diametric"])
                
                # 2. 중간에 끼어있는 파동(w_x)이 방향이 반대인 연결 파동인지 확인
                dirs_ok = (w_corr1.direction == w_corr2.direction) and (w_x.direction == -w_corr1.direction)
                
                if is_corr1 and is_corr2 and dirs_ok:
                    # 3. 닐리의 X파동 되돌림 법칙 판별 (Small X vs Large X)
                    ret_x = w_x.price_length / max(w_corr1.price_length, 1e-5)
                    
                    complex_name = ""
                    # [작은 X파동 조건]: 되돌림이 61.8% 미만 -> 주로 2중 지그재그(Double Zigzag)
                    if ret_x < 0.618 and "Zigzag" in w_corr1.pattern_name and "Zigzag" in w_corr2.pattern_name:
                        complex_name = f"Double Zigzag (2중 지그재그 w/ Small X: {ret_x*100:.1f}%)"
                    # [큰 X파동 조건]: 되돌림이 61.8% 이상 -> 복합 플랫/혼합 조정(Double Combination)
                    elif ret_x >= 0.618:
                        complex_name = f"Double Combination (복합 조정 w/ Large X: {ret_x*100:.1f}%)"
                    else:
                        complex_name = f"Complex Corrective (복합 조정 w/ X-wave: {ret_x*100:.1f}%)"

                    # 4. 3개의 폴리파동을 단 1개의 멀티파동(Multiwave)으로 병합!
                    complex_wave = CompoundWave(
                        degree_level="Multiwave",
                        pattern_name=complex_name,
                        sub_waves=[w_corr1, w_x, w_corr2]
                    )
                    multiwaves.append(complex_wave)
                    i += 3 # 3개 파동을 하나로 합쳤으므로 인덱스 3칸 점프
                    continue

            # 복합 조정 패턴이 아니면 그대로 유지
            multiwaves.append(polywaves[i])
            i += 1
            
        self._recalculate_retracements(multiwaves)
        return multiwaves

    def _recalculate_retracements(self, waves: list):
        for j in range(len(waves) - 1):
            w0 = waves[j]
            w1 = waves[j+1]
            if w0.price_length > 0:
                w0.retracement_ratio = w1.price_length / w0.price_length
            else:
                w0.retracement_ratio = 0.0