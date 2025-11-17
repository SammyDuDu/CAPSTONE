#!/bin/bash
# 서버 동작 빠른 확인 스크립트

echo "=== KoSPA 서버 상태 확인 ==="
echo ""

# Health check
echo "1. Health Check:"
curl -s http://localhost:8000/health | python3 -m json.tool
echo ""

# 메인 페이지
echo "2. 메인 페이지 확인:"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/)
if [ "$STATUS" = "200" ]; then
    echo "✅ 메인 페이지 정상 (HTTP $STATUS)"
else
    echo "❌ 메인 페이지 오류 (HTTP $STATUS)"
fi
echo ""

# Sound 페이지
echo "3. Sound 페이지 확인:"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/sound?s=ㅏ")
if [ "$STATUS" = "200" ]; then
    echo "✅ Sound 페이지 정상 (HTTP $STATUS)"
else
    echo "❌ Sound 페이지 오류 (HTTP $STATUS)"
fi
echo ""

echo "=== 완료 ==="
echo "브라우저에서 http://localhost:8000 접속하세요!"
