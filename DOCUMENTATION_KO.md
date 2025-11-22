# KoSPA - Korean Speech Pronunciation Analyzer
## 프로젝트 전체 문서

**Version**: 1.0.0
**Last Updated**: 2025-11-02
**Python Version**: 3.11.0
**License**: MIT (추정)

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [기술 스택](#3-기술-스택)
4. [분석 엔진 상세](#4-분석-엔진-상세)
5. [API 명세](#5-api-명세)
6. [데이터베이스 스키마](#6-데이터베이스-스키마)
7. [프론트엔드 구조](#7-프론트엔드-구조)
8. [배포 가이드](#8-배포-가이드)
9. [알려진 이슈 및 해결책](#9-알려진-이슈-및-해결책)
10. [개발 가이드](#10-개발-가이드)

---

## 1. 프로젝트 개요

### 1.1 목적
한국어 학습자를 위한 실시간 발음 분석 및 피드백 시스템. 음성학적 분석 알고리즘을 기반으로 모음과 자음의 정확도를 객관적으로 평가하고, 구체적인 교정 방법을 제시합니다.

### 1.2 주요 기능
- **브라우저 기반 2초 음성 녹음** (MediaRecorder API)
- **이중 분석 엔진**:
  - 모음: 포먼트(F1, F2, F3) 분석
  - 자음: VOT, 마찰음, 비음 에너지 측정
- **시각적 피드백**: 포먼트 공간 플롯 생성
- **개인화 캘리브레이션**: 사용자별 기준값 설정
- **진행도 추적**: PostgreSQL 기반 학습 이력 관리

### 1.3 지원 음소
- **모음 (6개)**: ㅏ, ㅓ, ㅗ, ㅜ, ㅡ, ㅣ
- **자음 (18개)**:
  - 평음: ㄱ, ㄴ, ㄷ, ㄹ, ㅁ, ㅂ, ㅅ, ㅈ, ㅎ
  - 경음: ㄲ, ㄸ, ㅃ, ㅆ, ㅉ
  - 격음: ㅋ, ㅌ, ㅍ, ㅊ

---

## 2. 시스템 아키텍처

### 2.1 전체 구조도

```
┌─────────────────────────────────────────────────────────────┐
│                    USER (Web Browser)                       │
│  MediaRecorder API → FormData → Fetch API                  │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Application (main.py)                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Web Layer: Jinja2 Templates + Static Files          │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ API Layer: /api/analyze-sound, /api/auth/*, etc    │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Audio Pipeline: Upload → FFmpeg → WAV conversion   │   │
│  └────────────┬─────────────────────────┬──────────────┘   │
│               │                         │                   │
│    ┌──────────▼──────────┐   ┌─────────▼──────────┐       │
│    │  Vowel Engine       │   │ Consonant Engine   │       │
│    │  (vowel_v2.py)      │   │ (consonant.py)     │       │
│    │  - Formant Analysis │   │ - VOT Measurement  │       │
│    │  - Gender Detection │   │ - Aspiration Ratio │       │
│    │  - Plot Generation  │   │ - Frication Stats  │       │
│    └─────────────────────┘   └────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ PostgreSQL   │ │ Static FS    │ │   FFmpeg     │
│ (Render DB)  │ │ (Ephemeral)  │ │  (System)    │
└──────────────┘ └──────────────┘ └──────────────┘
```

### 2.2 디렉토리 구조

```
CAPSTONE/
├── main.py                    # FastAPI 애플리케이션 엔트리포인트 (532줄)
├── requirements.txt           # Python 의존성
├── runtime.txt                # Python 버전 명시 (3.11.0)
├── run.sh                     # Uvicorn 실행 스크립트
├── build.sh                   # Render.com 빌드 스크립트 (ffmpeg 설치)
├── render.yaml                # Render.com IaC 설정
├── .env.example               # 환경 변수 템플릿
├── test_engine_validation.py  # 엔진 검증 스크립트
│
├── analysis/                  # 음성 분석 엔진
│   ├── vowel_v2.py           # 모음 분석 (11,885 bytes)
│   ├── consonant.py          # 자음 분석 (32,737 bytes, 버그 수정됨)
│   ├── plot_vowel_space.py   # 포먼트 플롯 생성
│   └── README.md             # 엔진 상세 문서
│
├── templates/                 # Jinja2 HTML 템플릿
│   ├── base.html             # 기본 레이아웃
│   ├── index.html            # 메인 페이지 (음소 선택)
│   └── sound.html            # 녹음 및 분석 페이지
│
├── static/                    # 정적 파일
│   ├── scripts/
│   │   ├── script.js         # 메인 JavaScript
│   │   ├── ui.js             # 사용자 인터페이스 로직
│   │   └── sound.js          # 녹음 및 분석 통신 (80줄)
│   ├── styles/
│   │   └── style.css         # Tailwind CSS
│   └── images/
│       └── analysis/         # 동적 생성 포먼트 플롯 (임시 저장)
│
└── sample/                    # 테스트용 샘플 오디오
    ├── vowel_man/            # 모음 샘플 (실제로는 여성 음성!)
    ├── consonant/            # 자음 샘플
    └── 10sample_vowel/       # 다중 샘플 (일관성 테스트용)
```

---

## 3. 기술 스택

### 3.1 백엔드
| 기술 | 버전 | 용도 |
|------|------|------|
| **Python** | 3.11.0 | 런타임 환경 |
| **FastAPI** | latest | 웹 프레임워크 |
| **Uvicorn** | latest | ASGI 서버 |
| **Praat-Parselmouth** | latest | 음성 분석 (Praat 래퍼) |
| **NumPy** | latest | 수치 연산 |
| **SciPy** | latest | 신호 처리 |
| **Matplotlib** | latest | 포먼트 플롯 생성 |
| **psycopg2-binary** | latest | PostgreSQL 드라이버 |
| **python-multipart** | latest | 파일 업로드 처리 |
| **Jinja2** | latest | HTML 템플릿 렌더링 |

### 3.2 프론트엔드
| 기술 | 설명 |
|------|------|
| **Vanilla JavaScript** | 순수 JS (No React/Vue/Angular) |
| **MediaRecorder API** | 브라우저 녹음 (WebM 컨테이너, Opus 코덱) |
| **Fetch API** | AJAX 통신 |
| **Tailwind CSS** | 유틸리티 퍼스트 CSS 프레임워크 |
| **Jinja2 템플릿** | 서버 사이드 렌더링 |

### 3.3 시스템 의존성
| 도구 | 용도 |
|------|------|
| **FFmpeg** | WebM/M4A → WAV 변환 (필수) |
| **PostgreSQL** | 사용자 데이터 및 진행도 저장 |

### 3.4 인프라 (Render.com)
- **Web Service**: Python 3.11 환경
- **Database**: PostgreSQL (Free Tier)
- **Region**: Singapore
- **Build**: apt-get install ffmpeg

---

## 4. 분석 엔진 상세

### 4.1 모음 분석 엔진 (vowel_v2.py)

#### 4.1.1 핵심 알고리즘

```python
# 1. Stable Window Selection (0.12초)
stable_window = find_highest_rms_segment(audio, duration=0.12s)

# 2. F0 (Pitch) Extraction
f0_median = extract_pitch_median(stable_window)
gender = "Male" if f0_median < 165 Hz else "Female"

# 3. Formant Extraction (Praat Burg Algorithm)
formant_object = sound.to_formant_burg(
    time_step=0.01,
    max_number_of_formants=5,
    maximum_formant=5500 (Female) or 5000 (Male),
    window_length=0.025,
    pre_emphasis_from=50.0
)

f1 = formant.get_value_at_time(1, time_point)  # 혀 높이
f2 = formant.get_value_at_time(2, time_point)  # 전후 위치
f3 = formant.get_value_at_time(3, time_point)  # 입술 모양

# 4. Z-score Calculation
z1 = abs(f1 - reference_f1) / reference_f1_sd
z2 = abs(f2 - reference_f2) / reference_f2_sd
z3 = abs(f3 - reference_f3) / reference_f3_sd  # (선택적)

avg_z = (z1 + z2) / 2  # F1, F2만 사용

# 5. Scoring (±2.5σ 기준)
if avg_z <= 2.5:
    score = 100
else:
    penalty = (avg_z - 2.5) * 40  # 40점/σ
    score = max(0, 100 - penalty)
```

#### 4.1.2 참조 데이터 (Reference Formants)

**성인 남성 (Hz)**
| 모음 | F1 | F1 SD | F2 | F2 SD | F3 |
|------|-------|-------|----------|-------|------|
| ㅏ (a) | 651 | 136 | 1156 | 77 | 2500 |
| ㅓ (eo) | 445 | 103 | 845 | 149 | 2500 |
| ㅗ (o) | 320 | 56 | 587 | 132 | 2300 |
| ㅜ (u) | 324 | 43 | 595 | 140 | 2400 |
| ㅡ (eu) | 317 | 27 | 1218 | 155 | 2600 |
| ㅣ (i) | 236 | 30 | 2183 | 136 | 3010 |

**성인 여성 (Hz)**
| 모음 | F1 | F1 SD | F2 | F2 SD | F3 |
|------|-------|-------|----------|-------|------|
| ㅏ (a) | 945 | 83 | 1582 | 141 | 3200 |
| ㅓ (eo) | 576 | 78 | 961 | 87 | 2700 |
| ㅗ (o) | 371 | 25 | 700 | 72 | 2600 |
| ㅜ (u) | 346 | 28 | 810 | 106 | 2700 |
| ㅡ (eu) | 390 | 34 | 1752 | 191 | 2900 |
| ㅣ (i) | 273 | 22 | 2864 | 109 | 3400 |

**출처**: 한국 성인 화자 음성 코퍼스 연구 (추정)

#### 4.1.3 피드백 생성 로직

```python
# F1 피드백 (혀 높이)
if f1 > reference_f1:
    feedback += "Mouth too open / tongue too low → raise tongue slightly."
else:
    feedback += "Mouth too closed / tongue too high → lower tongue slightly."

# F2 피드백 (전후 위치)
if f2 > reference_f2:
    feedback += "Tongue too front → pull it slightly back."
else:
    feedback += "Tongue too back → move it slightly forward."
```

#### 4.1.4 포먼트 플롯 생성

**파일**: `analysis/plot_vowel_space.py`
**출력**: `static/images/analysis/{uuid}.png`

```python
# F1-F2 공간에 타원형 기준 영역 + 사용자 점 표시
plt.scatter(f2_user, f1_user, marker='X', s=200, color='red', label='Your')
ellipse = Ellipse(
    (f2_ref, f1_ref),
    width=2*f2_sd, height=2*f1_sd,
    edgecolor='blue', facecolor='none', linewidth=2
)
plt.gca().add_patch(ellipse)
```

**주의**: Render.com의 ephemeral filesystem에서는 재시작 시 이미지가 삭제됩니다. 프로덕션에서는 S3 또는 Render Disk 사용을 권장합니다.

---

### 4.2 자음 분석 엔진 (consonant.py)

#### 4.2.1 지원 자음 타입

```python
# 1. Stop (파열음): ㄱ, ㄷ, ㅂ, ㄲ, ㄸ, ㅃ, ㅋ, ㅌ, ㅍ
# 2. Fricative (마찰음): ㅅ, ㅆ, ㅎ
# 3. Affricate (파찰음): ㅈ, ㅉ, ㅊ
# 4. Sonorant (공명음): ㄴ, ㄹ, ㅁ
```

#### 4.2.2 측정 특징 (Features)

**파열음 (Stop)**
- `VOT_ms` (Voice Onset Time): 개방부터 유성음 시작까지 시간 (ms)
- `asp_ratio` (Aspiration Ratio): VOT 구간 에너지 / 전체 에너지
- `burst_dB`: 파열 에너지 (dB)

**마찰음 (Fricative)**
- `fric_dur_ms`: 마찰 구간 길이 (ms)
- `centroid_kHz`: 스펙트럼 중심 주파수 (kHz)

**파찰음 (Affricate)**
- VOT + Frication 특징 조합

**공명음 (Sonorant)**
- `seg_dur_ms`: 자음 구간 길이 (ms)
- `nasal_lowFreq_amp`: 저주파 비음 에너지 비율

#### 4.2.3 참조 데이터 예시

```python
reference = {
    "다": {
        "type": "stop",
        "features": {
            "VOT_ms": {
                "male":   (62.9, 27.6),  # (평균, 표준편차)
                "female": (65.2, 23.1),
            },
            "asp_ratio": {
                "male":   (0.16, 0.06),
                "female": (0.18, 0.06),
            },
        },
        "coaching": "혀끝을 윗잇몸 바로 뒤에 대고 막았다가 부드럽게 떼면서..."
    },
    # ... (18개 자음)
}
```

#### 4.2.4 VOT 측정 알고리즘

```python
def estimate_vot_ms(sound, aspirated_mode=False):
    """
    1. Intensity 피크 찾기 (파열 burst)
    2. 이후 pitch 시작점 찾기 (유성음 onset)
    3. VOT = onset_time - burst_time (ms)
    """
    intensity = sound.to_intensity()
    pitch = sound.to_pitch()

    # Burst detection
    burst_time = find_intensity_peak(intensity)

    # Voice onset detection
    if aspirated_mode:
        # 격음: 높은 intensity threshold
        onset_time = find_voiced_onset(pitch, strict=True)
    else:
        # 평음/경음: 낮은 threshold
        onset_time = find_voiced_onset(pitch, strict=False)

    vot_ms = (onset_time - burst_time) * 1000
    return vot_ms, burst_time, onset_time
```

#### 4.2.5 점수 계산

```python
def score_against_reference(measured_feats, ref_feats, sex):
    z_list = []

    for feat_name, (mean, sd) in ref_feats.items():
        measured_val = measured_feats.get(feat_name)
        z = abs((measured_val - mean) / sd)
        z_list.append(min(z, 3.0))  # Cap at 3σ

    avg_z = sum(z_list) / len(z_list)

    if avg_z <= 1.5:
        score = 100
    else:
        penalty = (avg_z - 1.5) * 60  # 60점/σ
        score = max(0, 100 - penalty)

    return score, advice_list
```

#### 4.2.6 수정된 버그 (2025-11-02)

**위치**: `consonant.py:791-795`

**Before**:
```python
if len(z_list) == 0:
    overall_score = None  # ❌ TypeError 발생
```

**After**:
```python
if len(z_list) == 0:
    overall_score = 0.0  # ✅ 안전한 기본값
    advice_list.append("Could not extract enough acoustic features.")
```

---

## 5. API 명세

### 5.1 인증 API

#### POST `/api/auth/signup`
회원가입

**Request Body**:
```json
{
  "username": "string",
  "password": "string"  // ⚠️ 평문 저장 (보안 이슈)
}
```

**Response**:
```json
{
  "ok": true,
  "message": "User created"
}
```

---

#### POST `/api/auth/login`
로그인

**Request Body**:
```json
{
  "username": "string",
  "password": "string"
}
```

**Response**:
```json
{
  "ok": true,
  "message": "Login successful",
  "user": "username",
  "userid": 123,
  "calibration_complete": false
}
```

**Notes**:
- `calibration_complete`: 'a', 'e', 'u' 3개 캘리브레이션 완료 여부

---

#### POST `/api/auth/change-password`
비밀번호 변경

**Request Body**:
```json
{
  "username": "string",
  "new_password": "string"
}
```

---

### 5.2 분석 API

#### POST `/api/analyze-sound`
로그인 사용자 음성 분석 (진행도 저장)

**Request** (multipart/form-data):
```
audio: File (WebM/M4A/MP3)
userid: int
sound: string (한글 음소, 예: "ㅏ", "ㄱ")
```

**Response**:
```json
{
  "userid": 123,
  "sound": "ㅏ",
  "analysis_type": "vowel",
  "score": 85,
  "result": 85,
  "feedback": "Mouth too closed / tongue too high → lower tongue slightly.",
  "details": {
    "symbol": "ㅏ",
    "vowel_key": "a (아)",
    "gender": "Female",
    "formants": {
      "f0": 220.5,
      "f1": 920.3,
      "f2": 1550.2,
      "f3": 2600.1
    },
    "quality_hint": "Good recording quality",
    "reference": {
      "f1": 945,
      "f1_sd": 83,
      "f2": 1582,
      "f2_sd": 141,
      "f3": 3200
    },
    "plot_url": "/static/images/analysis/abc123.png"
  }
}
```

**Side Effect**:
- `progress` 테이블에 점수 업데이트 (기존 최고점보다 높을 때만)

---

#### POST `/api/analyze-sound-guest`
비로그인 사용자 음성 분석

**Request** (multipart/form-data):
```
audio: File
sound: string
```

**Response**: `/api/analyze-sound`와 동일하지만 `userid` 없음

---

### 5.3 캘리브레이션 API

#### POST `/api/calibration`
개인 포먼트 캘리브레이션

**Request** (multipart/form-data):
```
audio: File
sound: string ('a', 'e', 'u' 중 하나)
userid: int
```

**Response**:
```json
{
  "ok": true,
  "message": "Calibration recording for 'a' saved",
  "sound": "a",
  "userid": 123
}
```

**TODO**: 현재는 더미 데이터(f1mean=500, f2mean=1500) 저장. 실제 포먼트 추출 로직 구현 필요 (main.py:445-449).

---

#### GET `/api/formants?userid={id}`
사용자 캘리브레이션 데이터 조회

**Response**:
```json
{
  "userid": 123,
  "formants": {
    "a": {
      "f1_mean": 650.5,
      "f1_std": 80.2,
      "f2_mean": 1200.3,
      "f2_std": 120.5
    },
    "e": { ... },
    "u": { ... }
  }
}
```

---

### 5.4 진행도 API

#### GET `/api/progress?username={name}`
사용자 학습 진행도 조회

**Response**:
```json
{
  "progress": {
    "ㅏ": 85,
    "ㅓ": 70,
    "ㄱ": 90
  }
}
```

---

### 5.5 기타 API

#### GET `/health`
헬스체크

**Response**:
```json
{
  "status": "ok",
  "message": "FastAPI server is running!"
}
```

---

#### GET `/`
메인 페이지 (HTML)

음소 선택 인터페이스 렌더링 (`templates/index.html`)

---

#### GET `/sound?s={symbol}`
음소별 녹음 페이지 (HTML)

`templates/sound.html` 렌더링, 파라미터 `s`로 음소 전달

---

## 6. 데이터베이스 스키마

### 6.1 연결 정보

**Provider**: Render.com PostgreSQL
**Connection String** (main.py:24):
```
postgresql://capstone_itcd_user:2XLTwuuR3pJw4epFlT7lo71WnsmzuDFU@dpg-d411ot1r0fns739sc58g-a.singapore-postgres.render.com/capstone_itcd
```

⚠️ **보안 이슈**: 하드코딩된 상태. 환경 변수로 변경 권장.

---

### 6.2 테이블 구조

#### `users`
사용자 계정 정보

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL  -- ⚠️ 평문 저장 (bcrypt 해싱 필요)
);
```

---

#### `progress`
학습 진행도

```sql
CREATE TABLE progress (
    userid INTEGER REFERENCES users(id) ON DELETE CASCADE,
    sound VARCHAR(10) NOT NULL,    -- 한글 음소 (예: "ㅏ", "ㄱ")
    progress INTEGER NOT NULL,     -- 0-100 점수
    PRIMARY KEY (userid, sound)
);
```

**업데이트 로직** (main.py:490-500):
```sql
-- 새 점수가 기존 최고점보다 높을 때만 업데이트
UPDATE progress SET progress = GREATEST(progress, %s)
WHERE userid = %s AND sound = %s;

-- 레코드 없으면 INSERT
INSERT INTO progress (userid, sound, progress) VALUES (%s, %s, %s);
```

---

#### `formants`
개인 캘리브레이션 데이터

```sql
CREATE TABLE formants (
    userid INTEGER REFERENCES users(id) ON DELETE CASCADE,
    sound VARCHAR(10) NOT NULL,    -- 'a', 'e', 'u'
    f1_mean FLOAT,
    f1_std FLOAT,
    f2_mean FLOAT,
    f2_std FLOAT,
    PRIMARY KEY (userid, sound)
);
```

**용도**: 사용자의 자연스러운 발음 기준선 저장 (향후 개인화 분석에 사용 가능)

---

## 7. 프론트엔드 구조

### 7.1 기술 스택

- **프레임워크**: 없음 (Vanilla JavaScript)
- **템플릿 엔진**: Jinja2 (서버 사이드)
- **CSS**: Tailwind CSS
- **빌드 도구**: 없음 (CDN 사용 추정)

### 7.2 주요 파일

#### `static/scripts/sound.js`
녹음 및 분석 로직 (80줄)

**핵심 코드**:
```javascript
// 1. MediaRecorder 초기화
const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
mediaRecorder = new MediaRecorder(stream);

// 2. 2초 녹음
mediaRecorder.start();
setTimeout(() => mediaRecorder.stop(), 2000);

// 3. Blob → FormData
const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
const formData = new FormData();
formData.append('audio', audioBlob, 'recording.webm');
formData.append('sound', soundSymbol);
formData.append('userid', userId);

// 4. API 호출
const response = await fetch('/api/analyze-sound', {
    method: 'POST',
    body: formData
});

// 5. 결과 표시
const data = await response.json();
updateScoreCard(data.score);
updateFeedback(data.feedback);
if (data.details.plot_url) {
    showFormantPlot(data.details.plot_url);
}
```

---

#### `static/scripts/ui.js`
사용자 인증 및 진행도 UI

**기능**:
- 로그인/회원가입 모달
- 진행도 카드 업데이트
- 캘리브레이션 플로우

---

#### `static/scripts/script.js`
메인 페이지 로직

**기능**:
- 음소 카드 클릭 이벤트
- `/sound?s={symbol}` 라우팅

---

### 7.3 템플릿 구조

#### `templates/base.html`
공통 레이아웃

```html
<!DOCTYPE html>
<html>
<head>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@..." />
</head>
<body>
    {% block content %}{% endblock %}
    <script src="/static/scripts/ui.js"></script>
</body>
</html>
```

---

#### `templates/index.html`
메인 페이지 (음소 선택)

**구조**:
```html
<div class="grid grid-cols-6">
    <div class="card" data-sound="ㅏ">
        <h3>ㅏ</h3>
        <p>Progress: 85%</p>
    </div>
    <!-- 40개 음소 카드 -->
</div>
```

---

#### `templates/sound.html`
녹음 및 분석 페이지

**전달된 컨텍스트** (main.py:307-310):
```python
{
    "request": request,
    "sound": "ㅏ",  # 쿼리 파라미터 's'
    "description": "Say 'a' like 'father'. Tongue low..."
}
```

**UI 컴포넌트**:
- 녹음 버튼 (2초 타이머)
- 분석 결과 카드 (점수, 피드백)
- 포먼트 플롯 (모음만)
- 음향 특징 테이블 (자음만)

---

## 8. 배포 가이드

### 8.1 Render.com 배포 준비

#### 8.1.1 필수 파일 확인

- ✅ `render.yaml`: 인프라 설정
- ✅ `build.sh`: ffmpeg 설치 스크립트
- ✅ `runtime.txt`: `python-3.11.0`
- ✅ `requirements.txt`: Python 의존성
- ✅ `run.sh`: Uvicorn 실행 명령

---

#### 8.1.2 환경 변수 설정

`.env` 파일 (로컬 개발용):
```bash
DATABASE_URL=postgresql://user:pass@host:port/db
HOST=0.0.0.0
PORT=8000
ALLOWED_ORIGINS=*
PLOT_OUTPUT_DIR=static/images/analysis
```

Render 대시보드에서 설정:
- `DATABASE_URL`: 자동 주입 (Database 연결 시)
- `PORT`: 자동 설정
- Custom 환경 변수는 수동 추가

---

#### 8.1.3 배포 절차

**1단계: GitHub 레포지토리 연결**
```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

**2단계: Render Dashboard**
1. New Web Service 생성
2. GitHub 레포지토리 선택
3. Build Command: `./build.sh`
4. Start Command: `./run.sh`
5. Environment: Python 3

**3단계: Database 생성**
1. New PostgreSQL 생성 (Free tier)
2. Web Service에 연결
3. `DATABASE_URL` 자동 주입 확인

**4단계: 배포 확인**
- Health Check: `https://your-app.onrender.com/health`
- 메인 페이지: `https://your-app.onrender.com/`

---

### 8.2 로컬 개발 환경 설정

#### 8.2.1 pyenv 가상환경 사용

```bash
# pyenv 가상환경 활성화
source ~/.pyenv/versions/CAP/bin/activate

# 또는 pyenv-virtualenv 사용
pyenv activate CAP

# 의존성 설치
pip install -r requirements.txt

# ffmpeg 설치 (Ubuntu)
sudo apt install ffmpeg

# 서버 실행
./run.sh
# 또는
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

#### 8.2.2 데이터베이스 마이그레이션

**스키마 생성** (PostgreSQL):
```sql
-- users 테이블
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);

-- progress 테이블
CREATE TABLE progress (
    userid INTEGER REFERENCES users(id) ON DELETE CASCADE,
    sound VARCHAR(10) NOT NULL,
    progress INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (userid, sound)
);

-- formants 테이블
CREATE TABLE formants (
    userid INTEGER REFERENCES users(id) ON DELETE CASCADE,
    sound VARCHAR(10) NOT NULL,
    f1_mean FLOAT,
    f1_std FLOAT,
    f2_mean FLOAT,
    f2_std FLOAT,
    PRIMARY KEY (userid, sound)
);
```

---

### 8.3 프로덕션 체크리스트

#### 보안
- [ ] DB URL을 환경 변수로 변경 (`os.getenv("DATABASE_URL")`)
- [ ] 비밀번호 bcrypt 해싱 구현
- [ ] CORS 설정 제한 (`allow_origins=["https://yourdomain.com"]`)
- [ ] HTTPS 강제 (Render는 자동 제공)
- [ ] API Rate Limiting 추가

#### 성능
- [ ] 포먼트 플롯 저장 위치 변경 (S3 또는 Render Disk)
- [ ] 임시 파일 정리 로직 검증 (cleanup_temp_file)
- [ ] 캐싱 전략 (정적 파일, API 응답)
- [ ] 데이터베이스 인덱스 최적화

#### 모니터링
- [ ] 로깅 설정 (uvicorn --log-level info)
- [ ] 에러 트래킹 (Sentry 등)
- [ ] 분석 실패율 모니터링
- [ ] 서버 리소스 사용량 확인

---

## 9. 알려진 이슈 및 해결책

### 9.1 샘플 데이터 품질 문제

**문제**:
- `sample/vowel_man/` 샘플이 실제로는 여성 음성 (F0: 169~241 Hz)
- 디렉토리명과 불일치로 인한 혼란
- 테스트 점수 저조 (평균 31.5/100)

**영향**:
- 엔진 자체는 정상 작동
- 샘플 데이터로 엔진 품질을 평가할 수 없음

**해결책**:
1. **옵션 A**: 실제 남성 화자의 음성 샘플로 교체
2. **옵션 B**: 디렉토리명을 `vowel_female`로 변경
3. **옵션 C**: 샘플 데이터 무시하고 실사용자 데이터로 검증

---

### 9.2 자음 엔진 None 점수 버그 (수정됨)

**문제**:
- 모든 음향 특징 추출 실패 시 `overall_score = None` 반환
- `TypeError: unsupported format string passed to NoneType.__format__`

**수정**:
- `consonant.py:791-795` 수정
- None 대신 0.0 반환 + 경고 메시지 추가

**커밋**:
```python
# Before
if len(z_list) == 0:
    overall_score = None

# After (2025-11-02)
if len(z_list) == 0:
    overall_score = 0.0
    advice_list.append("Could not extract enough acoustic features.")
```

---

### 9.3 보안 취약점

#### 9.3.1 비밀번호 평문 저장

**위치**: `main.py:332, 341, 363`

**현재 코드**:
```python
# 회원가입
cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)",
            (creds.username, creds.password))  # ❌ 평문

# 로그인
cur.execute("SELECT id FROM users WHERE username = %s AND password = %s",
            (creds.username, creds.password))  # ❌ 평문 비교
```

**해결책**:
```python
import bcrypt

# 회원가입
hashed = bcrypt.hashpw(creds.password.encode('utf-8'), bcrypt.gensalt())
cur.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)",
            (creds.username, hashed.decode('utf-8')))

# 로그인
cur.execute("SELECT id, password_hash FROM users WHERE username = %s", (creds.username,))
user = cur.fetchone()
if user and bcrypt.checkpw(creds.password.encode('utf-8'), user[1].encode('utf-8')):
    # 로그인 성공
```

**의존성 추가**:
```bash
pip install bcrypt
echo "bcrypt" >> requirements.txt
```

---

#### 9.3.2 CORS 전체 허용

**위치**: `main.py:41-47`

**현재 코드**:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ❌ 모든 도메인 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**해결책**:
```python
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # 환경 변수로 제한
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)
```

---

#### 9.3.3 DB URL 하드코딩

**위치**: `main.py:24`

**해결책**:
```python
# Before
DB_URL = "postgresql://capstone_itcd_user:2XLTwuuR3pJw4epFlT7lo71WnsmzuDFU@..."

# After
DB_URL = os.getenv("DATABASE_URL", "postgresql://localhost/kospa_dev")
```

---

### 9.4 Ephemeral Filesystem 이슈

**문제**:
- Render.com의 파일시스템은 재시작 시 초기화됨
- `static/images/analysis/` 에 저장된 포먼트 플롯 삭제됨

**영향**:
- 사용자가 이전 분석 결과 플롯을 볼 수 없음

**해결책**:

**옵션 A: AWS S3 사용**
```python
import boto3

s3_client = boto3.client('s3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

def save_plot_to_s3(plot_path, bucket='kospa-plots'):
    filename = f"analysis/{uuid4().hex}.png"
    s3_client.upload_file(plot_path, bucket, filename)
    return f"https://{bucket}.s3.amazonaws.com/{filename}"
```

**옵션 B: Render Disk**
```yaml
# render.yaml
services:
  - type: web
    disk:
      name: kospa-plots
      mountPath: /opt/render/project/src/static/images/analysis
      sizeGB: 1
```

**옵션 C: 일회성 사용 (현재 구현)**
- 플롯을 세션 내에서만 사용하고 저장하지 않음
- 간단하지만 재방문 시 이력 없음

---

### 9.5 캘리브레이션 미구현

**위치**: `main.py:445-449`

**현재 코드**:
```python
#TODO: analyze the recording and get the formants
f1mean = 500  # ❌ 하드코딩된 더미 데이터
f2mean = 1500
f1std = 100
f2std = 200
```

**해결책**:
```python
from analysis.vowel_v2 import analyze_single_audio

# 오디오 분석
temp_path = save_upload_to_temp(audio)
result, error = analyze_single_audio(temp_path, sound, return_reason=True)

if not error:
    f1mean = result.get('f1')
    f2mean = result.get('f2')
    # 여러 샘플 수집 후 표준편차 계산 필요
    f1std = 100  # 임시값
    f2std = 150  # 임시값
else:
    raise HTTPException(status_code=422, detail=error)

cleanup_temp_file(temp_path)
```

---

## 10. 개발 가이드

### 10.1 엔진 검증 스크립트 사용법

**파일**: `test_engine_validation.py`

**실행**:
```bash
source ~/.pyenv/versions/CAP/bin/activate
python test_engine_validation.py
```

**출력 예시**:
```
======================================================================
  모음 분석 엔진 검증
======================================================================
[a (아)] 분석 중... (sample/vowel_man/아.m4a)
  ✅ 점수: 91.0/100
  👤 성별: Female (F0: 179.2 Hz)
  📊 포먼트:
      F1: 880 Hz (기준: 945 ± 83)
      F2: 1302 Hz (기준: 1582 ± 141)
  ...

======================================================================
  자음 분석 엔진 검증
======================================================================
[ㄱ (가)] 분석 중... (sample/consonant/가.m4a)
  ✅ 점수: 76.6/100
  👤 성별: male (F0: 149.4 Hz)
  📊 음향 특징:
      VOT_ms: 68.2 (기준: 67.1, z=0.05)
  ...
```

---

### 10.2 새 음소 추가 방법

#### 모음 추가

**1단계: 참조 데이터 추가** (`analysis/vowel_v2.py`)
```python
STANDARD_MALE_FORMANTS = {
    # 기존 모음...
    'ae (애)': {'f1': 800, 'f2': 1800, 'f3': 2700, 'f1_sd': 90, 'f2_sd': 120},
}
```

**2단계: 심볼 매핑 추가** (`main.py:49-56`)
```python
VOWEL_SYMBOL_TO_KEY = {
    # 기존 매핑...
    "ㅐ": "ae (애)",
}
```

**3단계: 프론트엔드 카드 추가** (`templates/index.html`)
```html
<div class="card" data-sound="ㅐ">
    <h3>ㅐ</h3>
</div>
```

---

#### 자음 추가

**1단계: 참조 데이터 추가** (`analysis/consonant.py:12-304`)
```python
reference = {
    # 기존 자음...
    "빠": {
        "type": "stop",
        "features": {
            "VOT_ms": {"male": (8.5, 4.0), "female": (9.0, 4.5)},
            "asp_ratio": {"male": (0.08, 0.03), "female": (0.09, 0.03)},
        },
        "coaching": "입술을 단단하게 막고..."
    },
}
```

**2단계: 심볼 매핑 추가** (`main.py:58-77`)
```python
CONSONANT_SYMBOL_TO_SYLLABLE = {
    # 기존 매핑...
    "ㅃ": "빠",
}
```

---

### 10.3 디버깅 팁

#### 음성 분석 실패 시

**1. FFmpeg 설치 확인**
```bash
ffmpeg -version
```

**2. 임시 파일 권한 확인**
```bash
ls -la /tmp/tmp*.wav
```

**3. Parselmouth 버전 확인**
```python
import parselmouth
print(parselmouth.__version__)
```

**4. 로그 활성화**
```bash
uvicorn main:app --log-level debug
```

---

#### 포먼트 추출 실패 시

**원인**:
- 노이즈가 많은 녹음
- 너무 짧은 오디오 (<1초)
- 잘못된 샘플링 레이트

**해결**:
```python
# vowel_v2.py에서 파라미터 조정
formant = sound.to_formant_burg(
    max_number_of_formants=5,  # 3~7로 조정
    maximum_formant=5500,       # 성별에 따라 조정
    window_length=0.025,        # 0.020~0.030
)
```

---

#### 데이터베이스 연결 실패 시

**확인 사항**:
1. PostgreSQL 서버 실행 여부
2. `DATABASE_URL` 환경 변수 설정
3. 네트워크 방화벽 (Render: sslmode=require)

**테스트**:
```python
import psycopg2
conn = psycopg2.connect(os.getenv("DATABASE_URL"), sslmode="require")
print("DB 연결 성공!")
conn.close()
```

---

### 10.4 성능 최적화

#### 분석 속도 개선

**현재 처리 시간**:
- 모음 분석: ~1-2초
- 자음 분석: ~2-3초 (VOT 측정 복잡)

**최적화 방법**:
1. **병렬 처리** (여러 샘플 동시 분석)
```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(analyze_single_audio, path, key)
               for path, key in samples]
    results = [f.result() for f in futures]
```

2. **캐싱** (동일 오디오 재분석 방지)
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def analyze_cached(audio_hash, vowel_key):
    return analyze_single_audio(audio_path, vowel_key)
```

3. **Praat 파라미터 최적화**
```python
# 처리 속도 우선
pitch = sound.to_pitch(time_step=0.02)  # 0.01 → 0.02 (2배 빠름)
```

---

### 10.5 테스트 작성

#### 유닛 테스트 예시 (`tests/test_vowel_engine.py`)

```python
import pytest
from analysis.vowel_v2 import analyze_single_audio

def test_vowel_analysis_normal_case():
    result, error = analyze_single_audio("sample/vowel_man/아.wav", "a (아)")
    assert error is None
    assert result["score"] >= 0
    assert result["score"] <= 100
    assert "f1" in result
    assert "f2" in result

def test_vowel_analysis_invalid_file():
    result, error = analyze_single_audio("nonexistent.wav", "a (아)")
    assert error is not None

def test_gender_detection():
    result, error = analyze_single_audio("sample/vowel_man/아.wav", "a (아)")
    assert result["gender"] in ["Male", "Female"]
```

**실행**:
```bash
pip install pytest
pytest tests/
```

---

## 부록

### A. 용어 사전

| 용어 | 설명 |
|------|------|
| **Formant** | 성도의 공명 주파수. F1(혀 높이), F2(전후 위치), F3(입술 모양) |
| **VOT** | Voice Onset Time. 파열음 개방부터 유성음 시작까지 시간 |
| **Z-score** | 표준편차 단위로 표준값과의 차이를 나타냄. `(측정값 - 평균) / 표준편차` |
| **Aspiration** | 기식. 격음(ㅋ, ㅌ, ㅍ)에서 나는 거친 숨소리 |
| **Frication** | 마찰. ㅅ, ㅆ, ㅎ에서 공기가 좁은 틈을 통과하며 나는 소리 |
| **Parselmouth** | Python용 Praat 래퍼 라이브러리 |
| **Praat** | 음성학 분석 소프트웨어 (암스테르담 대학교 개발) |

---

### B. 참고 자료

- **Praat Documentation**: https://www.fon.hum.uva.nl/praat/
- **Parselmouth**: https://parselmouth.readthedocs.io/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Render.com Docs**: https://render.com/docs

---

### C. 라이선스 및 기여

**프로젝트 라이선스**: MIT (추정, 명시 필요)

**기여자**:
- 음성 분석 엔진: [분석 엔진 개발자]
- 프론트엔드: [프론트엔드 개발자]
- 문서화: Claude Code (2025-11-02)

**기여 방법**:
1. Fork this repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

**문서 버전**: 1.0.0
**최종 업데이트**: 2025-11-02
**작성자**: KoSPA Development Team
