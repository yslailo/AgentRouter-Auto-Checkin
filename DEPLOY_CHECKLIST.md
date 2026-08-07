# 🚀 部署检查清单

## ✅ 代码改动确认

### 1. 核心脚本 (app.py)
- [x] 移除 `USER_ID` 和 `SESSION` 环境变量
- [x] 新增 `USERNAME` 和 `PASSWORD` 环境变量
- [x] 实现 `login_with_password()` 函数
- [x] 登录接口：`POST /api/user/login?turnstile=`
- [x] 登录响应处理 `checked_in` 字段（判断登录前是否已签到）
- [x] 保留 WAF Cookie 获取逻辑（Playwright）
- [x] 保留 Telegram 通知功能
- [x] 错误处理和日志输出

### 2. GitHub Actions 工作流 (.github/workflows/checkin.yml)
- [x] 环境变量从 `USER_ID`, `SESSION` 改为 `USERNAME`, `PASSWORD`
- [x] 依赖安装：`requests`, `playwright`, `pynacl`
- [x] Playwright Chromium 浏览器安装
- [x] 定时任务：每天 UTC 02:00（北京时间 10:00）
- [x] 手动触发支持

### 3. 文档更新 (README.md)
- [x] 更新 Secrets 配置说明
- [x] 说明"登录即签到"模式
- [x] 更新部署步骤
- [x] 添加本地测试说明

## 📋 部署前确认事项

### GitHub Secrets 配置（必做）

请在 GitHub 仓库设置中配置以下 Secrets：

1. **删除旧的 Secrets**（如果存在）：
   - [ ] 删除 `USER_ID`
   - [ ] 删除 `SESSION`

2. **添加新的 Secrets**（必须）：
   - [ ] `USERNAME` = 你的 AgentRouter 登录邮箱
   - [ ] `PASSWORD` = 你的 AgentRouter 登录密码

3. **可选 Secrets**（推荐配置）：
   - [ ] `TG_BOT_TOKEN` = Telegram Bot Token
   - [ ] `TG_CHAT_ID` = Telegram Chat ID

### 配置路径
```
仓库 → Settings → Secrets and variables → Actions → New repository secret
```

## 🧪 测试步骤

### 方法一：本地测试（推荐先做）

```bash
# 1. 安装依赖
pip install requests playwright
playwright install chromium

# 2. 修改 test_local.sh 中的账号密码
# 3. 运行测试
bash test_local.sh

# 或者直接运行（Windows）
set USERNAME=your-email@example.com
set PASSWORD=your-password
python app.py
```

**预期输出：**
```
[时间] [INFO] ==================================================
[时间] [INFO] AgentRouter 登录签到脚本启动
[时间] [INFO] 时间: 2026-08-07 xx:xx:xx
[时间] [INFO] 用户名: your-email@example.com
[时间] [INFO] ==================================================
[时间] [INFO] 使用浏览器获取 WAF Cookie（访问 https://agentrouter.org/login）...
[时间] [INFO] 获取到 X 个 WAF Cookie: [...]
[时间] [INFO] 已设置 X 个 WAF Cookie: [...]
[时间] [INFO] 使用账号密码登录...
[时间] [INFO] 登录接口响应: HTTP 200
[时间] [INFO] ✅ 登录成功！用户 ID: xxxxx, 用户名: xxx
[时间] [INFO] 用户名: xxx
[时间] [INFO] 用户 ID: xxxxx
[时间] [INFO] 登录前签到状态: 未签到/已签到
[时间] [INFO] 初始余额: X.XX$
[时间] [INFO] 等待 3 秒后重新获取余额...
[时间] [INFO] 刷新后余额: X.XX$
[时间] [INFO] 🎁/✅ 通过登录完成签到/今日已签到过
[时间] [INFO] === 脚本执行完毕 ===
```

### 方法二：GitHub Actions 测试

1. **提交代码**：
   ```bash
   git add .
   git commit -m "改为账号密码登录模式"
   git push
   ```

2. **配置 Secrets**（见上方）

3. **手动触发运行**：
   - 前往仓库 → Actions
   - 选择 "Ayrouter Daily Check-in" 工作流
   - 点击 "Run workflow" → "Run workflow"

4. **查看运行日志**：
   - 查看日志输出是否正常
   - 确认登录和签到状态

## ❌ 常见问题排查

### 1. 登录失败
**错误信息**：`登录失败: HTTP 401` 或 `账号或密码错误`

**解决方法**：
- [ ] 检查 `USERNAME` 是否正确（通常是邮箱）
- [ ] 检查 `PASSWORD` 是否正确
- [ ] 在浏览器中手动登录一次，确认账号可用
- [ ] 检查是否有特殊字符需要转义

### 2. WAF Cookie 获取失败
**错误信息**：`未获取到 WAF Cookie`

**解决方法**：
- [ ] 确认网络可以访问 `https://agentrouter.org`
- [ ] 确认 Playwright Chromium 安装成功
- [ ] 这不影响登录，可以继续运行

### 3. Telegram 通知未收到
**解决方法**：
- [ ] 检查 `TG_BOT_TOKEN` 格式是否正确
- [ ] 检查 `TG_CHAT_ID` 是否正确（纯数字）
- [ ] 确认已将 Bot 添加到聊天中
- [ ] 查看日志中是否有 Telegram 发送错误信息

### 4. GitHub Actions 权限问题
**错误信息**：`secrets.USERNAME not found`

**解决方法**：
- [ ] 确认 Secrets 已正确配置
- [ ] Secrets 名称必须完全匹配（区分大小写）
- [ ] 重新运行工作流

## 📊 成功标志

运行成功的标志：
- [x] 脚本执行完毕，退出码 0
- [x] 日志显示"登录成功"
- [x] 日志显示签到状态（已签到或完成签到）
- [x] 余额显示正常
- [x] Telegram 收到通知（如已配置）

## 🎯 最终确认

在你出门前，请确认：

1. **本地测试**：
   - [ ] 运行 `test_local.sh` 或手动测试成功

2. **GitHub 配置**：
   - [ ] Secrets 已配置（`USERNAME`, `PASSWORD`）
   - [ ] 代码已提交推送
   - [ ] 手动触发 Actions 成功运行

3. **通知配置**（可选）：
   - [ ] Telegram Bot Token 已配置
   - [ ] 收到测试通知

## 📝 备注

- 脚本每天自动运行时间：**北京时间 10:00**（UTC 02:00）
- 如需修改时间，编辑 `.github/workflows/checkin.yml` 中的 cron 表达式
- 登录即签到，无需额外调用签到接口
- 脚本会自动清理旧的运行记录（保留最新 1 条）

---

**如有问题，请查看 GitHub Actions 运行日志获取详细错误信息。**
