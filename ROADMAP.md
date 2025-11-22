# KoSPA 개발 로드맵

## 현재 상태: Stage 2 완료 ✅

### ✅ Stage 1: 기본 음소 분석 (완료)
- [x] 모음 6개 분석 (ㅏ, ㅓ, ㅗ, ㅜ, ㅡ, ㅣ)
- [x] 자음 18개 분석 (평음/경음/격음)
- [x] 포먼트 기반 점수 계산
- [x] VOT/Aspiration/Frication 측정
- [x] 실시간 피드백 생성

### ✅ Stage 2: 시스템 안정화 (완료)
- [x] Race Condition 버그 수정
- [x] 성별 임계값 통일
- [x] 모바일 지원 (ngrok)
- [x] 배포 준비 (Render.com)
- [x] 문서화

---

## 🚧 Stage 3: 데이터 수집 & 통계 개선

### 목표
실제 사용자 데이터로 참조값(mean/std) 업데이트하여 정확도 향상

### 3.1 데이터 수집 시스템

#### 필요한 기능
```python
# 1. 사용자 녹음 저장
POST /api/submit-recording
- userid, sound, audio_file
- 서버에 WAV 파일 저장 (또는 S3)
- metadata 저장 (F0, F1, F2, F3, gender, score)

# 2. 통계 계산
- 음소별 N >= 30개 샘플 수집
- mean, std 자동 계산
- 이상치(outlier) 제거 (±3σ 초과)

# 3. 참조값 업데이트
- analysis/config.py에 새 통계 반영
- A/B 테스트로 개선 효과 검증
```

#### 데이터베이스 스키마 추가
```sql
CREATE TABLE recordings (
    id SERIAL PRIMARY KEY,
    userid INTEGER REFERENCES users(id),
    sound VARCHAR(10),           -- "ㅏ", "ㄱ" 등
    audio_path TEXT,             -- S3 URL 또는 로컬 경로
    f0 FLOAT,
    f1 FLOAT,
    f2 FLOAT,
    f3 FLOAT,
    gender VARCHAR(10),
    score INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    is_outlier BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_recordings_sound ON recordings(sound);
CREATE INDEX idx_recordings_gender ON recordings(gender);
```

#### 통계 업데이트 스크립트
```python
# scripts/update_statistics.py

from sqlalchemy import create_engine
import pandas as pd
import numpy as np

def update_formant_statistics(sound, gender):
    """
    특정 음소의 통계값 업데이트
    """
    # 1. 데이터 로드 (N >= 30)
    query = f"""
        SELECT f1, f2, f3
        FROM recordings
        WHERE sound = '{sound}'
          AND gender = '{gender}'
          AND is_outlier = FALSE
    """
    df = pd.read_sql(query, engine)

    if len(df) < 30:
        print(f"❌ {sound} ({gender}): 샘플 부족 ({len(df)}/30)")
        return None

    # 2. 이상치 제거 (±3σ)
    for col in ['f1', 'f2', 'f3']:
        mean = df[col].mean()
        std = df[col].std()
        df = df[np.abs(df[col] - mean) <= 3 * std]

    # 3. 통계 계산
    stats = {
        'f1': df['f1'].mean(),
        'f1_sd': df['f1'].std(),
        'f2': df['f2'].mean(),
        'f2_sd': df['f2'].std(),
        'f3': df['f3'].mean(),
        'f3_sd': df['f3'].std(),
    }

    print(f"✅ {sound} ({gender}): N={len(df)}")
    print(f"   F1: {stats['f1']:.0f} ± {stats['f1_sd']:.0f} Hz")
    print(f"   F2: {stats['f2']:.0f} ± {stats['f2_sd']:.0f} Hz")

    return stats

# 4. config 파일 자동 생성
def generate_config_file(all_stats):
    """
    analysis/formant_data.py 자동 생성
    """
    with open('analysis/formant_data.py', 'w') as f:
        f.write("# Auto-generated from user data\n")
        f.write("# Last updated: {datetime.now()}\n\n")
        f.write("UPDATED_MALE_FORMANTS = {\n")
        for sound, stats in all_stats['male'].items():
            f.write(f"    '{sound}': {stats},\n")
        f.write("}\n\n")
        # ... Female도 동일
```

#### API 엔드포인트 추가
```python
# main.py

@app.post("/api/submit-recording")
async def submit_recording(
    userid: int,
    sound: str,
    audio: UploadFile
):
    """
    사용자 녹음을 서버에 저장하고 통계에 반영
    """
    # 1. 분석
    result = await analyse_uploaded_audio(audio, sound)

    # 2. 저장
    audio_path = save_to_s3(audio)  # 또는 로컬

    with connect(DB_URL) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO recordings
            (userid, sound, audio_path, f0, f1, f2, f3, gender, score)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            userid, sound, audio_path,
            result['f0'], result['f1'], result['f2'], result['f3'],
            result['gender'], result['score']
        ))
        conn.commit()

    return {"ok": True, "message": "Recording saved for statistics"}
```

### 3.2 구현 우선순위

**Phase 1: 데이터 수집 (1~2주)**
- [ ] recordings 테이블 생성
- [ ] /api/submit-recording 엔드포인트
- [ ] 프론트엔드: "통계 제공 동의" 체크박스
- [ ] 최소 30개/음소 수집

**Phase 2: 통계 분석 (1주)**
- [ ] 이상치 제거 로직
- [ ] update_statistics.py 스크립트
- [ ] A/B 테스트 준비

**Phase 3: 배포 (1주)**
- [ ] 새 통계값 적용
- [ ] 점수 개선 효과 측정
- [ ] 사용자 피드백 수집

---

## 🤖 Stage 4: 단어 수준 분석 (LLM 활용)

### 목표
단어/문장 발음을 분석하고 자연스러운 피드백 제공

### 4.1 왜 LLM이 필요한가?

#### 기존 음소 분석의 한계
```
사용자: "안녕하세요" 발음
→ 현재: 각 음소별 점수만 제공
   ㅇ: 85점, ㅏ: 90점, ㄴ: 80점, ...

→ 문제점:
   - 연음 법칙 (안녕 → [안녕])
   - 억양/강세 무시
   - 자연스러움 평가 불가
```

#### LLM으로 해결 가능한 것
1. **음운 변화 인식**
   - "국물" → [궁물] (비음화)
   - "놓고" → [노코] (격음화)
   - LLM이 "예상 발음"과 "실제 발음" 비교

2. **자연스러움 평가**
   ```python
   # Whisper로 STT
   transcription = whisper.transcribe("안녕하세요.wav")
   # → "안녕하세요"

   # GPT로 평가
   prompt = f"""
   Target: 안녕하세요
   Actual: {transcription}

   1. Pronunciation accuracy (0-100)
   2. Natural flow (0-100)
   3. Specific feedback in Korean
   """

   feedback = openai.chat.completions.create(
       model="gpt-4",
       messages=[{"role": "user", "content": prompt}]
   )
   ```

3. **맥락 기반 피드백**
   - "배우고 있어요" → 격식체/비격식체 구분
   - 상황에 맞는 억양 제안

### 4.2 아키텍처 설계

```
┌─────────────────────────────────────────┐
│  User: "안녕하세요" 녹음 (3~5초)         │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  Stage 1: 음소 분석 (기존 엔진)          │
│  - 각 음소별 점수                        │
│  - 포먼트/VOT 측정                       │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  Stage 2: STT (Whisper API)             │
│  - 음성 → 텍스트 변환                   │
│  - 발음 오류 감지                        │
│    Input: audio.wav                     │
│    Output: "안녕하세요" (confidence)     │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  Stage 3: LLM 분석 (GPT-4)              │
│  - 음운 규칙 적용 여부 확인              │
│  - 억양/강세 평가                        │
│  - 자연스러운 피드백 생성                │
└────────────┬────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────┐
│  Output: 종합 피드백                     │
│  - 음소 점수: 85/100                    │
│  - 단어 점수: 90/100                    │
│  - 피드백: "연음이 자연스럽습니다.       │
│    다만 '하세요'의 강세를 조금 더..."   │
└─────────────────────────────────────────┘
```

### 4.3 LLM 통합 방법

#### 옵션 A: OpenAI API (추천)
```python
import openai

async def analyze_word_pronunciation(
    audio_path: str,
    target_text: str,
    phoneme_scores: dict
):
    # 1. Whisper STT
    with open(audio_path, "rb") as audio:
        transcription = openai.Audio.transcribe(
            model="whisper-1",
            file=audio,
            language="ko"
        )

    # 2. GPT-4 평가
    prompt = f"""
    You are a Korean pronunciation expert.

    Target phrase: {target_text}
    User said: {transcription.text}
    Phoneme scores: {phoneme_scores}

    Analyze:
    1. Phonological rules applied correctly? (연음, 비음화 등)
    2. Natural intonation? (억양)
    3. Overall fluency score (0-100)
    4. Specific feedback in Korean (2-3 sentences)

    Output JSON format:
    {{
        "word_score": 85,
        "intonation_score": 80,
        "fluency_score": 90,
        "feedback": "...",
        "phonological_rules": ["연음: 정확", "비음화: 부족"]
    }}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )

    return json.loads(response.choices[0].message.content)
```

**장점**:
- ✅ 한국어 특화 (Whisper 한국어 성능 우수)
- ✅ 구현 간단
- ✅ 확장성 좋음

**단점**:
- ❌ API 비용 (Whisper $0.006/분, GPT-4 $0.03/1K tokens)
- ❌ 레이턴시 2~5초

#### 옵션 B: 로컬 LLM (Llama 3.1 + Whisper)
```python
from transformers import pipeline

# Whisper 로컬
whisper = pipeline("automatic-speech-recognition",
                   model="openai/whisper-large-v3")

# Llama 3.1 로컬
llm = pipeline("text-generation",
               model="meta-llama/Llama-3.1-8B-Instruct")

transcription = whisper(audio_path)
feedback = llm(prompt)
```

**장점**:
- ✅ 무료
- ✅ 프라이버시 보호
- ✅ 오프라인 가능

**단점**:
- ❌ GPU 필요 (최소 16GB VRAM)
- ❌ 한국어 성능 OpenAI보다 낮음
- ❌ 관리 복잡

#### 옵션 C: 하이브리드
```python
# 음소 분석: 로컬 (무료, 빠름)
phoneme_result = vowel_v2.analyze_single_audio(...)

# 단어 분석: OpenAI API (정확, 유료)
if user.premium or demo_mode:
    word_result = analyze_with_openai(...)
else:
    word_result = None  # 기본 사용자는 음소만
```

### 4.4 비용 추정

#### OpenAI API 비용 (단어 분석 1회)
```
- Whisper: 5초 오디오 → $0.0005
- GPT-4: 500 tokens → $0.015
- 총: ~$0.0155/요청

월 1,000명 × 10회 = 10,000 요청
→ $155/월
```

#### 무료 Tier로 제한
```python
# 사용자별 제한
if user.word_analysis_count < 10:  # 월 10회 무료
    result = analyze_with_openai(...)
    user.word_analysis_count += 1
else:
    return {"error": "월 무료 할당량 초과. 프리미엄 가입 필요"}
```

### 4.5 구현 로드맵

**Phase 1: POC (2주)**
- [ ] OpenAI API 연동
- [ ] 5개 샘플 단어로 테스트
  - "안녕하세요"
  - "감사합니다"
  - "죄송합니다"
  - "맛있어요"
  - "좋아요"
- [ ] 정확도 검증

**Phase 2: 프로토타입 (2주)**
- [ ] 프론트엔드 UI (단어 선택 페이지)
- [ ] 음소 + 단어 결과 통합 표시
- [ ] 무료/프리미엄 Tier 구분

**Phase 3: 프로덕션 (1주)**
- [ ] 비용 모니터링
- [ ] 에러 핸들링
- [ ] 사용자 피드백 수집

---

## 📊 전체 타임라인

```
현재 (2025-11)
    |
    ├─ Stage 2 완료 ✅
    |   - 데모 성공
    |   - 모바일 지원
    |
    ├─ Stage 3: 데이터 수집 (1개월)
    |   Week 1-2: 수집 시스템 구축
    |   Week 3-4: 30개/음소 수집
    |
    ├─ Stage 3.5: 통계 업데이트 (1주)
    |   - 이상치 제거
    |   - 새 통계값 배포
    |
    └─ Stage 4: LLM 통합 (1.5개월)
        Week 1-2: POC
        Week 3-4: 프로토타입
        Week 5-6: 프로덕션
```

---

## 🎯 즉시 해야 할 것

### 우선순위 1: 데이터 수집 시작
```sql
-- 1. DB 스키마 추가
CREATE TABLE recordings (...);

-- 2. API 엔드포인트 추가
POST /api/submit-recording

-- 3. 프론트엔드: 동의 체크박스
"분석 데이터를 연구 목적으로 사용하는 것에 동의합니다"
```

### 우선순위 2: LLM POC
```python
# 간단한 테스트
import openai

openai.api_key = "sk-..."

response = openai.Audio.transcribe(
    model="whisper-1",
    file=open("sample/vowel_man/아.m4a", "rb")
)

print(response.text)  # "아"
```

---

## 💡 추천 전략

### 단기 (이번 학기 내)
1. **데이터 수집 시작** → 통계 개선
2. **LLM POC** → 5개 단어로 가능성 검증

### 중기 (다음 학기)
1. 단어 분석 정식 출시
2. 프리미엄 모델 도입 ($5/월)

### 장기 (논문/취업)
1. 논문: "LLM-based Korean Pronunciation Feedback System"
2. 포트폴리오: 실사용자 1,000명+

---

**질문**:
1. Stage 3 데이터 수집부터 시작할까요?
2. LLM POC를 먼저 해볼까요?
3. 둘 다 병행?

어떤 방향으로 진행하고 싶으신가요?
