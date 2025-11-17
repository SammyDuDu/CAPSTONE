# 핸드폰에서 KoSPA 데모하기

핸드폰에서 접속하려면 외부에서 접근 가능한 URL이 필요합니다.
데모 환경에 따라 3가지 방법 중 선택하세요.

---

## 🚀 방법 1: ngrok (가장 쉬움, 추천!)

### 장점
- ✅ 설치 간단 (5분)
- ✅ HTTPS 자동 지원
- ✅ 방화벽 설정 불필요
- ✅ 공개 URL 즉시 생성

### 단점
- ⚠️ 무료 플랜: 세션 2시간 제한
- ⚠️ URL이 매번 바뀜

---

### 1-1. ngrok 설치

```bash
# 방법 A: snap으로 설치 (Ubuntu)
sudo snap install ngrok

# 방법 B: 직접 다운로드
cd ~
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar xvzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/
```

### 1-2. ngrok 계정 설정 (선택, 무료)

```bash
# https://dashboard.ngrok.com/get-started/setup 에서 가입
# authtoken 받기

ngrok config add-authtoken YOUR_TOKEN_HERE
```

### 1-3. KoSPA 서버 실행 (터미널 1)

```bash
cd /home/woong/CAPSTONE
source ~/.pyenv/versions/CAP/bin/activate
./run.sh
```

서버가 `http://0.0.0.0:8000` 에서 실행 중이어야 함.

### 1-4. ngrok 터널 시작 (터미널 2)

```bash
ngrok http 8000
```

### 1-5. 출력된 URL 확인

```
ngrok

Session Status                online
Account                       your-email@example.com
Version                       3.x.x
Region                        Asia Pacific (ap)
Latency                       -
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123.ngrok-free.app -> http://localhost:8000

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

**핸드폰에서 접속**: `https://abc123.ngrok-free.app`

---

## 📱 방법 2: 같은 Wi-Fi 네트워크 (로컬 네트워크)

### 장점
- ✅ 설정 가장 간단
- ✅ 인터넷 연결 불필요
- ✅ 빠른 속도

### 단점
- ⚠️ 같은 Wi-Fi에 연결되어야 함
- ⚠️ 외부 인터넷에서 접속 불가

---

### 2-1. 서버 PC의 IP 확인

```bash
# WSL에서 실행 중이라면
ip addr show eth0 | grep "inet " | awk '{print $2}' | cut -d/ -f1

# 또는
hostname -I | awk '{print $1}'

# Windows IP 확인 (WSL 외부)
ipconfig | grep "IPv4"
```

출력 예시: `192.168.0.105`

### 2-2. 서버 실행

```bash
cd /home/woong/CAPSTONE
source ~/.pyenv/versions/CAP/bin/activate

# 0.0.0.0으로 바인딩 (중요!)
./run.sh
```

### 2-3. 핸드폰에서 접속

**핸드폰과 PC가 같은 Wi-Fi에 연결된 상태에서**:

```
http://192.168.0.105:8000
```

### 2-4. 안되면 방화벽 확인

**Ubuntu/WSL**:
```bash
# 방화벽 8000 포트 열기
sudo ufw allow 8000
```

**Windows 방화벽** (WSL 사용 시):
1. Windows 보안 → 방화벽 및 네트워크 보호
2. 고급 설정 → 인바운드 규칙 → 새 규칙
3. 포트 → TCP → 8000 → 허용

---

## ☁️ 방법 3: Render.com 배포 (프로덕션용)

### 장점
- ✅ 24시간 접속 가능
- ✅ 영구 URL
- ✅ HTTPS 자동
- ✅ 전 세계 어디서나 접속

### 단점
- ⚠️ 첫 배포 시간: 10~15분
- ⚠️ Free tier: cold start 지연

---

### 3-1. GitHub에 푸시

```bash
cd /home/woong/CAPSTONE
git add .
git commit -m "Add Render deployment configs"
git push origin main
```

### 3-2. Render 배포

1. https://render.com 가입/로그인
2. New → Web Service
3. GitHub 레포지토리 연결
4. 설정:
   - **Build Command**: `./build.sh`
   - **Start Command**: `./run.sh`
   - **Environment**: Python 3
5. Create Web Service

### 3-3. 배포 완료 대기 (10분)

```
Building... ✓
Deploying... ✓
Live at: https://kospa.onrender.com
```

### 3-4. 핸드폰에서 접속

```
https://kospa.onrender.com
```

---

## 🎯 데모 상황별 추천

### 당장 오늘/내일 데모 → **ngrok** 🚀
```bash
# 터미널 1
./run.sh

# 터미널 2
ngrok http 8000

# 핸드폰에서 https://xxxx.ngrok-free.app 접속
```

**소요 시간**: 5분

---

### 같은 장소에서 데모 → **로컬 네트워크** 📱
```bash
# IP 확인
hostname -I

# 서버 실행
./run.sh

# 핸드폰에서 http://192.168.x.x:8000 접속
```

**소요 시간**: 2분

---

### 며칠 후 정식 발표 → **Render.com** ☁️
```bash
# GitHub 푸시
git push

# Render 대시보드에서 배포
# 완료되면 https://kospa.onrender.com
```

**소요 시간**: 15분 (첫 배포)

---

## 🛠️ 트러블슈팅

### ngrok 사용 시

**문제**: "ERR_NGROK_108"
```bash
# authtoken 설정 필요
ngrok config add-authtoken YOUR_TOKEN
```

**문제**: "Failed to start tunnel"
```bash
# 포트 충돌 확인
lsof -i :8000
kill -9 <PID>
```

---

### 로컬 네트워크 사용 시

**문제**: 핸드폰에서 연결 안 됨
```bash
# 1. 방화벽 확인
sudo ufw status
sudo ufw allow 8000

# 2. 0.0.0.0으로 바인딩 확인
# run.sh에서 HOST=0.0.0.0 인지 확인

# 3. IP 주소 재확인
ip addr | grep inet
```

**문제**: "사이트에 연결할 수 없음"
- PC와 핸드폰이 **같은 Wi-Fi**인지 확인
- 핸드폰이 **모바일 데이터**가 아닌 **Wi-Fi** 사용 중인지 확인

---

### Render 배포 시

**문제**: "Build failed"
```bash
# build.sh 권한 확인
chmod +x build.sh run.sh

# ffmpeg 설치 확인 (build.sh에 포함됨)
cat build.sh | grep ffmpeg
```

**문제**: "Application error"
```bash
# Render 로그 확인
# Dashboard → Logs에서 에러 메시지 확인

# DB_URL 환경 변수 설정 확인
# Dashboard → Environment → DATABASE_URL
```

---

## 📝 데모 체크리스트

### 데모 30분 전
- [ ] 서버 실행 확인 (`./run.sh`)
- [ ] ngrok 터널 시작 (또는 IP 확인)
- [ ] URL 복사 (QR코드 생성 권장)
- [ ] 핸드폰에서 접속 테스트
- [ ] 마이크 권한 허용 확인

### QR 코드 생성 (선택)
```bash
# qrencode 설치
sudo apt install qrencode

# QR 코드 생성
qrencode -o qr.png "https://abc123.ngrok-free.app"

# 이미지 확인
xdg-open qr.png
```

핸드폰에서 QR 코드 스캔 → 바로 접속!

---

## 💡 추가 팁

### HTTPS 인증서 경고 무시 (ngrok)
- ngrok 무료 플랜은 경고 화면이 나올 수 있음
- "Visit Site" 클릭하면 됨

### 핸드폰 마이크 권한
- 브라우저에서 "마이크 허용" 팝업에 **반드시 허용**
- 차단했다면: 브라우저 설정 → 사이트 권한 → 마이크 → 허용

### 데이터 사용량 절약
- 로컬 Wi-Fi 사용 시 데이터 사용 안 함
- ngrok/Render 사용 시 약간의 데이터 사용 (음성 파일 2초 ≈ 50KB)

---

**데모 성공을 기원합니다!** 🚀
