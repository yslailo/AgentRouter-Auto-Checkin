#!/usr/bin/env python3

import os
import sys
import time
import traceback
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# 环境变量配置
USERNAME = os.getenv("USERNAME") or ""
PASSWORD = os.getenv("PASSWORD") or ""
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN") or ""
TG_CHAT_ID = os.getenv("TG_CHAT_ID") or ""

# 代理配置（可选）
PROXY_SERVER = os.getenv("PROXY_SERVER") or ""  # 格式: http://host:port 或 socks5://host:port
PROXY_USERNAME = os.getenv("PROXY_USERNAME") or ""  # 代理用户名（如果需要）
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD") or ""  # 代理密码（如果需要）

SITE_URL = "https://agentrouter.org"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

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

def browser_login_complete() -> dict | None:
    """
    使用 Playwright 完成整个登录流程。
    支持代理配置绕过 WAF 检测。
    """
    log("INFO", f"使用浏览器自动化登录 {SITE_URL}...")

    # 配置代理
    proxy_config = None
    if PROXY_SERVER:
        proxy_config = {
            "server": PROXY_SERVER,
        }
        if PROXY_USERNAME and PROXY_PASSWORD:
            proxy_config["username"] = PROXY_USERNAME
            proxy_config["password"] = PROXY_PASSWORD
        log("INFO", f"使用代理: {PROXY_SERVER}")

    result = None

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
            ],
            proxy=proxy_config,  # 设置代理
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

            # 等待页面完全加载
            log("INFO", "等待页面渲染...")
            page.wait_for_timeout(3000)  # 增加到 3 秒

            # 检查页面状态
            page_info = page.evaluate("""
                () => {
                    return {
                        url: window.location.href,
                        title: document.title,
                        readyState: document.readyState,
                        bodyText: document.body?.innerText?.substring(0, 200) || '',
                        hasInputs: document.querySelectorAll('input').length,
                        hasButtons: document.querySelectorAll('button').length,
                        hasForm: !!document.querySelector('form'),
                        htmlPreview: document.documentElement.outerHTML.substring(0, 500)
                    };
                }
            """)

            log("INFO", f"  当前 URL: {page_info.get('url')}")
            log("INFO", f"  页面标题: {page_info.get('title')}")
            log("INFO", f"  输入框数量: {page_info.get('hasInputs')}")
            log("INFO", f"  按钮数量: {page_info.get('hasButtons')}")

            # 如果页面不对，截图并报错
            if page_info.get('hasInputs') == 0:
                log("ERROR", f"页面没有输入框！可能被重定向或拦截")
                log("ERROR", f"页面文本预览: {page_info.get('bodyText')}")
                log("ERROR", f"HTML 预览: {page_info.get('htmlPreview')}")

                try:
                    screenshot_path = "page_error.png"
                    page.screenshot(path=screenshot_path, full_page=True)
                    log("INFO", f"已保存页面截图: {screenshot_path}")
                except:
                    pass

                raise Exception(f"登录页面加载异常，没有找到表单元素")

            # Step 2: 填写表单（使用更宽松的等待策略）
            log("INFO", "Step 2: 填写登录表单...")

            # 使用 page.evaluate 等待元素真正可见
            wait_result = page.evaluate("""
                async () => {
                    let attempts = 0;
                    const maxAttempts = 30; // 最多等待 15 秒

                    while (attempts < maxAttempts) {
                        const username = document.querySelector('input#username');
                        const password = document.querySelector('input#password');
                        const submit = document.querySelector('button[type="submit"]');

                        if (username && password && submit &&
                            username.offsetParent !== null &&
                            password.offsetParent !== null &&
                            submit.offsetParent !== null) {
                            return {
                                success: true,
                                waitTime: attempts * 500
                            };
                        }

                        await new Promise(resolve => setTimeout(resolve, 500));
                        attempts++;
                    }

                    return {
                        success: false,
                        hasUsername: !!document.querySelector('input#username'),
                        hasPassword: !!document.querySelector('input#password'),
                        hasSubmit: !!document.querySelector('button[type="submit"]')
                    };
                }
            """)

            if not wait_result.get("success"):
                raise Exception(f"表单元素未出现: {wait_result}")

            log("INFO", f"  表单元素已就绪（等待 {wait_result.get('waitTime')}ms）")

            # 填写用户名（使用 locator 并等待）
            try:
                username_locator = page.locator('input#username')
                username_locator.wait_for(state="visible", timeout=5000)
                username_locator.click(timeout=5000)
                username_locator.fill(USERNAME, timeout=5000)
                log("INFO", "  ✓ 已填写用户名")
            except Exception as e:
                raise Exception(f"填写用户名失败: {e}")

            # 等待一下
            page.wait_for_timeout(500)

            # 填写密码
            try:
                password_locator = page.locator('input#password')
                password_locator.wait_for(state="visible", timeout=5000)
                password_locator.click(timeout=5000)
                password_locator.fill(PASSWORD, timeout=5000)
                log("INFO", "  ✓ 已填写密码")
            except Exception as e:
                raise Exception(f"填写密码失败: {e}")

            # 等待一下
            page.wait_for_timeout(1000)

            # Step 3: 点击提交按钮
            log("INFO", "Step 3: 点击提交按钮...")
            try:
                submit_locator = page.locator('button[type="submit"]')
                submit_locator.wait_for(state="visible", timeout=5000)
                submit_locator.click(timeout=5000)
                log("INFO", "  ✓ 已点击提交按钮")
            except Exception as e:
                raise Exception(f"点击提交按钮失败: {e}")

            # Step 4: 等待登录完成
            log("INFO", "Step 4: 等待登录响应...")
            page.wait_for_timeout(3000)

            # 检查是否有滑块验证
            has_captcha = page.evaluate("""
                () => !!document.querySelector('#nc_1_n1z, .nc-container, [class*="captcha"]')
            """)

            if has_captcha:
                log("WARN", "检测到滑块验证码，等待处理...")
                page.wait_for_timeout(5000)

            current_url = page.url
            log("INFO", f"  当前 URL: {current_url}")

            # Step 5: 使用登录后的浏览器会话调用用户信息接口
            log("INFO", "Step 5: 获取用户信息...")

            api_result = page.evaluate("""
                async () => {
                    try {
                        let userStr = null;
                        for (let attempt = 0; attempt < 10; attempt++) {
                            userStr = localStorage.getItem('user');
                            if (userStr) break;
                            await new Promise(resolve => setTimeout(resolve, 500));
                        }

                        if (!userStr) {
                            return { success: false, error: '登录后未找到用户 ID' };
                        }

                        const localUser = JSON.parse(userStr);
                        if (!localUser.id) {
                            return { success: false, error: '登录用户 ID 无效' };
                        }

                        const response = await fetch('/api/user/self', {
                            method: 'GET',
                            headers: {
                                'Accept': 'application/json, text/plain, */*',
                                'New-API-User': String(localUser.id)
                            },
                            credentials: 'include',
                            cache: 'no-store'
                        });

                        let payload;
                        try {
                            payload = await response.json();
                        } catch (err) {
                            return {
                                success: false,
                                status: response.status,
                                error: '用户信息接口未返回 JSON'
                            };
                        }

                        return {
                            success: response.ok,
                            status: response.status,
                            payload
                        };
                    } catch (err) {
                        return {
                            success: false,
                            error: err.toString()
                        };
                    }
                }
            """)

            if not api_result.get("success"):
                status = api_result.get("status")
                error = api_result.get("error") or "请求失败"
                if status:
                    raise Exception(f"获取用户信息失败（HTTP {status}）: {error}")
                raise Exception(f"获取用户信息失败: {error}")

            payload = api_result.get("payload")
            if not isinstance(payload, dict) or payload.get("success") is not True:
                message = payload.get("message") if isinstance(payload, dict) else "响应格式错误"
                raise Exception(f"获取用户信息失败: {message or '接口返回失败'}")

            user_data = payload.get("data")
            if not isinstance(user_data, dict):
                raise Exception("获取用户信息失败: 响应中缺少 data")

            quota = user_data.get("quota")
            if isinstance(quota, bool) or not isinstance(quota, (int, float)):
                raise Exception("获取用户信息失败: data.quota 不是有效数字")

            result = {
                "user_id": user_data.get("id", 0),
                "username": user_data.get("username") or USERNAME,
                "quota": quota,
                "checked_in": None,
            }
            log("INFO", "  ✓ 已从 /api/user/self 获取用户信息")
            log("INFO", f"  ✓ 用户 ID: {result['user_id']}")
            log("INFO", f"  ✓ 用户名: {result['username']}")
            log("INFO", f"  ✓ quota: {result['quota']}")

        except PlaywrightTimeoutError as e:
            log("ERROR", f"页面操作超时: {e}")
            log("ERROR", f"当前 URL: {page.url}")
            # 截图用于调试
            try:
                screenshot_path = "error_screenshot.png"
                page.screenshot(path=screenshot_path)
                log("INFO", f"已保存错误截图: {screenshot_path}")
            except:
                pass

        except Exception as e:
            log("ERROR", f"浏览器自动化登录失败: {e}")
            log("ERROR", traceback.format_exc())

        finally:
            browser.close()

    return result

def format_balance(quota: int) -> str:
    """将 quota 转换为美元显示（假设 500000 = $1）"""
    if quota is None:
        return "N/A"
    balance = quota / 500000
    return f"{balance:.2f}$"

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
    balance = format_balance(login_result.get("quota", 0))

    log("INFO", f"✅ 登录成功！")
    log("INFO", f"用户 ID: {user_id}")
    log("INFO", f"用户名: {username}")
    log("INFO", f"当前余额: {balance}")
    log("INFO", f"🎁 通过登录完成签到")

    # ---------- Step 2: 发送 Telegram 通知 ----------
    message = (
        f"🎁 <b>AgentRouter 签到通知</b>\n\n"
        f"👤 登录账户: {USERNAME}\n"
        f"💰 当前余额: {balance}\n"
        f"📋 状态: 通过登录完成签到\n"
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
