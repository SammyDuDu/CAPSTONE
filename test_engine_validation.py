#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KoSPA 엔진 검증 스크립트
모음/자음 분석 엔진을 샘플 데이터로 테스트하고 품질을 평가합니다.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Analysis engines
from analysis.vowel_v2 import analyze_single_audio, STANDARD_MALE_FORMANTS, STANDARD_FEMALE_FORMANTS
from analysis import consonant as consonant_analysis
from analysis.vowel_v2 import convert_to_wav


VOWEL_SAMPLES = {
    'a (아)': 'sample/vowel_man/아.m4a',
    'eo (어)': 'sample/vowel_man/어.m4a',
    'o (오)': 'sample/vowel_man/오.m4a',
    'u (우)': 'sample/vowel_man/우.m4a',
    'eu (으)': 'sample/vowel_man/으.m4a',
    'i (이)': 'sample/vowel_man/이.m4a',
}

CONSONANT_SAMPLES = {
    'ㄱ': 'sample/consonant/가.m4a',
    'ㄴ': 'sample/consonant/나.m4a',
    'ㄷ': 'sample/consonant/다.m4a',
    'ㄹ': 'sample/consonant/라.m4a',
    'ㅁ': 'sample/consonant/마.m4a',
    'ㅂ': 'sample/consonant/바.m4a',
    'ㅅ': 'sample/consonant/사.m4a',
    'ㅈ': 'sample/consonant/자.m4a',
    'ㅊ': 'sample/consonant/차.m4a',
    'ㅋ': 'sample/consonant/카.m4a',
    'ㅌ': 'sample/consonant/타.m4a',
    'ㅍ': 'sample/consonant/파.m4a',
    'ㅎ': 'sample/consonant/하.m4a',
}

CONSONANT_SYMBOL_TO_SYLLABLE = {
    "ㄱ": "가", "ㄴ": "나", "ㄷ": "다", "ㄹ": "라",
    "ㅁ": "마", "ㅂ": "바", "ㅅ": "사", "ㅈ": "자",
    "ㅊ": "차", "ㅋ": "카", "ㅌ": "타", "ㅍ": "파", "ㅎ": "하",
}


def print_section(title: str):
    """섹션 헤더 출력"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)


def test_vowel_engine():
    """모음 분석 엔진 테스트"""
    print_section("모음 분석 엔진 검증")

    results = []

    for vowel_key, audio_path in VOWEL_SAMPLES.items():
        if not os.path.exists(audio_path):
            print(f"⚠️  {vowel_key}: 샘플 파일 없음 ({audio_path})")
            continue

        print(f"\n[{vowel_key}] 분석 중... ({audio_path})")

        try:
            result, error = analyze_single_audio(audio_path, vowel_key, return_reason=True)

            if error:
                print(f"  ❌ 에러: {error}")
                results.append({
                    'vowel': vowel_key,
                    'status': 'error',
                    'error': error
                })
                continue

            # 결과 출력
            score = result.get('score', 0)
            gender = result.get('gender', 'Unknown')
            f0 = result.get('f0', 0)
            f1 = result.get('f1', 0)
            f2 = result.get('f2', 0)
            f3 = result.get('f3', 0)
            feedback = result.get('feedback', '')
            quality_hint = result.get('quality_hint', '')

            # 기준값 가져오기
            ref_table = STANDARD_MALE_FORMANTS if gender == "Male" else STANDARD_FEMALE_FORMANTS
            ref = ref_table.get(vowel_key, {})

            print(f"  ✅ 점수: {score:.1f}/100")
            print(f"  👤 성별: {gender} (F0: {f0:.1f} Hz)")
            print(f"  📊 포먼트:")
            print(f"      F1: {f1:.0f} Hz (기준: {ref.get('f1', 0):.0f} ± {ref.get('f1_sd', 0):.0f})")
            print(f"      F2: {f2:.0f} Hz (기준: {ref.get('f2', 0):.0f} ± {ref.get('f2_sd', 0):.0f})")
            print(f"      F3: {f3:.0f} Hz (기준: {ref.get('f3', 0):.0f})")

            if quality_hint:
                print(f"  🎤 품질: {quality_hint}")

            print(f"  💬 피드백: {feedback}")

            # 점수 평가
            if score >= 90:
                status_emoji = "🌟 우수"
            elif score >= 70:
                status_emoji = "👍 양호"
            elif score >= 50:
                status_emoji = "⚠️  개선 필요"
            else:
                status_emoji = "❌ 불량"

            print(f"  📈 상태: {status_emoji}")

            results.append({
                'vowel': vowel_key,
                'status': 'success',
                'score': score,
                'gender': gender,
                'formants': {'f1': f1, 'f2': f2, 'f3': f3},
                'quality_hint': quality_hint
            })

        except Exception as e:
            print(f"  ❌ 예외 발생: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append({
                'vowel': vowel_key,
                'status': 'exception',
                'error': str(e)
            })

    # 통계 요약
    print_section("모음 분석 결과 요약")
    success_count = sum(1 for r in results if r['status'] == 'success')
    avg_score = sum(r.get('score', 0) for r in results if r['status'] == 'success') / max(success_count, 1)

    print(f"총 테스트: {len(results)}")
    print(f"성공: {success_count}")
    print(f"실패: {len(results) - success_count}")
    print(f"평균 점수: {avg_score:.1f}/100")

    return results


def test_consonant_engine():
    """자음 분석 엔진 테스트"""
    print_section("자음 분석 엔진 검증")

    results = []

    for symbol, audio_path in CONSONANT_SAMPLES.items():
        if not os.path.exists(audio_path):
            print(f"⚠️  {symbol}: 샘플 파일 없음 ({audio_path})")
            continue

        syllable = CONSONANT_SYMBOL_TO_SYLLABLE[symbol]
        print(f"\n[{symbol} ({syllable})] 분석 중... ({audio_path})")

        try:
            # 자음 분석 프로세스
            info = consonant_analysis.reference.get(syllable)
            if info is None:
                print(f"  ⚠️  {symbol} ({syllable})는 지원되지 않는 자음입니다.")
                results.append({
                    'consonant': symbol,
                    'syllable': syllable,
                    'status': 'unsupported'
                })
                continue

            # WAV 변환
            from tempfile import NamedTemporaryFile
            tmp_wav = NamedTemporaryFile(delete=False, suffix='.wav')
            wav_path = tmp_wav.name
            tmp_wav.close()

            if not convert_to_wav(audio_path, wav_path):
                print(f"  ❌ 오디오 변환 실패")
                os.remove(wav_path)
                results.append({
                    'consonant': symbol,
                    'syllable': syllable,
                    'status': 'conversion_error'
                })
                continue

            # 분석 실행
            snd, y, sr = consonant_analysis.load_sound(wav_path)
            measured = consonant_analysis.extract_features_for_syllable(snd, y, sr, syllable, info)

            vot_for_pitch = measured.get("VOT_ms")
            f0_est, sex_guess = consonant_analysis.estimate_speaker_f0_and_sex(
                wav_path=wav_path,
                vot_ms=vot_for_pitch
            )

            sex_for_scoring = sex_guess if sex_guess != "unknown" else "female"
            per_feature, overall_score, advice = consonant_analysis.score_against_reference(
                measured,
                info["features"],
                sex_for_scoring
            )

            # 임시 파일 삭제
            os.remove(wav_path)

            # 결과 출력
            print(f"  ✅ 점수: {overall_score:.1f}/100")
            print(f"  👤 성별: {sex_guess} (F0: {f0_est:.1f} Hz)")
            print(f"  📊 음향 특징:")

            for feat_name, feat_data in per_feature.items():
                measured_val = feat_data.get('measured', 'N/A')
                ref_val = feat_data.get('ref', 'N/A')
                z_score = feat_data.get('z', 'N/A')

                if isinstance(measured_val, (int, float)) and isinstance(ref_val, (int, float)):
                    print(f"      {feat_name}: {measured_val:.2f} (기준: {ref_val:.2f}, z={z_score:.2f})")
                else:
                    print(f"      {feat_name}: {measured_val}")

            if advice:
                print(f"  💬 피드백:")
                for adv in advice:
                    print(f"      - {adv}")

            # 점수 평가
            if overall_score >= 90:
                status_emoji = "🌟 우수"
            elif overall_score >= 70:
                status_emoji = "👍 양호"
            elif overall_score >= 50:
                status_emoji = "⚠️  개선 필요"
            else:
                status_emoji = "❌ 불량"

            print(f"  📈 상태: {status_emoji}")

            results.append({
                'consonant': symbol,
                'syllable': syllable,
                'status': 'success',
                'score': overall_score,
                'gender': sex_guess,
                'features': measured
            })

        except Exception as e:
            print(f"  ❌ 예외 발생: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append({
                'consonant': symbol,
                'syllable': syllable,
                'status': 'exception',
                'error': str(e)
            })

    # 통계 요약
    print_section("자음 분석 결과 요약")
    success_count = sum(1 for r in results if r['status'] == 'success')
    avg_score = sum(r.get('score', 0) for r in results if r['status'] == 'success') / max(success_count, 1)

    print(f"총 테스트: {len(results)}")
    print(f"성공: {success_count}")
    print(f"실패: {len(results) - success_count}")
    print(f"평균 점수: {avg_score:.1f}/100")

    return results


def test_multiple_samples():
    """10sample_vowel 디렉토리의 다중 샘플 테스트"""
    print_section("다중 샘플 일관성 검증 (10sample_vowel)")

    base_dir = Path('sample/10sample_vowel')

    for vowel_dir in base_dir.iterdir():
        if not vowel_dir.is_dir():
            continue

        vowel_name = vowel_dir.name
        vowel_key_map = {
            '아': 'a (아)',
            '어': 'eo (어)',
            '오': 'o (오)',
            '우': 'u (우)',
            '으': 'eu (으)',
            '이': 'i (이)',
        }

        vowel_key = vowel_key_map.get(vowel_name)
        if not vowel_key:
            continue

        print(f"\n[{vowel_name}] 10개 샘플 분석 중...")

        scores = []
        wav_files = list(vowel_dir.glob('*.wav'))

        for i, wav_file in enumerate(wav_files[:10], 1):
            try:
                result, error = analyze_single_audio(str(wav_file), vowel_key, return_reason=True)
                if not error:
                    score = result.get('score', 0)
                    scores.append(score)
                    status = "✅" if score >= 70 else "⚠️"
                    print(f"  {status} 샘플 {i}: {score:.1f}점")
            except Exception as e:
                print(f"  ❌ 샘플 {i}: 에러 ({str(e)[:50]})")

        if scores:
            avg = sum(scores) / len(scores)
            std = (sum((s - avg) ** 2 for s in scores) / len(scores)) ** 0.5
            min_score = min(scores)
            max_score = max(scores)

            print(f"\n  📊 [{vowel_name}] 통계:")
            print(f"      평균: {avg:.1f}점")
            print(f"      표준편차: {std:.1f}")
            print(f"      범위: {min_score:.1f} ~ {max_score:.1f}")

            if std > 20:
                print(f"      ⚠️  표준편차가 큽니다! 샘플 품질이 일관되지 않을 수 있습니다.")
            else:
                print(f"      ✅ 일관성 양호")


if __name__ == '__main__':
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                 KoSPA 엔진 검증 도구                          ║
    ║          Korean Speech Pronunciation Analyzer                 ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)

    # 1. 모음 엔진 테스트
    vowel_results = test_vowel_engine()

    # 2. 자음 엔진 테스트
    consonant_results = test_consonant_engine()

    # 3. 다중 샘플 일관성 테스트
    test_multiple_samples()

    # 최종 요약
    print_section("최종 검증 결과")

    vowel_success = sum(1 for r in vowel_results if r['status'] == 'success')
    consonant_success = sum(1 for r in consonant_results if r['status'] == 'success')

    print(f"✅ 모음 엔진: {vowel_success}/{len(vowel_results)} 성공")
    print(f"✅ 자음 엔진: {consonant_success}/{len(consonant_results)} 성공")

    if vowel_success == len(vowel_results) and consonant_success == len(consonant_results):
        print("\n🎉 모든 테스트 통과! 엔진이 정상 작동합니다.")
    else:
        print("\n⚠️  일부 테스트 실패. 위 로그를 확인하세요.")
