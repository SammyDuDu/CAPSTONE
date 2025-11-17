#!/bin/bash
# 데모 서버 종료 스크립트

echo "🛑 KoSPA 모바일 데모 종료 중..."
echo ""

# 서버 종료
if [ -f .server.pid ]; then
    SERVER_PID=$(cat .server.pid)
    if ps -p $SERVER_PID > /dev/null 2>&1; then
        echo "🔴 서버 종료 (PID: $SERVER_PID)"
        kill $SERVER_PID
    fi
    rm .server.pid
fi

# ngrok 종료
if [ -f .ngrok.pid ]; then
    NGROK_PID=$(cat .ngrok.pid)
    if ps -p $NGROK_PID > /dev/null 2>&1; then
        echo "🔴 ngrok 종료 (PID: $NGROK_PID)"
        kill $NGROK_PID
    fi
    rm .ngrok.pid
fi

# 혹시 남은 프로세스 정리
pkill -f "uvicorn main:app" 2>/dev/null || true
pkill -f "ngrok http" 2>/dev/null || true

# 로그 파일 정리 (선택)
# rm -f server.log ngrok.log

echo ""
echo "✅ 모든 서비스 종료 완료"
