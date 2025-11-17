#!/bin/bash
# ngrok 빠른 설치 스크립트

set -e

echo "🚀 ngrok 설치 중..."
echo ""

# ngrok 다운로드
cd /tmp
wget -q https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz

# 압축 해제
tar xzf ngrok-v3-stable-linux-amd64.tgz

# 이동
sudo mv ngrok /usr/local/bin/

# 정리
rm ngrok-v3-stable-linux-amd64.tgz

echo "✅ ngrok 설치 완료!"
echo ""

# 버전 확인
ngrok version

echo ""
echo "📝 다음 단계:"
echo "1. https://dashboard.ngrok.com/get-started/your-authtoken 에서 토큰 받기"
echo "2. ngrok config add-authtoken YOUR_TOKEN"
echo "3. 서버 실행: ./run.sh"
echo "4. 새 터미널에서: ngrok http 8000"
echo ""
echo "💡 또는 간단하게: ./start_mobile_demo.sh"
