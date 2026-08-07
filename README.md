## 🚀 AgentRouter 自动签到（GitHub Actions）

这是一个基于 GitHub Actions 的自动化脚本，用于定时登录签到 [AgentRouter](https://agentrouter.org) 服务。

> **重要说明**：AgentRouter 采用**登录即签到**的模式，没有独立的签到 API。本脚本通过账号密码登录来完成每日签到。

━━━━━━━━━━━━━━━━━━━━━━

### 🔐 Secrets 配置说明

| Secret 名称         | 是否必填 | 说明                                              |
|---------------------|----------|---------------------------------------------------|
| USERNAME           | ✅ 必填  | AgentRouter 登录账号（通常是邮箱）                      |
| PASSWORD           | ✅ 必填  | AgentRouter 登录密码                                  |
| TG_BOT_TOKEN       | ❌ 可选  | Telegram Bot Token（用于发送通知）                     |
| TG_CHAT_ID         | ❌ 可选  | Telegram Chat ID（接收通知的用户或群组 ID）             |

━━━━━━━━━━━━━━━━━━━━━━

## 📋 部署步骤

### 1. Fork 本项目
Fork 本项目到你的 GitHub 账户，然后在 `Actions` 菜单中启用工作流。

### 2. 配置 Secrets
在仓库的 `Settings` ➡ `Secrets and variables` ➡ `Actions` 中添加以下 Secrets：

- **USERNAME**：你的 AgentRouter 登录邮箱
- **PASSWORD**：你的 AgentRouter 登录密码
- **TG_BOT_TOKEN**（可选）：Telegram 机器人 Token
- **TG_CHAT_ID**（可选）：Telegram 聊天 ID

### 3. 手动测试运行
前往 `Actions` 菜单，选择工作流并手动触发一次，确认配置正确。

━━━━━━━━━━━━━━━━━━━━━━

## ⏰ 运行时间

- **定时运行**：每天北京时间 10:00（UTC 02:00）自动执行
- **手动触发**：可在 Actions 页面手动触发运行

━━━━━━━━━━━━━━━━━━━━━━

## 🔔 Telegram 通知配置（可选）

如需接收签到通知，需要配置 Telegram Bot：

### 1. 创建 Telegram Bot
1. 在 Telegram 中搜索 `@BotFather`
2. 发送 `/newbot` 并按提示创建 Bot
3. 保存 Bot Token（格式：`1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`）

### 2. 获取 Chat ID
1. 在 Telegram 中搜索 `@userinfobot`
2. 发送任意消息，获取你的 Chat ID（纯数字）

### 3. 配置到 Secrets
将 Bot Token 和 Chat ID 分别配置到 `TG_BOT_TOKEN` 和 `TG_CHAT_ID`。

━━━━━━━━━━━━━━━━━━━━━━

## 🛠️ 本地测试

如需本地测试脚本：

```bash
# 安装依赖
pip install requests playwright
playwright install chromium

# 设置环境变量并运行
export USERNAME="your-email@example.com"
export PASSWORD="your-password"
python app.py
```

━━━━━━━━━━━━━━━━━━━━━━

## 📝 工作原理

1. 使用 Playwright 获取 WAF Cookie（绕过 Cloudflare 等防护）
2. 使用账号密码调用 `/api/user/login` 接口登录
3. 登录成功后，服务端自动完成签到（登录即签到）
4. 获取账户余额信息并发送通知

━━━━━━━━━━━━━━━━━━━━━━

## ⚠️ 注意事项

- 本项目仅供学习交流使用，请遵守 AgentRouter 服务条款
- 密码存储在 GitHub Secrets 中，相对安全，但仍建议使用独立密码
- 如遇登录失败，请检查账号密码是否正确
- 建议开启 Telegram 通知以便及时了解签到状态

━━━━━━━━━━━━━━━━━━━━━━

## 📜 License

MIT License
