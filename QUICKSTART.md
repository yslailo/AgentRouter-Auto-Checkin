# 🚀 快速开始指南

## 📦 你已经拥有的完整可执行版本

所有代码已经改造完成，可以直接使用！

---

## ⚡ 方案选择

### 选项 A：直接部署到 GitHub Actions（推荐）

**适合场景**：你信任代码，想直接自动化运行

**步骤**：
1. 在 GitHub 仓库配置 2 个 Secrets：
   - `USERNAME` = 你的 AgentRouter 邮箱
   - `PASSWORD` = 你的 AgentRouter 密码

2. 提交代码并推送：
   ```bash
   git add .
   git commit -m "改为账号密码登录模式"
   git push
   ```

3. 前往 Actions → 手动触发运行测试

**结果**：每天北京时间 10:00 自动签到

---

### 选项 B：先本地测试，再部署（保守）

**适合场景**：想先确认脚本能正常工作

**步骤**：

#### 1. 安装依赖
```bash
pip install requests playwright
playwright install chromium
```

#### 2. 本地测试（任选一种）

**方法 1：使用测试脚本（最简单）**
```bash
# 1. 用编辑器打开 test_local.py
# 2. 修改第 9-10 行的账号密码
# 3. 运行
python test_local.py
```

**方法 2：命令行直接测试**
```bash
# Windows
set USERNAME=your-email@example.com
set PASSWORD=your-password
python app.py

# Linux/Mac
export USERNAME=your-email@example.com
export PASSWORD=your-password
python app.py
```

#### 3. 确认成功后，按选项 A 部署到 GitHub

---

## 📋 GitHub Secrets 配置位置

```
你的仓库 → Settings → Secrets and variables → Actions → New repository secret
```

### 必须配置（2 个）：
- **Name**: `USERNAME`, **Value**: 你的 AgentRouter 邮箱
- **Name**: `PASSWORD`, **Value**: 你的 AgentRouter 密码

### 可选配置（Telegram 通知）：
- **Name**: `TG_BOT_TOKEN`, **Value**: 你的 Bot Token
- **Name**: `TG_CHAT_ID`, **Value**: 你的 Chat ID

---

## ✅ 成功标志

运行成功时，你会看到：

```
[时间] [INFO] ✅ 登录成功！用户 ID: xxxxx, 用户名: xxx
[时间] [INFO] 登录前签到状态: 未签到
[时间] [INFO] 初始余额: X.XX$
[时间] [INFO] 🎁 通过登录完成签到
[时间] [INFO] === 脚本执行完毕 ===
```

如果今天已经签到过：
```
[时间] [INFO] 登录前签到状态: 已签到
[时间] [INFO] ✅ 今日已签到过（登录前）
```

---

## 🔧 与旧版本的区别

| 项目 | 旧版本（SESSION 模式） | 新版本（密码登录模式） |
|------|----------------------|---------------------|
| 环境变量 | `USER_ID`, `SESSION` | `USERNAME`, `PASSWORD` |
| 签到方式 | Cookie + API 签到接口 | 账号密码登录（登录即签到） |
| Session 管理 | 需定期更新 SESSION | 无需管理，每次重新登录 |
| 适用站点 | 有独立签到 API 的站点 | 登录即签到的站点（如 AgentRouter） |

---

## ❓ 常见问题

### Q1: 我需要删除旧的 Secrets 吗？
**A**: 建议删除旧的 `USER_ID` 和 `SESSION`，但不删除也不影响运行。

### Q2: 密码会泄露吗？
**A**: GitHub Secrets 是加密存储的，不会在日志中显示。脚本中密码也做了脱敏处理。

### Q3: 可以多账号签到吗？
**A**: 当前版本只支持单账号。如需多账号，可以使用 `newapi-checkin` 项目（在 `newapi-checkin/` 目录）。

### Q4: 什么时候自动运行？
**A**: 每天北京时间 10:00（UTC 02:00）。可在 `.github/workflows/checkin.yml` 修改 cron 时间。

### Q5: 如何查看运行日志？
**A**: 前往仓库 → Actions → 选择最近的运行 → 展开 "Run check-in script" 查看详细日志。

---

## 📞 需要帮助？

1. 查看详细检查清单：`DEPLOY_CHECKLIST.md`
2. 查看完整文档：`README.md`
3. 查看 GitHub Actions 运行日志获取错误详情

---

**现在你可以出门了！回来后按照上面的步骤操作即可。** 🎉
