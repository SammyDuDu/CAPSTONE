# KoSPA 분석 엔진 상세 분석 및 문제점 진단

**분석 일자**: 2025-11-02
**분석 대상**: `vowel_v2.py`, `consonant.py`
**목적**: 로직 검증, 잠재적 버그 발견, 코드 흐름 파악

---

## 목차

1. [엔진 간 의존성 맵](#1-엔진-간-의존성-맵)
2. [Vowel Engine 상세 분석](#2-vowel-engine-상세-분석)
3. [Consonant Engine 상세 분석](#3-consonant-engine-상세-분석)
4. [발견된 문제점 및 권장 사항](#4-발견된-문제점-및-권장-사항)
5. [코드 플로우 다이어그램](#5-코드-플로우-다이어그램)

---

## 1. 엔진 간 의존성 맵

### 1.1 전체 시스템 연결 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                        main.py (FastAPI)                        │
└────────┬────────────────────────────────────────────┬───────────┘
         │                                            │
         ▼                                            ▼
┌──────────────────────┐                  ┌──────────────────────┐
│   vowel_v2.py        │                  │   consonant.py       │
│                      │                  │                      │
│ analyze_single_audio │◀────┐            │ analyze_one_file     │
│         │            │     │            │         │            │
│         ▼            │     │            │         ▼            │
│ convert_to_wav       │◀────┼────────────┤ convert_to_wav       │
│         │            │     │            │   (from vowel_v2)    │
│         ▼            │     │            │         │            │
│ analyze_vowel_and_   │     │            │         ▼            │
│   pitch              │     │            │ load_sound           │
│         │            │     │            │         │            │
│         ▼            │     │            │         ▼            │
│ _stable_window       │     │            │ extract_features_    │
│         │            │     │            │   for_syllable       │
│         ▼            │     │            │         │            │
│ parselmouth.Sound    │     │            │         ├─▶ VOT      │
│   .to_pitch()        │     │            │         ├─▶ Frication│
│   .to_formant_burg() │     │            │         └─▶ Nasal    │
│         │            │     │            │         │            │
│         ▼            │     │            │         ▼            │
│ compute_score        │     │            │ score_against_       │
│         │            │     │            │   reference          │
│         ▼            │     │            │         │            │
│ get_feedback         │     │            │         ▼            │
│         │            │     │            │ (advice_list)        │
│         ▼            │     │            │                      │
│ (optional)           │     │            └──────────────────────┘
│ plot_single_vowel_   │     │
│   space              │     │
│         │            │     │
│         ▼            │     │
│ matplotlib.pyplot    │     │
└──────────────────────┘     │
                             │
         ┌───────────────────┘
         │ Shared Dependency
         ▼
┌──────────────────────┐
│  System Tools        │
│                      │
│ • FFmpeg (subprocess)│
│ • Parselmouth (Praat)│
│ • NumPy              │
│ • SciPy              │
│ • Matplotlib         │
└──────────────────────┘
```

### 1.2 main.py와 엔진 연결

#### main.py → vowel_v2.py
```python
# main.py:15-22
from analysis.vowel_v2 import (
    analyze_single_audio,       # 핵심 분석 함수
    convert_to_wav,             # 오디오 변환
    STANDARD_MALE_FORMANTS,     # 참조 데이터
    STANDARD_FEMALE_FORMANTS,   # 참조 데이터
    plot_single_vowel_space,    # 시각화
)

# main.py:124-166 (run_vowel_analysis 함수)
def run_vowel_analysis(audio_path: str, symbol: str):
    vowel_key = VOWEL_SYMBOL_TO_KEY[symbol]  # "ㅏ" → "a (아)"
    result, error = analyze_single_audio(audio_path, vowel_key, return_reason=True)

    if error:
        raise ValueError(error)

    # 포먼트 플롯 생성
    plot_single_vowel_space(f1, f2, vowel_key, gender, plot_path)

    return {...}  # JSON 응답
```

#### main.py → consonant.py
```python
# main.py:15
from analysis import consonant as consonant_analysis

# main.py:169-228 (run_consonant_analysis 함수)
def run_consonant_analysis(audio_path: str, symbol: str):
    syllable = CONSONANT_SYMBOL_TO_SYLLABLE[symbol]  # "ㄱ" → "가"
    info = consonant_analysis.reference.get(syllable)

    # 오디오 변환 (vowel_v2의 함수 재사용)
    from analysis.vowel_v2 import convert_to_wav
    convert_to_wav(audio_path, wav_path)

    # 자음 분석
    snd, y, sr = consonant_analysis.load_sound(wav_path)
    measured = consonant_analysis.extract_features_for_syllable(...)
    f0, sex = consonant_analysis.estimate_speaker_f0_and_sex(...)
    score, advice = consonant_analysis.score_against_reference(...)

    return {...}
```

**중요**: consonant.py는 `convert_to_wav`를 vowel_v2.py에서 import하여 사용합니다 (코드 재사용).

---

## 2. Vowel Engine 상세 분석

### 2.1 핵심 함수 플로우

```
analyze_single_audio(audio_path, vowel_key)
    │
    ├─▶ 1. 파일 존재 확인 (vowel_v2.py:232-236)
    │
    ├─▶ 2. FFmpeg 변환 (vowel_v2.py:243-249)
    │       convert_to_wav(input, "kospa_temp.wav")
    │           │
    │           └─▶ subprocess.run(["ffmpeg", "-i", input,
    │                   "-y", "-ac", "1", "-ar", "44100", output])
    │
    ├─▶ 3. 포먼트 및 피치 추출 (vowel_v2.py:257)
    │       analyze_vowel_and_pitch("kospa_temp.wav")
    │           │
    │           ├─▶ 오디오 로드 (vowel_v2.py:120)
    │           │       snd_full = parselmouth.Sound(wav_path)
    │           │
    │           ├─▶ Stable Window 추출 (vowel_v2.py:126)
    │           │       _stable_window(snd_full, min_len=0.12)
    │           │           │
    │           │           ├─▶ RMS 계산 (hop=win_size//4)
    │           │           │       for 각 윈도우:
    │           │           │           rms = sqrt(mean(segment^2))
    │           │           │
    │           │           ├─▶ 최고 에너지 윈도우 선택
    │           │           │       rms_list.sort(reverse=True)
    │           │           │       best_rms, best_idx = rms_list[0]
    │           │           │
    │           │           ├─▶ SNR 계산
    │           │           │       noise_floor = median(all_rms)
    │           │           │       snr_ratio = best_rms / noise_floor
    │           │           │
    │           │           └─▶ 서브 오디오 추출
    │           │                   sound.extract_part(start_t, end_t)
    │           │
    │           ├─▶ 품질 검사 (vowel_v2.py:130-137)
    │           │       if seg_len < 0.08: "Too short"
    │           │       if peak_rms < 0.01: "Volume too low"
    │           │       if snr_ratio < 1.5: "Background noise high"
    │           │
    │           ├─▶ 피치 추출 (vowel_v2.py:139-143)
    │           │       pitch = stable.to_pitch(
    │           │           pitch_floor=75.0,
    │           │           pitch_ceiling=500.0
    │           │       )
    │           │       voiced = [f for f in pitch_values if f > 0]
    │           │       f0_mean = mean(voiced)
    │           │
    │           ├─▶ 포먼트 추출 (vowel_v2.py:145-156)
    │           │       formant = stable.to_formant_burg(
    │           │           maximum_formant=5500.0
    │           │       )
    │           │       for each frame:
    │           │           f1_vals.append(formant.get_value_at_time(1, t))
    │           │           f2_vals.append(formant.get_value_at_time(2, t))
    │           │           f3_vals.append(formant.get_value_at_time(3, t))
    │           │
    │           │       f1_mean = nanmedian(f1_vals)
    │           │       f2_mean = nanmedian(f2_vals)
    │           │       f3_mean = nanmedian(f3_vals)
    │           │
    │           └─▶ 반환 (vowel_v2.py:162)
    │                   return f1, f2, f3, f0, quality_hint
    │
    ├─▶ 4. 성별 판별 (vowel_v2.py:271-272)
    │       gender = "Male" if f0 < 165.0 else "Female"
    │       ref_table = MALE_FORMANTS or FEMALE_FORMANTS
    │
    ├─▶ 5. 점수 계산 (vowel_v2.py:281)
    │       compute_score(f1, f2, f3, vowel_key, ref_table)
    │           │
    │           ├─▶ Z-score 계산 (vowel_v2.py:173-174)
    │           │       f1_z = abs(f1 - ref_f1) / ref_f1_sd
    │           │       f2_z = abs(f2 - ref_f2) / ref_f2_sd
    │           │       z_avg = (f1_z + f2_z) / 2
    │           │
    │           ├─▶ F3 가중치 적용 (vowel_v2.py:178-181)
    │           │       if f3 exists:
    │           │           f3_z = abs(f3 - ref_f3) / f3_sd
    │           │           z_avg = z_avg * 0.75 + f3_z * 0.25
    │           │
    │           └─▶ 점수 변환 (vowel_v2.py:183-188)
    │                   if z_avg <= 1.5: score = 100
    │                   else: score = 100 - (z_avg - 1.5) * 60
    │
    ├─▶ 6. 피드백 생성 (vowel_v2.py:282)
    │       get_feedback(vowel_key, f1, f2, ref_table, quality_hint)
    │           │
    │           ├─▶ F1 비교 (vowel_v2.py:202-205)
    │           │       if f1 > ref_f1 + tol:
    │           │           "Mouth too open / tongue too low"
    │           │       elif f1 < ref_f1 - tol:
    │           │           "Mouth too closed / tongue too high"
    │           │
    │           ├─▶ F2 비교 (vowel_v2.py:207-211)
    │           │       if f2 > ref_f2 + tol:
    │           │           "Tongue too front"
    │           │       elif f2 < ref_f2 - tol:
    │           │           "Tongue too back"
    │           │
    │           └─▶ 품질 힌트 추가 (vowel_v2.py:216-217)
    │                   if quality_hint: append to feedback
    │
    └─▶ 7. 결과 반환 (vowel_v2.py:284-298)
            return {
                "vowel_key", "gender", "f0", "f1", "f2", "f3",
                "score", "feedback", "quality_hint"
            }, None
```

### 2.2 발견된 잠재적 문제점

#### 🔴 **P1: 임시 파일 고정명 (Race Condition 위험)**

**위치**: `vowel_v2.py:243`

```python
tmp_wav = "kospa_temp.wav"  # ❌ 고정된 파일명
```

**문제**:
- 동시에 여러 요청이 들어오면 같은 파일을 덮어쓰게 됨
- 멀티스레드/멀티프로세스 환경에서 충돌 가능

**예상 시나리오**:
```
Time    Thread A                Thread B
0ms     convert_to_wav("a.m4a", "kospa_temp.wav")
10ms                            convert_to_wav("b.m4a", "kospa_temp.wav")  # ❌ 덮어씀!
50ms    analyze("kospa_temp.wav")  # ❌ b.m4a 내용 분석!
```

**해결책**:
```python
import tempfile
import uuid

# 옵션 1: tempfile 사용
with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
    tmp_wav = tmp.name

# 옵션 2: UUID 사용
tmp_wav = f"kospa_temp_{uuid.uuid4().hex}.wav"
```

**영향도**: 🔥 높음 (프로덕션에서 간헐적 오류 발생 가능)

---

#### 🟡 **P2: 성별 판별 임계값 단순화**

**위치**: `vowel_v2.py:43, 271`

```python
F0_GENDER_THRESHOLD = 165.0  # 고정값

gender_guess = "Male" if f0 < F0_GENDER_THRESHOLD else "Female"
```

**문제**:
- 165Hz 근처에서 불안정 (예: 164Hz ↔ 166Hz 차이가 극명)
- 개인차 고려 안 됨 (높은 음역대 남성, 낮은 음역대 여성)
- 검증 결과: `sample/vowel_man/` 샘플이 여성으로 판별됨 (F0 169~241Hz)

**개선 방안**:
```python
# 옵션 1: Soft threshold with confidence
def guess_gender_with_confidence(f0):
    if f0 < 140:
        return "Male", 0.95
    elif f0 < 160:
        return "Male", 0.70
    elif f0 < 180:
        return "Female", 0.70  # Ambiguous zone
    else:
        return "Female", 0.95

# 옵션 2: Use calibration data
if user_calibration_exists:
    gender = user_calibration["gender"]
else:
    gender = guess_from_f0(f0)
```

**영향도**: 🟡 중간 (정확도 저하, but 치명적이진 않음)

---

#### 🟡 **P3: 점수 계산 불일치**

**위치**: `vowel_v2.py:183` vs `consonant.py:797`

**Vowel Engine**:
```python
if z_avg <= 1.5:  # 1.5σ 이내
    return 100
penalty = (z_avg - 1.5) * 60.0  # 60점/σ
```

**Consonant Engine**:
```python
if avg_abs_z <= 1.5:  # 동일
    overall_score = 100
penalty = (avg_abs_z - 1.5) * 60.0  # 동일
```

**문제**: README.md에는 "±2.5σ 기준"이라고 명시되어 있지만, 실제 코드는 1.5σ 사용.

**출처**: `README.md:66-68`
```markdown
- **Vowels** – F1/F2/F3 deviations are converted to σ units. Average z ≤ 2.5
  scores 100; beyond that, the score decreases linearly (≈40 points per σ).
```

**문서와 코드 불일치**:
- 문서: 2.5σ, 40점/σ
- 실제: 1.5σ, 60점/σ

**권장**:
1. 코드를 문서에 맞추거나
2. 문서를 코드에 맞춰 수정

**영향도**: 🟡 중간 (기능 작동하지만 혼란 초래)

---

#### 🟢 **P4: F3 가중치 로직 불명확**

**위치**: `vowel_v2.py:178-181`

```python
if "f3" in std and f3:
    f3_sd = std.get("f3_sd", 250.0)  # ❌ f3_sd가 없으면 250Hz 사용
    f3_z = abs(f3 - std["f3"]) / f3_sd
    z_avg = (z_avg * 0.75) + (f3_z * 0.25)
```

**문제**:
- 참조 데이터에 `f3_sd`가 없음 (STANDARD_MALE_FORMANTS, STANDARD_FEMALE_FORMANTS)
- 항상 250Hz를 표준편차로 사용하게 됨
- F3의 실제 변동성을 반영하지 못함

**데이터 확인**:
```python
# vowel_v2.py:24-40
STANDARD_MALE_FORMANTS = {
    'a (아)': {'f1': 651, 'f2': 1156, 'f3': 2500,
               'f1_sd': 136, 'f2_sd': 77},  # f3_sd 없음!
    ...
}
```

**해결책**:
```python
# 옵션 1: f3_sd를 참조 데이터에 추가
STANDARD_MALE_FORMANTS = {
    'a (아)': {..., 'f3_sd': 200},  # 실제 연구 데이터 기반
}

# 옵션 2: F3를 점수 계산에서 제외 (현재도 사실상 의미 없음)
z_avg = (f1_z + f2_z) / 2  # F3 제거
```

**영향도**: 🟢 낮음 (F3는 25% 가중치로 이미 낮음)

---

#### 🟢 **P5: 품질 힌트 임계값 하드코딩**

**위치**: `vowel_v2.py:132-137`

```python
if seg_len < 0.08:  # ❌ 매직 넘버
    quality_msgs.append("Too short; hold ~0.3s.")
if peak_rms < 0.01:  # ❌ 매직 넘버
    quality_msgs.append("Volume too low; speak louder.")
if snr_ratio < 1.5:  # ❌ 매직 넘버
    quality_msgs.append("Background noise high...")
```

**권장**:
```python
# 상수로 추출
MIN_SEGMENT_LENGTH = 0.08
MIN_RMS_THRESHOLD = 0.01
MIN_SNR_RATIO = 1.5
```

**영향도**: 🟢 낮음 (가독성 문제, 기능적 영향 없음)

---

### 2.3 성능 분석

#### Stable Window 추출 복잡도

**위치**: `vowel_v2.py:86-91`

```python
hop = max(win_size // 4, 1)  # 25% overlap
for start_idx in range(0, len(snd_values) - win_size + 1, hop):
    seg = snd_values[start_idx:start_idx+win_size]
    rms = float(np.sqrt(np.mean(seg**2)))
    rms_list.append((rms, start_idx))
```

**시간 복잡도**: O(n * win_size)
- n = 오디오 길이 / hop
- 2초 오디오 (44.1kHz): ~88,200 샘플
- win_size = 0.12s * 44,100 = 5,292 샘플
- hop = 5,292 / 4 ≈ 1,323 샘플
- 반복 횟수: 88,200 / 1,323 ≈ 67회
- 총 연산: 67 * 5,292 ≈ 354,564 연산

**처리 시간**: ~10-50ms (NumPy 최적화 덕분)

**최적화 가능성**:
- 낮음 (이미 NumPy로 최적화됨)
- hop 크기를 늘리면 정확도 저하

---

## 3. Consonant Engine 상세 분석

### 3.1 핵심 함수 플로우

```
analyze_one_file(wav_path, syllable)  # main 함수
    │
    ├─▶ 1. 참조 데이터 로드 (consonant.py:862)
    │       info = reference.get(syllable)
    │       ctype = info["type"]  # stop/fricative/affricate/sonorant
    │
    ├─▶ 2. 오디오 로드 (consonant.py:872-874)
    │       load_sound(wav_path)
    │           │
    │           └─▶ snd = parselmouth.Sound(wav_path)
    │               y = snd.values[0]  # mono signal
    │               sr = snd.sampling_frequency
    │
    ├─▶ 3. 특징 추출 (consonant.py:878)
    │       extract_features_for_syllable(snd, y, sr, syllable, info)
    │           │
    │           ├─▶ 자음 타입별 분기 (consonant.py:811-850)
    │           │
    │           ├─▶ [STOP: ㄱ, ㄷ, ㅂ, ㅋ, ㅌ, ㅍ, ㄲ, ㄸ, ㅃ]
    │           │       │
    │           │       ├─▶ VOT 측정 (consonant.py:817)
    │           │       │       estimate_vot_ms(snd, aspirated_mode)
    │           │       │           │
    │           │       │           ├─▶ Burst 검출 (consonant.py:360-383)
    │           │       │           │       detect_burst_time(snd)
    │           │       │           │           │
    │           │       │           │           ├─▶ Intensity 피크 찾기
    │           │       │           │           │       intensity = snd.to_intensity()
    │           │       │           │           │       max_intensity_frame
    │           │       │           │           │
    │           │       │           │           └─▶ burst_time 반환
    │           │       │           │
    │           │       │           ├─▶ Voice Onset 검출 (consonant.py:385-428)
    │           │       │           │       aspirated_mode 분기:
    │           │       │           │           if aspirated (ㅋ, ㅌ, ㅍ, ㅊ):
    │           │       │           │               intensity_threshold = peak - 20dB
    │           │       │           │           else:
    │           │       │           │               intensity_threshold = peak - 30dB
    │           │       │           │
    │           │       │           │       find_voiced_onset_time()
    │           │       │           │
    │           │       │           └─▶ VOT = onset - burst (ms)
    │           │       │
    │           │       └─▶ Aspiration Ratio (consonant.py:819)
    │           │               aspiration_ratio_after_burst(y, sr, burst_t, voiced_t)
    │           │                   │
    │           │                   ├─▶ VOT 구간 신호 추출
    │           │                   │       vot_sig = y[burst_idx:onset_idx]
    │           │                   │
    │           │                   ├─▶ 고주파 대역 필터링
    │           │                   │       bp_sig = bandpass(vot_sig, sr, 2000, 8000)
    │           │                   │
    │           │                   ├─▶ 에너지 계산
    │           │                   │       vot_energy = sum(bp_sig^2)
    │           │                   │       vowel_energy = sum(vowel_sig^2)
    │           │                   │
    │           │                   └─▶ ratio = vot_energy / total_energy
    │           │
    │           ├─▶ [FRICATIVE: ㅅ, ㅆ, ㅎ]
    │           │       │
    │           │       └─▶ Frication Stats (consonant.py:836)
    │           │               frication_stats(snd, y, sr)
    │           │                   │
    │           │                   ├─▶ Voice Onset 찾기 (consonant.py:600-641)
    │           │                   │       pitch 기반 + intensity 기반 조합
    │           │                   │       first_voiced_time
    │           │                   │
    │           │                   ├─▶ Frication 구간 정의
    │           │                   │       fric_start = snd.xmin (시작)
    │           │                   │       fric_end = first_voiced_time
    │           │                   │
    │           │                   ├─▶ 고주파 필터링 (consonant.py:655-656)
    │           │                   │       fric_sig = bandpass(sig, sr, 2000, 12000)
    │           │                   │
    │           │                   ├─▶ Spectral Centroid 계산 (consonant.py:669)
    │           │                   │       compute_spectral_centroid(fric_sig, sr)
    │           │                   │           │
    │           │                   │           ├─▶ FFT 수행
    │           │                   │           │       spectrum = fft(signal)
    │           │                   │           │
    │           │                   │           ├─▶ 가중 평균
    │           │                   │           │       centroid = sum(freq * mag) / sum(mag)
    │           │                   │           │
    │           │                   │           └─▶ kHz 단위 변환
    │           │                   │
    │           │                   └─▶ return fric_dur_ms, centroid_kHz, confident
    │           │
    │           ├─▶ [AFFRICATE: ㅈ, ㅉ, ㅊ]
    │           │       │
    │           │       ├─▶ VOT (파열음 특징)
    │           │       └─▶ Frication (마찰음 특징)
    │           │
    │           └─▶ [SONORANT: ㄴ, ㄹ, ㅁ]
    │                   │
    │                   ├─▶ Segment Duration (consonant.py:689)
    │                   │       segment_duration_ms(snd)
    │                   │           duration_ms = snd.get_total_duration() * 1000
    │                   │
    │                   └─▶ Nasal Low-Freq Ratio (consonant.py:708)
    │                           lowfreq_ratio(y, sr, cutoff=500)
    │                               │
    │                               ├─▶ 저주파 필터링
    │                               │       lp_sig = lowpass(y, sr, 500)
    │                               │
    │                               ├─▶ 에너지 계산
    │                               │       low_energy = sum(lp_sig^2)
    │                               │       total_energy = sum(y^2)
    │                               │
    │                               └─▶ ratio = low_energy / total_energy
    │
    ├─▶ 4. 화자 F0 추정 (consonant.py:881-886)
    │       estimate_speaker_f0_and_sex(wav_path, vot_ms)
    │           │
    │           ├─▶ VOT 이후 구간에서 F0 추출
    │           │       offset_s = (vot_ms + extra_offset_ms) / 1000
    │           │       vowel_part = snd.extract_part(offset_s, ...)
    │           │       pitch = vowel_part.to_pitch()
    │           │
    │           ├─▶ 유성음 프레임 필터링
    │           │       voiced_frames = [f for f in pitch if 75 < f < 400]
    │           │
    │           ├─▶ 중앙값 F0 계산
    │           │       median_f0 = np.median(voiced_frames)
    │           │
    │           └─▶ 성별 판별
    │                   sex = "male" if median_f0 < 160 else "female"
    │
    ├─▶ 5. 점수 계산 (consonant.py:890-894)
    │       score_against_reference(measured, ref_feats, sex)
    │           │
    │           ├─▶ 각 특징별 Z-score 계산 (consonant.py:741-756)
    │           │       for feat_name in ref_feats:
    │           │           mean, sd = ref_feats[feat_name][sex]
    │           │           measured_val = measured[feat_name]
    │           │           z = capped_z(measured_val, mean, sd, cap=3.0)
    │           │           z_list.append(abs(z))
    │           │
    │           ├─▶ 평균 Z-score (consonant.py:797)
    │           │       avg_abs_z = sum(z_list) / len(z_list)
    │           │
    │           ├─▶ 점수 변환 (consonant.py:798-802)
    │           │       if avg_abs_z <= 1.5:
    │           │           score = 100
    │           │       else:
    │           │           penalty = (avg_abs_z - 1.5) * 60
    │           │           score = max(0, 100 - penalty)
    │           │
    │           └─▶ 피드백 생성 (consonant.py:758-789)
    │                   특징별 조언 (VOT, aspiration, frication, nasal...)
    │
    └─▶ 6. 결과 반환 (consonant.py:896-954)
            return {
                "syllable", "sex", "f0", "measured_features",
                "per_feature_report", "overall_score", "advice"
            }
```

### 3.2 발견된 잠재적 문제점

#### 🔴 **C1: 성별 임계값 불일치**

**위치**:
- `vowel_v2.py:43, 271`: 165Hz
- `consonant.py:544`: 160Hz

```python
# vowel_v2.py
F0_GENDER_THRESHOLD = 165.0
gender_guess = "Male" if f0 < F0_GENDER_THRESHOLD else "Female"

# consonant.py:544
if median_f0 < 160:
    sex_guess = "male"
else:
    sex_guess = "female"
```

**문제**:
- 같은 사용자가 모음과 자음을 녹음했을 때 성별이 다르게 판별될 수 있음
- 예: F0 = 162Hz → 모음: Female, 자음: Male

**해결책**:
```python
# config.py (공통 파일)
F0_GENDER_THRESHOLD = 165.0

# vowel_v2.py
from .config import F0_GENDER_THRESHOLD

# consonant.py
from .config import F0_GENDER_THRESHOLD
```

**영향도**: 🔥 높음 (일관성 문제)

---

#### 🔴 **C2: None 점수 버그 (수정됨)**

**위치**: `consonant.py:791-795` (2025-11-02 수정)

**Before**:
```python
if len(z_list) == 0:
    overall_score = None  # ❌ TypeError 유발
```

**After**:
```python
if len(z_list) == 0:
    overall_score = 0.0  # ✅ 안전한 기본값
    advice_list.append("Could not extract enough acoustic features.")
```

**발생 조건**:
- 모든 측정값이 None일 때 (예: VOT 검출 실패, frication 검출 실패)
- 자음 타입과 참조 데이터 불일치

**영향도**: 🔥 높음 (크래시 유발) → ✅ 해결됨

---

#### 🟡 **C3: Aspirated Mode 판별 로직**

**위치**: `consonant.py:329-336, 813-814`

```python
def is_aspirated_like(syllable):
    aspirated_chars = ["카", "타", "파", "차"]
    return syllable in aspirated_chars

# extract_features_for_syllable
aspirated_mode = False
if ctype in ["stop", "affricate"] and is_aspirated_like(syllable_label):
    aspirated_mode = True
```

**문제**:
- 하드코딩된 리스트
- 확장성 낮음 (새 자음 추가 시 수동 업데이트 필요)

**개선안**:
```python
# reference 데이터에 추가
reference = {
    "카": {
        "type": "stop",
        "aspirated": True,  # ✅ 메타데이터로 관리
        "features": {...}
    }
}

# 판별 로직
aspirated_mode = info.get("aspirated", False)
```

**영향도**: 🟡 중간 (유지보수성)

---

#### 🟡 **C4: Frication 신뢰도 기준 불명확**

**위치**: `consonant.py:671-683`

```python
confident = False
if fric_dur_ms > 10.0:  # ❌ 매직 넘버
    raw_centroid_hz = compute_spectral_centroid(...)
    if raw_centroid_hz is not None and raw_centroid_hz > 100:  # ❌ 매직 넘버
        centroid_kHz = raw_centroid_hz / 1000.0
        confident = True
```

**문제**:
- 10ms, 100Hz 임계값의 근거 불명확
- `confident=False`일 때 None 반환 → z_list에 추가 안 됨 → 점수 계산에서 제외

**영향**:
- ㅅ, ㅆ, ㅎ 분석 시 frication 검출 실패 시 0점 가능성

**권장**:
```python
# 상수화
MIN_FRICATION_DURATION_MS = 10.0  # ㅅ 최소 지속 시간
MIN_CENTROID_HZ = 100.0           # 유의미한 스펙트럼 중심
```

**영향도**: 🟡 중간

---

#### 🟢 **C5: Z-score Capping**

**위치**: `consonant.py:726-734`

```python
def capped_z(value, mean, sd, cap=3.0):
    z = raw_z_score(value, mean, sd)
    if z is None:
        return None
    if z > cap:
        return cap  # ✅ 3σ 이상은 3으로 제한
    if z < -cap:
        return -cap
    return z
```

**특징**:
- Z-score를 ±3σ로 제한
- 극단값 방지 (outlier 처리)

**장점**:
- 잡음이 많은 샘플에 대해 과도한 패널티 방지

**단점**:
- 매우 잘못된 발음도 일정 수준 이상 패널티 받지 않음

**권장**: 현재 구현이 합리적. 유지.

**영향도**: 🟢 낮음 (정상 작동)

---

### 3.3 성능 분석

#### VOT 측정 복잡도

**위치**: `consonant.py:338-428`

**시간 복잡도**:
- Intensity object 생성: O(n) (Praat 내부)
- Pitch object 생성: O(n)
- 프레임별 순회: O(frames) ≈ O(n / hop)
- 총: O(n)

**처리 시간**: ~100-500ms (Praat 의존)

**병목 지점**:
- `snd.to_intensity()`: ~50-100ms
- `snd.to_pitch()`: ~100-200ms

**최적화 가능성**:
- 낮음 (Praat 알고리즘 의존)
- 캐싱 가능 (같은 오디오 재분석 시)

---

## 4. 발견된 문제점 및 권장 사항

### 4.1 심각도별 분류

| 심각도 | 코드 | 문제 | 영향 | 상태 |
|--------|------|------|------|------|
| 🔴 높음 | V-P1 | 임시 파일 고정명 (Race Condition) | 동시 요청 시 충돌 | ⚠️ 미해결 |
| 🔴 높음 | C-C1 | 성별 임계값 불일치 (165 vs 160) | 일관성 문제 | ⚠️ 미해결 |
| 🔴 높음 | C-C2 | None 점수 버그 | 크래시 유발 | ✅ 해결됨 |
| 🟡 중간 | V-P2 | 성별 판별 단순화 | 정확도 저하 | ⚠️ 미해결 |
| 🟡 중간 | V-P3 | 점수 계산 문서 불일치 | 혼란 초래 | ⚠️ 미해결 |
| 🟡 중간 | C-C3 | Aspirated 판별 하드코딩 | 유지보수성 | ⚠️ 미해결 |
| 🟡 중간 | C-C4 | Frication 신뢰도 기준 불명확 | 점수 불안정 | ⚠️ 미해결 |
| 🟢 낮음 | V-P4 | F3 가중치 불명확 | 미미한 영향 | ⚠️ 미해결 |
| 🟢 낮음 | V-P5 | 매직 넘버 하드코딩 | 가독성 | ⚠️ 미해결 |

### 4.2 우선 순위별 수정 권장 사항

#### 🔥 **즉시 수정 필요**

**1. 임시 파일명 Race Condition (V-P1)**

```python
# vowel_v2.py:243-249
# Before
tmp_wav = "kospa_temp.wav"

# After
import tempfile
with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
    tmp_wav = tmp.name

if not convert_to_wav(audio_path, tmp_wav):
    ...

try:
    f1, f2, f3, f0, qhint = analyze_vowel_and_pitch(tmp_wav)
finally:
    try:
        os.remove(tmp_wav)
    except OSError:
        pass
```

**2. 성별 임계값 통일 (C-C1)**

```python
# analysis/config.py (새 파일)
F0_GENDER_THRESHOLD = 165.0  # Hz

# vowel_v2.py
from .config import F0_GENDER_THRESHOLD
gender_guess = "Male" if f0 < F0_GENDER_THRESHOLD else "Female"

# consonant.py
from .config import F0_GENDER_THRESHOLD
sex_guess = "male" if median_f0 < F0_GENDER_THRESHOLD else "female"
```

---

#### 📋 **차후 개선 사항**

**3. 점수 계산 로직 문서화**

README.md 수정:
```markdown
# Before
Average z ≤ 2.5 scores 100; beyond that, the score decreases linearly (≈40 points per σ).

# After
Average z ≤ 1.5 scores 100; beyond that, the score decreases linearly (60 points per σ).
Score = max(0, 100 - (z_avg - 1.5) * 60)
```

**4. 상수 추출 및 중앙 관리**

```python
# analysis/config.py
# Vowel Analysis
MIN_SEGMENT_LENGTH = 0.08  # seconds
MIN_RMS_THRESHOLD = 0.01
MIN_SNR_RATIO = 1.5

# Consonant Analysis
MIN_FRICATION_DURATION_MS = 10.0
MIN_CENTROID_HZ = 100.0

# Scoring
PERFECT_SCORE_THRESHOLD = 1.5  # sigma
PENALTY_PER_SIGMA = 60.0  # points
```

---

## 5. 코드 플로우 다이어그램

### 5.1 전체 요청 처리 흐름

```
[User Browser]
     │
     │ 2초 녹음 (MediaRecorder API)
     │ → Blob (audio/webm, Opus codec)
     ▼
[POST /api/analyze-sound]
     │ multipart/form-data
     │ - audio: File
     │ - userid: int
     │ - sound: string ("ㅏ" or "ㄱ")
     ▼
[main.py:468] analyze_sound()
     │
     ├─ userid 검증 (DB query)
     │
     ├─ analyse_uploaded_audio(audio, sound)  # main.py:231
     │     │
     │     ├─ resolve_sound_symbol(sound)  # main.py:83
     │     │     │
     │     │     ├─ if sound in VOWEL_SYMBOL_TO_KEY → "vowel"
     │     │     └─ if sound in CONSONANT_SYMBOL_TO_SYLLABLE → "consonant"
     │     │
     │     ├─ save_upload_to_temp(audio)  # main.py:109
     │     │     │
     │     │     └─ NamedTemporaryFile(suffix=".webm")  # ✅ 안전
     │     │
     │     ├─ [IF VOWEL]
     │     │     run_vowel_analysis(temp_path, symbol)  # main.py:124
     │     │         │
     │     │         ├─ analyze_single_audio()  # vowel_v2.py:225
     │     │         │     │
     │     │         │     ├─ convert_to_wav()  # ⚠️ Race Condition!
     │     │         │     ├─ analyze_vowel_and_pitch()
     │     │         │     ├─ compute_score()
     │     │         │     └─ get_feedback()
     │     │         │
     │     │         └─ plot_single_vowel_space()  # 선택적
     │     │
     │     └─ [IF CONSONANT]
     │           run_consonant_analysis(temp_path, symbol)  # main.py:169
     │               │
     │               ├─ convert_to_wav()  # vowel_v2에서 import
     │               ├─ consonant_analysis.load_sound()
     │               ├─ extract_features_for_syllable()
     │               ├─ estimate_speaker_f0_and_sex()
     │               └─ score_against_reference()
     │
     ├─ normalise_score(score)  # main.py:244
     │
     ├─ [DB UPDATE] progress 테이블 업데이트
     │     UPDATE progress SET progress = GREATEST(progress, %s)
     │     WHERE userid = %s AND sound = %s
     │
     └─ return JSON response
           {
               "score": 85,
               "feedback": "...",
               "details": {...}
           }
```

### 5.2 의존성 그래프

```
main.py
    │
    ├─ imports
    │   ├─ analysis.vowel_v2
    │   │   ├─ analyze_single_audio ✅
    │   │   ├─ convert_to_wav ✅
    │   │   ├─ STANDARD_MALE_FORMANTS ✅
    │   │   ├─ STANDARD_FEMALE_FORMANTS ✅
    │   │   └─ plot_single_vowel_space ✅
    │   │
    │   └─ analysis.consonant (as consonant_analysis)
    │       ├─ reference ✅
    │       ├─ load_sound ✅
    │       ├─ extract_features_for_syllable ✅
    │       ├─ estimate_speaker_f0_and_sex ✅
    │       └─ score_against_reference ✅
    │
    └─ internal dependencies
        ├─ psycopg2 (DB)
        ├─ fastapi
        ├─ jinja2
        └─ tempfile

vowel_v2.py
    │
    ├─ external libs
    │   ├─ numpy ✅
    │   ├─ parselmouth ✅
    │   ├─ matplotlib ✅
    │   └─ subprocess (ffmpeg) ✅
    │
    └─ internal calls
        analyze_single_audio()
            └─ convert_to_wav()  # ⚠️ Race Condition
                └─ analyze_vowel_and_pitch()
                    └─ _stable_window()
                        └─ compute_score()
                            └─ get_feedback()
                                └─ plot_single_vowel_space()

consonant.py
    │
    ├─ external libs
    │   ├─ numpy ✅
    │   ├─ scipy.signal ✅
    │   ├─ parselmouth ✅
    │   └─ (vowel_v2.convert_to_wav) ✅ [간접 의존]
    │
    └─ internal calls
        analyze_one_file()  # main 분석 함수 (main.py에서는 직접 호출 안 함)
            └─ load_sound()
                └─ extract_features_for_syllable()
                    ├─ [STOP] estimate_vot_ms()
                    │           └─ detect_burst_time()
                    │           └─ aspiration_ratio_after_burst()
                    │                   └─ bandpass()
                    │
                    ├─ [FRICATIVE] frication_stats()
                    │               └─ compute_spectral_centroid()
                    │
                    └─ [SONORANT] segment_duration_ms()
                                  lowfreq_ratio()
                                      └─ lowpass()

                    └─ estimate_speaker_f0_and_sex()
                        └─ score_against_reference()
                            └─ capped_z()
                                └─ raw_z_score()
```

### 5.3 상호 의존성 요약

| 파일 | 의존 대상 | 제공 기능 |
|------|-----------|-----------|
| **main.py** | vowel_v2, consonant, psycopg2, fastapi | API 엔드포인트, 라우팅 |
| **vowel_v2.py** | parselmouth, numpy, matplotlib, subprocess | 모음 분석, FFmpeg 변환 |
| **consonant.py** | parselmouth, numpy, scipy, (vowel_v2) | 자음 분석 |

**주의**: `consonant.py`는 `vowel_v2.convert_to_wav`를 간접적으로 사용하지만, main.py에서 직접 호출하므로 순환 의존성 없음.

---

## 6. 결론 및 종합 권장 사항

### 6.1 엔진 품질 평가

| 항목 | 평가 | 상세 |
|------|------|------|
| **알고리즘 정확성** | ⭐⭐⭐⭐☆ | 음성학 이론 기반, 합리적인 구현 |
| **코드 안정성** | ⭐⭐⭐☆☆ | Race Condition, None 버그 존재 |
| **성능** | ⭐⭐⭐⭐☆ | 1-3초 처리 시간, 실시간 피드백 가능 |
| **확장성** | ⭐⭐⭐☆☆ | 하드코딩 많음, 새 음소 추가 어려움 |
| **유지보수성** | ⭐⭐⭐☆☆ | 문서화 부족, 매직 넘버 많음 |

### 6.2 우선순위별 개선 로드맵

#### Phase 1: 긴급 수정 (배포 전 필수)
1. ✅ None 점수 버그 수정 (완료)
2. ⚠️ 임시 파일 Race Condition 수정
3. ⚠️ 성별 임계값 통일

#### Phase 2: 품질 개선 (배포 후 1개월 내)
4. 상수 중앙화 (config.py)
5. 문서-코드 일치성 확보
6. 에러 핸들링 강화

#### Phase 3: 장기 개선 (2개월~)
7. 성별 판별 알고리즘 개선
8. 캘리브레이션 기능 구현
9. 참조 데이터 확장 (복모음, 겹받침)

---

**분석자**: Claude Code
**분석 완료일**: 2025-11-02
**다음 리뷰 예정일**: 배포 후 1개월
