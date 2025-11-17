# 📱 핸드폰 데모 빠른 시작

## 🚀 가장 빠른 방법 (3단계)

### 1️⃣ ngrok 설치 (최초 1회만)
```bash
./setup_ngrok.sh
```

### 2️⃣ 토큰 설정 (최초 1회만)
1. https://dashboard.ngrok.com/signup 가입 (무료)
2. https://dashboard.ngrok.com/get-started/your-authtoken 접속
3. 토큰 복사
```bash
ngrok config add-authtoken YOUR_TOKEN_HERE
```

### 3️⃣ 데모 시작!
```bash
./start_mobile_demo.sh
```

화면에 나오는 URL을 핸드폰 브라우저에 입력!

---

## 💡 더 간단한 방법 (같은 Wi-Fi)

ngrok 없이 바로 시작:

```bash
# 1. 서버 실행
source ~/.pyenv/versions/CAP/bin/activate
./run.sh

# 2. IP 확인
hostname -I

# 3. 핸드폰에서 접속
# http://YOUR_IP:8000
# 예: http://192.168.0.105:8000
```

**주의**: PC와 핸드폰이 **같은 Wi-Fi**에 연결되어야 함!

---

## 🛑 종료

```bash
./stop_mobile_demo.sh
```

---

## 🔧 문제 해결

### "연결할 수 없음"
```bash
# 방화벽 확인
sudo ufw allow 8000

# 서버 재시작
./stop_mobile_demo.sh
./start_mobile_demo.sh
```

### "마이크가 작동하지 않음"
- 핸드폰 브라우저에서 **마이크 권한 허용** 필요
- Chrome/Safari 사용 권장

---

## 📊 데모 팁

1. **조용한 곳**에서 녹음
2. **마이크에 가까이** 대고 녹음
3. **2초 동안** 안정적으로 발음
4. 점수 낮으면 **재녹음**으로 개선 효과 보여주기!

---

**데모 성공을 기원합니다!** 🎉
