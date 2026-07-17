import pandas as pd
from core.monowave import MonowaveBuilder
from core.retracement import RetracementAnalyzer
from core.visualizer import NeoWaveVisualizer
from core.compounding import WaveCompoundingEngine
from patterns.impulse import ImpulseWaveValidator
from patterns.corrective import CorrectiveWaveValidator
from patterns.confirmation import PostPatternConfirmation

def run_ultimate_neowave_pipeline():
    print("=========================================================================")
    print(" 🌟 Glenn Neely's NeoWave Master AI Engine v6.0 (Ultimate Edition)")
    print("=========================================================================\n")

    # 1. 시뮬레이션 데이터: 
    # - [Wave 0~4]: 3파 연장 충격파동 (시간/가격 교대 및 1-5파 균등성 테스트)
    # - [Wave 5]: 5파 소요시간 내에 4파 저점 이탈 (사후 확증)
    # - [Wave 6~8]: 플랫 3-3-5 검증
    dates = pd.date_range(start='2026-01-01', periods=13, freq='D')
    df = pd.DataFrame({
        'Date': dates,
        'Open':  [100, 112, 107, 138, 122, 158, 120, 138, 112, 133, 118, 148, 138],
        'High':  [115, 118, 110, 145, 128, 165, 130, 148, 118, 138, 125, 155, 145],
        'Low':   [ 95, 105, 100, 130, 115, 150, 110, 128, 105, 125, 110, 138, 130],
        'Close': [110, 105, 140, 120, 160, 115, 145, 110, 130, 115, 150, 140, 135]
    })

    # 2. Phase 1: [중립의 법칙 탑재] 모노파동 추출
    print(" 📏 [Phase 1] 중립의 법칙(Rule of Neutrality) 적용 모노파동 작도 중...")
    builder = MonowaveBuilder(df)
    monowaves = builder.build_neowave_monowaves() # 고가/저가 아웃사이드 바 극점 판별
    
    analyzer = RetracementAnalyzer(monowaves)
    analyzer.analyze_all_waves()
    print(f"    └─ 완료: 총 {len(monowaves)}개의 정밀 모노파동 추출 및 법칙 1~7 기호 부여 완료.\n")
    print("-" * 70)

    # 3. Phase 3 & 4: 패턴 스캔 & 사후 확증 (균등성, 시간 교대, 터미널 50% 필터 가동)
    confirmed_patterns_log = []
    confirmer = PostPatternConfirmation(monowaves)

    # --- 충격 파동 스캔 ---
    for i in range(len(monowaves) - 4):
        slice_5 = monowaves[i:i+5]
        val = ImpulseWaveValidator(slice_5)
        if val.validate():
            is_term = "Terminal" in val.impulse_type
            is_conf, msg = confirmer.confirm_impulse(slice_5, is_terminal=is_term)
            print(f" 🟢 [충격파동 탐지] Wave {i} ~ Wave {i+4} ({val.impulse_type})")
            for r in val.reasons: print(f"    ├─ {r}")
            print(f"    └─ 🔍 확증 검증: {msg}\n")
            
            if is_conf:
                confirmed_patterns_log.append({
                    'start_idx': i, 'end_idx': i+4,
                    'pattern_type': val.impulse_type, 'degree': 'Polywave'
                })

    # --- 조정 파동 스캔 ---
    for i in range(len(monowaves) - 2):
        if any(p['start_idx'] <= i <= p['end_idx'] for p in confirmed_patterns_log): continue
        slice_3 = monowaves[i:i+3]
        val = CorrectiveWaveValidator(slice_3)
        if val.validate_3_wave():
            is_conf, msg = confirmer.confirm_zigzag_or_flat(slice_3, val.pattern_name)
            print(f" 🟡 [조정파동 탐지] Wave {i} ~ Wave {i+2} ({val.pattern_name})")
            print(f"    ├─ {val.reasons[0]}")
            print(f"    └─ 🔍 확증 검증: {msg}\n")
            if is_conf:
                confirmed_patterns_log.append({
                    'start_idx': i, 'end_idx': i+2,
                    'pattern_type': val.pattern_name, 'degree': 'Polywave'
                })

    # 4. Phase 5: 파동 병합 및 X파동 복합 조립
    print("-" * 70)
    print(" 🔄 [Phase 5] 파동 병합(Compounding) 및 차수 업그레이드 가동...")
    compounding_engine = WaveCompoundingEngine(monowaves)
    polywaves = compounding_engine.compound_to_polywaves(confirmed_patterns_log)
    multiwaves = compounding_engine.scan_and_compound_complex_corrective(polywaves)
    print(f"    └─ 최종 압축 결과: {len(monowaves)}개 모노파동 -> {len(multiwaves)}개 대형 멀티파동(Multiwave)!\n")

    for idx, mw in enumerate(multiwaves):
        print(f"    ⭐ [Multi-Index {idx}] {mw}")

    print("-" * 70)
    print(" [📊 인터랙티브 차트를 브라우저에 렌더링합니다!]")
    
    vis = NeoWaveVisualizer(df, monowaves)
    vis.create_chart("NeoWave v6.0 Ultimate Analysis Chart")
    if confirmed_patterns_log:
        p = confirmed_patterns_log[0]
        vis.highlight_pattern(p['start_idx'], p['end_idx'], f"Confirmed:<br>{p['pattern_type']}", 
                              color='rgba(0, 255, 100, 0.15)', border_color='#00ff66')
    vis.show()

if __name__ == "__main__":
    run_ultimate_neowave_pipeline()