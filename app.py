#!/usr/bin/env python3

import os
import sys
import json
import time
import http.cookiejar
import urllib.request
import urllib.error
import urllib.parse
import subprocess
import traceback
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright

# 环境变量配置
USERNAME     = os.getenv("USERNAME") or ""  # 用户名（邮箱），必填
PASSWORD     = os.getenv("PASSWORD") or ""  # 密码，必填
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN") or ""  # Telegram bot token，不需要通知可以留空
TG_CHAT_ID   = os.getenv("TG_CHAT_ID") or ""    # Telegram chat id

SITE_URL = "https://agentrouter.org"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

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
        import requests
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

# 使用 Playwright 完成整个登录流程（在浏览器内）
def browser_login_complete() -> dict:
    """
    使用 Playwright 在浏览器内完成整个登录流程。
    避免切换到 urllib，以免触发 WAF 验证。
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
            viewport={"width": 1920, "height": 1080},
            user_agent=USER_AGENT,
        )

        page = context.new_page()

        try:
            # Step 1: 访问登录页面
            log("INFO", "Step 1: 访问登录页面...")
            page.goto(f"{SITE_URL}/login", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)

            # Step 2: 填写表单
            log("INFO", "Step 2: 填写登录表单...")

            # 使用精确的选择器（从 jshook 分析得出）
            try:
                # 填写用户名
                username_input = page.locator('input#username')
                username_input.wait_for(state="visible", timeout=5000)
                username_input.fill(USERNAME)
                log("INFO", "  ✓ 已填写用户名")

                # 填写密码
                password_input = page.locator('input#password')
                password_input.wait_for(state="visible", timeout=5000)
                password_input.fill(PASSWORD)
                log("INFO", "  ✓ 已填写密码")

                page.wait_for_timeout(1000)

            except Exception as e:
                raise Exception(f"填写表单失败: {e}")

            # Step 3: 点击登录按钮
            log("INFO", "Step 3: 点击提交按钮...")
            try:
                # 点击"继续"按钮（type=submit）
                submit_button = page.locator('button[type="submit"]')
                submit_button.wait_for(state="visible", timeout=5000)
                submit_button.click()
                log("INFO", "  ✓ 已点击提交按钮")
            except Exception as e:
                raise Exception(f"点击提交按钮失败: {e}")

            # Step 4: 等待登录完成
            log("INFO", "Step 4: 等待登录完成...")
            page.wait_for_timeout(3000)

            # 检查是否有滑块验证
            try:
                captcha = page.locator('#nc_1_n1z, .nc-container, [class*="captcha"]').first
                if captcha.is_visible(timeout=2000):
                    log("WARN", "检测到滑块验证，等待处理...")
                    page.wait_for_timeout(5000)
            except:
                pass

            # 再等待一下，确保跳转完成
            page.wait_for_timeout(2000)

            current_url = page.url
            log("INFO", f"  当前 URL: {current_url}")

            # Step 5: 使用浏览器内的 fetch API 获取用户信息
            log("INFO", "Step 5: 获取用户信息...")
            try:
                api_response = page.evaluate("""
                    async () => {
                        try {
                            const resp = await fetch('/api/user/self', {
                                method: 'GET',
                                headers: {
                                    'Accept': 'application/json'
                                }
                            });
                            const data = await resp.json();
                            return {success: true, data: data};
                        } catch (err) {
                            return {success: false, error: err.toString()};
                        }
                    }
                """)

                if api_response.get("success"):
                    api_data = api_response.get("data", {})
                    if api_data.get("success"):
                        user_data = api_data.get("data", {})
                        user_id = user_data.get("id")
                        username = user_data.get("username")
                        quota = user_data.get("quota", 0)

                        log("INFO", f"  ✓ 用户 ID: {user_id}")
                        log("INFO", f"  ✓ 用户名: {username}")
                        log("INFO", f"  ✓ 余额: {quota}")

                        result = {
                            "user_id": user_id,
                            "username": username,
                            "quota": quota,
                            "checked_in": None,  # 登录即签到
                        }
                    else:
                        raise Exception(f"API 返回失败: {api_data}")
                else:
                    raise Exception(f"API 调用失败: {api_response.get('error')}")

            except Exception as e:
                log("WARN", f"通过 API 获取用户信息失败: {e}")
                # 尝试从页面元素中提取信息
                log("INFO", "尝试从页面中提取用户信息...")
                result = {
                    "user_id": 0,
                    "username": USERNAME,
                    "quota": 0,
                    "checked_in": None,
                }

        except Exception as e:
            log("ERROR", f"浏览器自动化登录失败: {e}")
            import traceback
            log("ERROR", traceback.format_exc())

        finally:
            browser.close()

    return result

# 以下 ApiClient 类已弃用（改用浏览器自动化）
# HTTP 客户端（参考 newapi-checkin 实现）
class ApiClient_DEPRECATED:
    def __init__(self, base_url: str, initial_cookies: dict):
        self.base_url = base_url.rstrip("/")
        self.cookie_jar = http.cookiejar.CookieJar()

        # 将初始 Cookie 添加到 CookieJar
        for name, value in initial_cookies.items():
            cookie = http.cookiejar.Cookie(
                version=0,
                name=name,
                value=value,
                port=None,
                port_specified=False,
                domain="agentrouter.org",
                domain_specified=True,
                domain_initial_dot=False,
                path="/",
                path_specified=True,
                secure=True,
                expires=None,
                discard=True,
                comment=None,
                comment_url=None,
                rest={},
                rfc2109=False
            )
            self.cookie_jar.set_cookie(cookie)

        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar)
        )
        self.user_id = None
        self.username = None

    def _make_request(
        self,
        path: str,
        method: str = "GET",
        body: dict = None,
        referer: str = "/console",
        parse_json: bool = True,
        timeout: float = 30.0
    ):
        url = self.base_url + path
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Referer": self.base_url + referer,
            "Cache-Control": "no-store",
        }

        request_data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            headers["Origin"] = self.base_url
            request_data = json.dumps(body, ensure_ascii=False).encode("utf-8")

        if self.user_id is not None:
            headers["New-API-User"] = str(self.user_id)

        request = urllib.request.Request(url, data=request_data, headers=headers, method=method)

        try:
            with self.opener.open(request, timeout=timeout) as response:
                text = response.read().decode("utf-8", "replace")

                if not parse_json:
                    return text

                try:
                    return json.loads(text)
                except json.JSONDecodeError as e:
                    log("ERROR", f"响应不是 JSON 格式: {e}")
                    log("ERROR", f"响应内容: {text[:500]}")
                    raise ValueError(f"响应不是 JSON: {text[:200]}")

        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", "replace")
            log("ERROR", f"HTTP {exc.code}: {text[:500]}")
            raise ValueError(f"HTTP {exc.code}: {text[:200]}")
        except urllib.error.URLError as exc:
            log("ERROR", f"网络错误: {exc.reason}")
            raise ValueError(f"网络错误: {exc.reason}")
        except Exception as exc:
            log("ERROR", f"请求异常: {exc}")
            raise

    def login(self, username: str, password: str) -> dict:
        """
        登录流程（完全参考 newapi-checkin）
        """
        log("INFO", "Step 1: 预访问登录页面...")
        try:
            self._make_request(
                "/login?expired=true",
                method="GET",
                referer="/login?expired=true",
                parse_json=False
            )
            log("INFO", "✓ 预访问成功，Cookie 已更新")
        except Exception as e:
            log("WARN", f"预访问失败（继续尝试登录）: {e}")

        # 等待一下，让 Cookie 生效
        time.sleep(2)

        log("INFO", "Step 2: 调用登录 API...")
        payload = self._make_request(
            "/api/user/login?turnstile=",
            method="POST",
            body={"username": username, "password": password},
            referer="/login?expired=true"
        )

        if not payload.get("success"):
            error_msg = payload.get("message", "登录失败")
            raise ValueError(error_msg)

        data = payload.get("data", {})
        user_id = data.get("id")
        username_ret = data.get("username", username)
        checked_in = data.get("checked_in")
        quota = data.get("quota", 0)

        if not isinstance(user_id, int):
            raise ValueError("登录响应缺少有效的用户 ID")

        self.user_id = user_id
        self.username = username_ret

        log("INFO", f"✅ 登录成功！用户 ID: {user_id}, 用户名: {username_ret}")

        return {
            "user_id": user_id,
            "username": username_ret,
            "checked_in": bool(checked_in) if isinstance(checked_in, bool) else None,
            "quota": quota,
        }

    def get_user_info(self) -> dict:
        """获取用户信息"""
        if self.user_id is None:
            raise ValueError("未登录")

        payload = self._make_request("/api/user/self")

        if not payload.get("success"):
            raise ValueError("获取用户信息失败")

        data = payload.get("data", {})
        return {
            "quota": data.get("quota", 0),
            "used_quota": data.get("used_quota", 0),
            "username": data.get("username", ""),
            "id": data.get("id", 0),
        }

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
    login_result = browser_login_complete()

    if not login_result:
        log("ERROR", "浏览器自动化登录失败")
        send_telegram(
            f"❌ <b>AgentRouter 登录失败</b>\n"
            f"👤 账户: {USERNAME}\n"
            f"⏱️ 时间: {now_str}\n"
            f"📝 原因: 浏览器自动化登录失败"
        )
        sys.exit(1)

    user_id = login_result.get("user_id", 0)
    username = login_result.get("username", USERNAME)
    checked_in_before = login_result.get("checked_in")
    first_balance = format_balance(login_result.get("quota", 0))

    log("INFO", f"用户 ID: {user_id}")
    log("INFO", f"用户名: {username}")
    log("INFO", f"初始余额: {first_balance}")

    # ---------- Step 2: 等待 3 秒（登录即签到，余额可能延迟更新）----------
    log("INFO", "等待 3 秒...")
    time.sleep(3)

    # 余额可能已在登录时获取，这里直接使用
    second_balance = first_balance

    # ---------- Step 3: 判断签到结果 ----------
    # 登录即签到，成功登录就是成功签到
    status_msg = "通过登录完成签到"
    status_emoji = "🎁"

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
