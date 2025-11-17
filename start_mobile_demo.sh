#!/bin/bash
# 핸드폰 데모용 원클릭 실행 스크립트

echo "📱 KoSPA 모바일 데모 시작"
echo "================================"
echo ""

# 1. pyenv 활성화 확인
if [ -z "$VIRTUAL_ENV" ]; then
    echo "🔧 가상환경 활성화 중..."
    source ~/.pyenv/versions/CAP/bin/activate
fi

# 2. 서버 실행 (백그라운드)
echo "🚀 서버 시작 중..."
nohup ./run.sh > server.log 2>&1 &
SERVER_PID=$!

sleep 3

# 3. 서버 확인
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ 서버 정상 실행 (PID: $SERVER_PID)"
else
    echo "❌ 서버 실행 실패"
    exit 1
fi

echo ""
echo "================================"
echo "📱 핸드폰 접속 방법"
echo "================================"
echo ""

# ngrok 있으면 자동 실행
if command -v ngrok &> /dev/null; then
    echo "🌐 ngrok 터널 시작 중..."
    echo ""

    # ngrok을 백그라운드에서 실행하고 URL 추출
    nohup ngrok http 8000 --log=stdout > ngrok.log 2>&1 &
    NGROK_PID=$!

    sleep 3

    # ngrok URL 추출
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o '"public_url":"https://[^"]*' | grep -o 'https://[^"]*' | head -1)

    if [ -n "$NGROK_URL" ]; then
        echo "✅ 공개 URL: $NGROK_URL"
        echo ""
        echo "📱 핸드폰에서 위 URL을 브라우저에 입력하세요!"
        echo ""

        # QR 코드 생성 (qrencode 있으면)
        if command -v qrencode &> /dev/null; then
            qrencode -t ansiutf8 "$NGROK_URL"
            echo ""
            echo "📷 위 QR 코드를 핸드폰으로 스캔하세요!"
        fi

        echo ""
        echo "🔗 ngrok 대시보드: http://localhost:4040"
    else
        echo "⚠️  ngrok URL을 가져올 수 없습니다."
        echo "    수동으로 확인: http://localhost:4040"
    fi
else
    # ngrok 없으면 로컬 IP 안내
    echo "⚠️  ngrok이 설치되지 않았습니다."
    echo ""
    echo "방법 1: 같은 Wi-Fi에서 접속"
    echo "---------------------------------"

    # IP 주소 확인
    LOCAL_IP=$(hostname -I | awk '{print $1}')

    if [ -n "$LOCAL_IP" ]; then
        echo "📱 핸드폰 브라우저에 입력: http://$LOCAL_IP:8000"
        echo ""

        if command -v qrencode &> /dev/null; then
            qrencode -t ansiutf8 "http://$LOCAL_IP:8000"
            echo ""
            echo "📷 위 QR 코드를 핸드폰으로 스캔하세요!"
        fi
    else
        echo "❌ IP 주소를 찾을 수 없습니다."
        echo "   수동 확인: ip addr | grep inet"
    fi

    echo ""
    echo "방법 2: ngrok 설치 (추천)"
    echo "---------------------------------"
    echo "chmod +x setup_ngrok.sh && ./setup_ngrok.sh"
fi

echo ""
echo "================================"
echo "⚠️  종료하려면: ./stop_mobile_demo.sh"
echo "================================"

# PID 저장
echo $SERVER_PID > .server.pid
if [ -n "$NGROK_PID" ]; then
    echo $NGROK_PID > .ngrok.pid
fi
