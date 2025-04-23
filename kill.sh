#!/bin/bash

PROCESS_NAME="python.*createVideoWithComfyUIAPI/main.py.*"

# 查找进程PID
# ps aux列出所有进程，grep查找指定进程，排除grep本身，awk提取PID列
PIDS=$(ps aux | grep -E "$PROCESS_NAME" | grep -v "grep" | awk '{print $2}')

# 检查是否找到进程
if [ -z "$PIDS" ]; then
    echo "未找到进程: $PROCESS_NAME"
    exit 1
fi

# 循环杀掉所有匹配的进程
for PID in $PIDS; do
    # 检查PID是否有效
    if [ -n "$PID" ] && [[ "$PID" =~ ^[0-9]+$ ]]; then
        echo "正在杀死进程 $PROCESS_NAME (PID: $PID)..."
        kill -9 "$PID"
        
        # 检查是否成功杀死
        if [ $? -eq 0 ]; then
            echo "成功杀死进程 PID: $PID"
        else
            echo "杀死进程 PID: $PID 失败"
        fi
    fi
done

ps -ef |grep "$PROCESS_NAME"
exit 0
