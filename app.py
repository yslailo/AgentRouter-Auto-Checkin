#!/usr/bin/env python3

import os
import sys
import json
import time
import subprocess
import requests
import traceback
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright

# 环境变量配置
USERNAME     = os.getenv("USERNAME") or ""  # 用户名（邮箱），必填
PASSWORD     = os.getenv("PASSWORD") or ""  # 密码，必填
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN") or ""  # Telegram bot token，不需要通知可以留空
TG_CHAT_ID   = os.getenv("TG_CHAT_ID") or ""    # Telegram chat id

SITE_URL = "https://agentrouter.org"
WAF_COOKIE_NAMES = ["acw_tc", "cdn_sec_tc", "acw_sc__v2"]

# 工具函数
def log(level: str, msg: str):
    """带时间戳的日志输出"""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)

def send_telegram(message: str) -> bool:
    """发送 Telegram 消息"""
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        log("WARN", "Telegram 配置不完整，跳过发送")
        print(f"--- 消息内容 ---\n{message}\n---------------")
        return False

    try:
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TG_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }
        resp = requests.post(url, json=data, timeout=30)
        resp.raise_for_status()
        log("INFO", "Telegram 消息发送成功")
        return True
    except Exception as e:
        log("ERROR", f"Telegram 发送失败: {e}")
        return False

# WAF Cookie 获取
def get_waf_cookies() -> dict:
    """
    使用 Playwright 浏览器访问登录页面，获取 WAF Cookie。
    """
    log("INFO", f"使用浏览器获取 WAF Cookie（访问 {SITE_URL}/login）...")

    waf_cookies = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )

        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
            ),
        )

        page = context.new_page()

        try:
            page.goto(f"{SITE_URL}/login", wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            log("WARN", f"访问登录页面失败: {e}")

        # 等待 WAF Cookie 生成
        page.wait_for_timeout(3000)

        cookies = context.cookies()
        for cookie in cookies:
            name = cookie.get("name")
            value = cookie.get("value")
            if name in WAF_COOKIE_NAMES and value:
                waf_cookies[name] = value

        browser.close()

    if waf_cookies:
        log("INFO", f"获取到 {len(waf_cookies)} 个 WAF Cookie: {list(waf_cookies.keys())}")
    else:
        log("WARN", "未获取到 WAF Cookie")

    return waf_cookies

# API 调用
def build_headers() -> dict:
    """构建 API 请求头"""
    return {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": SITE_URL,
        "Origin": SITE_URL,
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

def login_with_password(session: requests.Session, headers: dict) -> dict | None:
    """
    使用账号密码登录，登录动作本身即触发签到。
    返回:
      {
        "user_id": int,
        "username": str,
        "checked_in": bool,  # 登录前是否已签到
        "quota": int,         # 当前余额
        "raw": dict,
      }
    """
    # 先访问登录页面（可能触发 WAF 等）
    try:
        session.get(f"{SITE_URL}/login?expired=true", headers=headers, timeout=30)
    except Exception as e:
        log("WARN", f"预访问登录页面失败: {e}")

    # 调用登录 API
    login_url = f"{SITE_URL}/api/user/login?turnstile="
    login_headers = headers.copy()
    login_headers["Content-Type"] = "application/json"
    login_headers["X-Requested-With"] = "XMLHttpRequest"
    login_headers["Referer"] = f"{SITE_URL}/login?expired=true"

    payload = {
        "username": USERNAME,
        "password": PASSWORD,
    }

    try:
        resp = session.post(login_url, headers=login_headers, json=payload, timeout=30)
        log("INFO", f"登录接口响应: HTTP {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                user_data = data.get("data", {})
                user_id = user_data.get("id")
                username = user_data.get("username", USERNAME)
                checked_in = user_data.get("checked_in")  # 登录前是否已签到
                quota = user_data.get("quota", 0)

                log("INFO", f"✅ 登录成功！用户 ID: {user_id}, 用户名: {username}")

                return {
                    "user_id": user_id,
                    "username": username,
                    "checked_in": bool(checked_in) if isinstance(checked_in, bool) else None,
                    "quota": quota,
                    "raw": user_data,
                }
            else:
                error_msg = data.get("message", "未知错误")
                log("ERROR", f"登录失败: {error_msg}")
        else:
            log("ERROR", f"登录失败: HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        log("ERROR", f"登录请求异常: {e}")

    return None

def get_user_info(session: requests.Session, headers: dict, user_id: int) -> dict | None:
    """
    通过 /api/user/self 接口获取用户信息。
    """
    url = f"{SITE_URL}/api/user/self"
    headers_with_uid = headers.copy()
    headers_with_uid["new-api-user"] = str(user_id)

    try:
        resp = session.get(url, headers=headers_with_uid, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                user_data = data.get("data", {})
                return {
                    "quota": user_data.get("quota", 0),
                    "used_quota": user_data.get("used_quota", 0),
                    "username": user_data.get("username", ""),
                    "id": user_data.get("id", 0),
                    "raw": user_data,
                }
            else:
                log("WARN", f"API 返回非成功: {data}")
        else:
            log("WARN", f"API HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        log("WARN", f"获取用户信息失败: {e}")

    return None

def format_balance(quota: int) -> str:
    """将 quota 转换为美元显示（假设 500000 = $1）"""
    if quota is None:
        return "N/A"
    balance = quota / 500000
    if balance == int(balance):
        return f"{int(balance)}$"
    return f"{balance:.2f}$"

# 主流程
def run_checkin():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log("INFO", "=" * 50)
    log("INFO", "AgentRouter 登录签到脚本启动")
    log("INFO", f"时间: {now_str}")
    log("INFO", f"用户名: {USERNAME}")
    log("INFO", "=" * 50)

    if not USERNAME or not PASSWORD:
        log("ERROR", "USERNAME 或 PASSWORD 未配置，请设置环境变量")
        sys.exit(1)

    # ---------- Step 1: 获取 WAF Cookie ----------
    waf_cookies = get_waf_cookies()

    # ---------- Step 2: 构建 HTTP Session ----------
    session = requests.Session()

    # 设置 WAF Cookie
    for name, value in waf_cookies.items():
        session.cookies.set(name, value, domain="agentrouter.org", path="/")

    log("INFO", f"已设置 {len(waf_cookies)} 个 WAF Cookie: {list(waf_cookies.keys())}")

    headers = build_headers()

    # ---------- Step 3: 使用账号密码登录（登录即签到）----------
    log("INFO", "使用账号密码登录...")
    login_result = login_with_password(session, headers)

    if not login_result:
        log("ERROR", "登录失败，请检查账号密码是否正确")
        send_telegram(
            f"❌ <b>AgentRouter 登录失败</b>\n"
            f"👤 账户: {USERNAME}\n"
            f"⏱️ 时间: {now_str}\n"
            f"📝 原因: 账号或密码错误"
        )
        sys.exit(1)

    user_id = login_result["user_id"]
    username = login_result["username"]
    checked_in_before = login_result["checked_in"]
    first_balance = format_balance(login_result["quota"])

    log("INFO", f"用户名: {username}")
    log("INFO", f"用户 ID: {user_id}")
    log("INFO", f"登录前签到状态: {'已签到' if checked_in_before else '未签到'}")
    log("INFO", f"初始余额: {first_balance}")

    # ---------- Step 4: 等待 3 秒后重新获取余额 ----------
    log("INFO", "等待 3 秒后重新获取余额...")
    time.sleep(3)

    user_info = get_user_info(session, headers, user_id)
    second_balance = format_balance(user_info.get("quota", 0)) if user_info else "N/A"
    log("INFO", f"刷新后余额: {second_balance}")

    # ---------- Step 5: 判断签到结果 ----------
    if checked_in_before is True:
        status_msg = "今日已签到过（登录前）"
        status_emoji = "✅"
    elif checked_in_before is False:
        status_msg = "通过登录完成签到"
        status_emoji = "🎁"
    else:
        status_msg = "登录成功（签到状态未知）"
        status_emoji = "✅"

    log("INFO", f"{status_emoji} {status_msg}")

    # ---------- Step 6: 发送 Telegram 通知 ----------
    message = (
        f"{status_emoji} <b>AgentRouter 签到通知</b>\n\n"
        f"👤 登录账户: {USERNAME}\n"
        f"💰 登录时余额: {first_balance}\n"
        f"💰 当前余额: {second_balance}\n"
        f"📋 状态: {status_msg}\n"
        f"⏱️ 时间: {now_str}"
    )

    send_telegram(message)

    log("INFO", "=== 脚本执行完毕 ===")

def main():
    try:
        run_checkin()
    except KeyboardInterrupt:
        log("WARN", "用户中断")
        sys.exit(130)
    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        log("ERROR", f"脚本执行出错: {error_msg}")
        log("ERROR", traceback.format_exc())
        send_telegram(
            f"❌ <b>AgentRouter 脚本异常</b>\n"
            f"👤 账户: {USERNAME}\n"
            f"⏱️ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"📝 错误: {error_msg}"
        )
        sys.exit(1)

if __name__ == "__main__":
    main()
