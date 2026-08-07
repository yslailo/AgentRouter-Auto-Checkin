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

# 使用浏览器自动化登录
def browser_login() -> dict | None:
    """
    使用 Playwright 浏览器自动化登录，处理 WAF 和滑块验证。
    返回:
      {
        "user_id": int,
        "username": str,
        "checked_in": bool,
        "quota": int,
        "session": str,  # Session Cookie
        "cookies": dict,  # 所有 Cookie
      }
    """
    log("INFO", f"使用浏览器自动化登录 {SITE_URL}...")

    result = None

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
            # Step 1: 访问登录页面
            log("INFO", "正在访问登录页面...")
            page.goto(f"{SITE_URL}/login", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            # Step 2: 查找并填写账号密码
            log("INFO", "正在填写登录表单...")

            # 查找用户名输入框（可能是 input[type=text] 或 input[type=email]）
            username_input = page.locator("input[type=text], input[type=email], input[name*=user], input[name*=email], input[placeholder*=账号], input[placeholder*=邮箱]").first
            if username_input.is_visible():
                username_input.fill(USERNAME)
                log("INFO", "✓ 已填写用户名")
            else:
                log("ERROR", "找不到用户名输入框")
                browser.close()
                return None

            # 查找密码输入框
            password_input = page.locator("input[type=password]").first
            if password_input.is_visible():
                password_input.fill(PASSWORD)
                log("INFO", "✓ 已填写密码")
            else:
                log("ERROR", "找不到密码输入框")
                browser.close()
                return None

            # Step 3: 点击登录按钮
            log("INFO", "正在点击登录按钮...")
            login_button = page.locator("button[type=submit], button:has-text('登录'), button:has-text('Login')").first
            login_button.click()

            # Step 4: 等待登录完成或出现验证码
            log("INFO", "等待登录响应...")
            page.wait_for_timeout(3000)

            # 检查是否有滑块验证
            captcha_slider = page.locator("#nc_1_n1z, .nc-container, .aliyun-captcha, [id*=captcha], [class*=captcha]").first
            if captcha_slider.is_visible(timeout=2000):
                log("WARN", "检测到滑块验证码，尝试处理...")
                # 等待用户手动完成或尝试自动处理（这里简单等待）
                page.wait_for_timeout(5000)

            # Step 5: 检查是否登录成功（等待跳转或检查 URL 变化）
            page.wait_for_timeout(3000)
            current_url = page.url

            if "/login" not in current_url or "console" in current_url or "dashboard" in current_url:
                log("INFO", "✅ 登录成功，已跳转到控制台")
            else:
                log("INFO", f"当前页面: {current_url}")

            # Step 6: 获取登录后的 Cookie
            cookies = context.cookies()
            session_cookie = None
            user_id_cookie = None
            all_cookies = {}

            for cookie in cookies:
                name = cookie.get("name")
                value = cookie.get("value")
                all_cookies[name] = value

                if name == "session":
                    session_cookie = value
                    log("INFO", f"✓ 获取到 Session Cookie: {value[:10]}...{value[-10:]}")
                if name == "user_id":
                    user_id_cookie = value

            if not session_cookie:
                log("ERROR", "未获取到 Session Cookie，登录可能失败")
                log("INFO", f"获取到的 Cookie: {list(all_cookies.keys())}")
                browser.close()
                return None

            # Step 7: 调用 API 获取用户信息
            log("INFO", "正在获取用户信息...")
            try:
                # 使用 page.evaluate 调用 API
                api_response = page.evaluate("""
                    async () => {
                        const resp = await fetch('/api/user/self', {
                            method: 'GET',
                            headers: {
                                'Accept': 'application/json'
                            }
                        });
                        return await resp.json();
                    }
                """)

                if api_response and api_response.get("success"):
                    user_data = api_response.get("data", {})
                    user_id = user_data.get("id")
                    username = user_data.get("username")
                    quota = user_data.get("quota", 0)

                    # checked_in 可能需要从其他 API 获取，这里先设为 None
                    log("INFO", f"✓ 用户 ID: {user_id}, 用户名: {username}, 余额: {quota}")

                    result = {
                        "user_id": user_id,
                        "username": username,
                        "checked_in": None,  # 登录即签到，默认为已签到
                        "quota": quota,
                        "session": session_cookie,
                        "cookies": all_cookies,
                    }
                else:
                    log("WARN", f"获取用户信息失败: {api_response}")

            except Exception as e:
                log("WARN", f"获取用户信息失败: {e}")
                # 即使获取用户信息失败，也返回基本信息
                result = {
                    "user_id": int(user_id_cookie) if user_id_cookie and user_id_cookie.isdigit() else 0,
                    "username": USERNAME,
                    "checked_in": None,
                    "quota": 0,
                    "session": session_cookie,
                    "cookies": all_cookies,
                }

        except Exception as e:
            log("ERROR", f"浏览器自动化登录失败: {e}")
            import traceback
            log("ERROR", traceback.format_exc())

        browser.close()

    return result

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

    # ---------- Step 1: 使用浏览器自动化登录（登录即签到）----------
    login_result = browser_login()

    if not login_result:
        log("ERROR", "浏览器自动化登录失败")
        send_telegram(
            f"❌ <b>AgentRouter 登录失败</b>\n"
            f"👤 账户: {USERNAME}\n"
            f"⏱️ 时间: {now_str}\n"
            f"📝 原因: 浏览器自动化登录失败，可能需要人工处理验证码"
        )
        sys.exit(1)

    user_id = login_result["user_id"]
    username = login_result["username"]
    checked_in_before = login_result["checked_in"]
    first_balance = format_balance(login_result["quota"])
    session_cookie = login_result["session"]

    log("INFO", f"用户名: {username}")
    log("INFO", f"用户 ID: {user_id}")
    log("INFO", f"Session: {session_cookie[:10]}...{session_cookie[-10:] if len(session_cookie) > 20 else ''}")
    log("INFO", f"初始余额: {first_balance}")

    # ---------- Step 2: 等待 3 秒后重新获取余额 ----------
    log("INFO", "等待 3 秒后重新获取余额...")
    time.sleep(3)

    # 使用获取到的 Session 查询余额
    session = requests.Session()
    for name, value in login_result["cookies"].items():
        session.cookies.set(name, value, domain="agentrouter.org", path="/")

    headers = build_headers()
    user_info = get_user_info(session, headers, user_id)
    second_balance = format_balance(user_info.get("quota", 0)) if user_info else first_balance
    log("INFO", f"刷新后余额: {second_balance}")

    # ---------- Step 3: 判断签到结果 ----------
    # 登录即签到，如果成功登录就是成功签到
    balance_changed = first_balance != second_balance
    if balance_changed:
        status_msg = f"通过登录完成签到（余额变化: {first_balance} → {second_balance}）"
        status_emoji = "🎁"
    else:
        status_msg = "今日已签到（余额未变化）"
        status_emoji = "✅"

    log("INFO", f"{status_emoji} {status_msg}")

    # ---------- Step 4: 发送 Telegram 通知 ----------
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
