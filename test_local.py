#!/usr/bin/env python3
"""
本地测试脚本 - 用于测试 AgentRouter 登录签到功能
使用方法：修改下面的 USERNAME 和 PASSWORD 后运行
"""

import os
import sys

# ========== 配置区域 - 请修改这里 ==========
TEST_USERNAME = "your-email@example.com"  # 修改为你的邮箱
TEST_PASSWORD = "your-password"           # 修改为你的密码
TEST_TG_BOT_TOKEN = ""                    # 可选：Telegram Bot Token
TEST_TG_CHAT_ID = ""                      # 可选：Telegram Chat ID
# ==========================================

def main():
    print("=" * 60)
    print("AgentRouter 本地测试脚本")
    print("=" * 60)
    print()

    # 检查是否已修改配置
    if TEST_USERNAME == "your-email@example.com" or TEST_PASSWORD == "your-password":
        print("⚠️  警告：请先修改脚本中的 TEST_USERNAME 和 TEST_PASSWORD！")
        print()
        print("打开 test_local.py 文件，修改以下内容：")
        print("  TEST_USERNAME = \"your-email@example.com\"  # 改为你的邮箱")
        print("  TEST_PASSWORD = \"your-password\"           # 改为你的密码")
        print()
        sys.exit(1)

    # 设置环境变量
    os.environ["USERNAME"] = TEST_USERNAME
    os.environ["PASSWORD"] = TEST_PASSWORD
    if TEST_TG_BOT_TOKEN:
        os.environ["TG_BOT_TOKEN"] = TEST_TG_BOT_TOKEN
    if TEST_TG_CHAT_ID:
        os.environ["TG_CHAT_ID"] = TEST_TG_CHAT_ID

    print(f"✓ 用户名: {TEST_USERNAME}")
    print(f"✓ 密码: {TEST_PASSWORD[:3]}{'*' * (len(TEST_PASSWORD) - 3)}")
    print(f"✓ Telegram: {'已配置' if TEST_TG_BOT_TOKEN and TEST_TG_CHAT_ID else '未配置（跳过通知）'}")
    print()
    print("-" * 60)
    print()

    # 检查依赖
    try:
        import requests
        import playwright
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print()
        print("请先安装依赖：")
        print("  pip install requests playwright")
        print("  playwright install chromium")
        print()
        sys.exit(1)

    # 导入并运行主脚本
    try:
        # 将当前目录添加到路径
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

        # 导入 app.py 中的 main 函数
        from app import main as app_main

        # 运行主程序
        app_main()

    except Exception as e:
        print()
        print("=" * 60)
        print("❌ 测试失败")
        print("=" * 60)
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
