#!/bin/bash

# 本地测试脚本
# 使用方法:
# 1. 修改下面的 USERNAME 和 PASSWORD
# 2. 运行: bash test_local.sh

export USERNAME="your-email@example.com"
export PASSWORD="your-password"
export TG_BOT_TOKEN=""  # 可选
export TG_CHAT_ID=""    # 可选

echo "=== 开始本地测试 ==="
echo "用户名: $USERNAME"
echo "密码: ${PASSWORD:0:3}***"
echo ""

python app.py
