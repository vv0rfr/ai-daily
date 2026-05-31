# 部署指南

## GitHub Actions 自动化配置

### 1. Fork 仓库

点击右上角 Fork 按钮，将仓库复制到你的账号下。

### 2. 配置 Secrets

进入仓库 → Settings → Secrets and variables → Actions → New repository secret

| Secret 名称 | 必填 | 说明 |
|-------------|------|------|
| `ANTHROPIC_API_KEY` | 否 | Claude API 密钥，用于 AI 改写文章（不配则用模板生成） |
| `WECHAT_APP_ID` | 否 | 微信公众号 AppID |
| `WECHAT_APP_SECRET` | 否 | 微信公众号 AppSecret |
| `SERVERCHAN_KEY` | 否 | Server酱推送 Key，用于微信通知 |

### 3. 启用 Actions

进入仓库 → Actions → 点击 "I understand my workflows, go ahead and enable them"

### 4. 测试运行

进入 Actions → AI Daily Report → Run workflow → 选择模式 → Run workflow

---

## 本地自动化

### Windows 任务计划程序

1. 打开"任务计划程序"
2. 创建基本任务
3. 设置触发器：每天 8:00
4. 操作：启动程序
   - 程序：`python`
   - 参数：`main.py ai`
   - 起始于：`C:\Users\Lenovo\Desktop\ai-daily`

### Linux/Mac Crontab

```bash
# 编辑 crontab
crontab -e

# 添加（每天北京时间 8:00 运行，UTC+8）
0 0 * * * cd /path/to/ai-daily && python main.py ai
```

---

## Server酱配置

1. 访问 https://sct.ftqq.com/
2. 微信扫码登录
3. 复制 SendKey
4. 添加到 GitHub Secrets 的 `SERVERCHAN_KEY`

配置后，每次日报生成会自动推送微信通知。

---

## 公众号配置（可选）

### 前置条件

- 认证的微信公众号（订阅号或服务号）
- 已绑定管理员微信号

### 获取凭证

1. 登录微信公众平台
2. 开发 → 基本配置
3. 复制 AppID 和 AppSecret
4. 配置 IP 白名单（需要 GitHub Actions 的出口 IP）

### 注意事项

- 订阅号每天只能群发 1 次
- 服务号每月 4 次
- 文章需要人工审核后才会发布

---

## 常见问题

### Q: RSS 源抓取失败？

A: 部分源可能需要翻墙或有频率限制，系统会自动跳过失败的源。

### Q: 如何添加新的 RSS 源？

A: 编辑 `config.py`，在 `AI_FEEDS` 或 `TECH_FEEDS` 字典中添加。

### Q: 如何修改定时时间？

A: 编辑 `.github/workflows/daily.yml` 中的 cron 表达式。当前是 UTC 00:00（北京时间 8:00）。

### Q: 如何只生成不发布？

A: 不配置公众号 Secrets 即可，系统会跳过发布步骤。
