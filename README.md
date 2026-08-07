# AgentRouter 自动签到脚本

每天自动登录 [AgentRouter](https://agentrouter.org/) 完成签到，获取每日奖励。

## ⚙️ 功能特性

- ✅ 使用账号密码自动登录（登录即签到）
- ✅ 支持代理配置，绕过 WAF 验证
- ✅ Telegram 通知（可选）
- ✅ GitHub Actions 自动运行（每天北京时间 10:00）

## 🚀 快速开始

### 1. Fork 本仓库

点击右上角 **Fork** 按钮，将仓库复制到你的账号下。

### 2. 配置 Secrets

前往仓库的 **Settings** → **Secrets and variables** → **Actions** → **New repository secret**，添加以下配置：

#### 必须配置：

| Name | Value | 说明 |
|------|-------|------|
| `USERNAME` | 你的邮箱 | AgentRouter 登录邮箱 |
| `PASSWORD` | 你的密码 | AgentRouter 登录密码 |

#### 代理配置（推荐，用于绕过 WAF）：

**✨ 推荐方式：使用订阅链接（一个 Secret 搞定）**

| Name | Value | 说明 |
|------|-------|------|
| `PROXY_SUBSCRIPTION_URL` | 你的订阅链接 | 机场订阅链接，支持 V2Ray/Clash 格式 |

**工作原理**：
- 脚本自动下载 [mihomo](https://github.com/MetaCubeX/mihomo)（Clash Meta 内核）
- 自动拉取订阅并选择最快的可用节点
- 启动本地 HTTP 代理（`http://127.0.0.1:7890`）
- Playwright 通过本地代理访问 AgentRouter

**优点**：
- ✅ 只需配置一个 Secret
- ✅ 自动选择最快节点
- ✅ 支持多种协议（VMess/Trojan/SS/SSR/VLESS）
- ✅ 节点失效自动切换

---

**方式 2：使用 HTTP/SOCKS5 代理**

如果你有现成的 HTTP/SOCKS5 代理：

| Name | Value | 示例 |
|------|-------|------|
| `PROXY_SERVER` | 代理服务器地址 | `http://proxy.example.com:8080` 或 `socks5://proxy.example.com:1080` |
| `PROXY_USERNAME` | 代理用户名 | `your-proxy-username`（如果需要认证） |
| `PROXY_PASSWORD` | 代理密码 | `your-proxy-password`（如果需要认证） |

#### Telegram 通知（可选）：

| Name | Value | 说明 |
|------|-------|------|
| `TG_BOT_TOKEN` | Bot Token | 从 [@BotFather](https://t.me/BotFather) 获取 |
| `TG_CHAT_ID` | Chat ID | 你的 Telegram Chat ID |

### 3. 启用 GitHub Actions

1. 前往仓库的 **Actions** 标签页
2. 点击 **I understand my workflows, go ahead and enable them**
3. 脚本将在每天北京时间 10:00 自动运行

### 4. 手动测试运行

前往 **Actions** → 选择 **Ayrouter Daily Check-in** → 点击 **Run workflow**

## 🔧 本地测试

```bash
# 安装依赖
pip install requests playwright
playwright install chromium

# 设置环境变量
export USERNAME="your-email@example.com"
export PASSWORD="your-password"
export PROXY_SERVER="http://your-proxy:port"  # 可选
export PROXY_USERNAME="proxy-user"             # 可选
export PROXY_PASSWORD="proxy-pass"             # 可选

# 运行脚本
python app.py
```

## 📋 工作原理

1. **登录即签到**：AgentRouter 的签到机制是"登录即完成签到"
2. **浏览器自动化**：使用 Playwright 模拟真实浏览器登录
3. **代理绕过 WAF**：通过住宅代理 IP 避免触发阿里云 WAF 滑块验证
4. **每日自动运行**：GitHub Actions 定时任务

## ⚠️ 关于 WAF 验证

AgentRouter 使用了阿里云 WAF，在以下情况会触发滑块验证：
- GitHub Actions 等云服务 IP
- 数据中心 IP
- 频繁请求的 IP

**解决方案**：
1. ✅ **推荐**：配置住宅代理 IP（稳定可靠）
2. ⚠️ 备选：使用 Session Cookie 模式（需定期手动更新）

## 🛠️ 常见问题

### Q: 为什么需要代理？
A: GitHub Actions 的 IP 会被 AgentRouter 的 WAF 识别为机器人，触发滑块验证。使用住宅代理可以绕过这个检测。

### Q: 代理服务推荐？
A: 
- **✨ 推荐**：使用机场订阅（配置最简单）
- **Smartproxy**：性价比高，适合个人使用
- **BrightData**：质量最好，但价格较贵
- **IPRoyal**：价格便宜，中等质量

### Q: 如何获取订阅链接？
A:
1. 从你的机场（VPN 服务商）获取订阅链接
2. 通常在"订阅中心"或"客户端配置"页面
3. 支持 V2Ray/Clash 格式的订阅链接
4. 链接格式通常是 `https://xxx.com/api/v1/client/subscribe?token=...`

### Q: 不想用代理怎么办？
A: 可以改用 Session Cookie 模式，但需要每 30 天手动更新一次 Cookie。

### Q: 如何获取 Telegram Chat ID？
A: 
1. 向 [@userinfobot](https://t.me/userinfobot) 发送任意消息
2. Bot 会返回你的 Chat ID

### Q: 脚本运行失败怎么办？
A: 
1. 查看 Actions 运行日志
2. 检查是否配置了代理
3. 确认账号密码是否正确
4. 查看是否有错误截图（`page_error.png`）

## 📜 更新日志

- **2026-08-07**: 添加代理支持，绕过 WAF 验证
- **2026-08-07**: 改为账号密码登录模式
- **2026-08-06**: 初始版本

## 📄 许可证

MIT License
