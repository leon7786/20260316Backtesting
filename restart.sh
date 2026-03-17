#!/bin/bash
# 可靠重启 Flask 服务
PORT=5005
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="/tmp/backtest_app.log"

# 1. 找到占用端口的进程并强杀
PID=$(ss -tlnp | grep ":${PORT}" | grep -oP 'pid=\K[0-9]+')
if [ -n "$PID" ]; then
    echo "Killing old process PID=$PID on port $PORT..."
    kill -9 "$PID" 2>/dev/null
    sleep 1
fi

# 2. 确认端口释放
if ss -tlnp | grep -q ":${PORT}"; then
    echo "ERROR: Port $PORT still in use!"
    exit 1
fi

# 3. 启动新进程
cd "$APP_DIR"
nohup python3 src/app.py >> "$LOG" 2>&1 &
NEW_PID=$!
echo "Started new process PID=$NEW_PID"

# 4. 等待并验证
sleep 2
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${PORT}/ 2>/dev/null)
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Service running on port $PORT (HTTP $HTTP_CODE)"
else
    echo "❌ Service failed (HTTP $HTTP_CODE), check $LOG"
    tail -5 "$LOG"
fi
