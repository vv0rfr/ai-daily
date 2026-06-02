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

## 公众号配置

### 前置条件

- 已注册的微信公众号（个人订阅号即可）
- 已绑定管理员微信号

### 获取凭证

1. 登录 [微信开发者平台](https://developers.weixin.qq.com/platform)
2. 进入 **我的业务** → 点击你的公众号
3. 在 **基础信息** 或 **开发密钥** 区域：
   - 复制 **AppID**
   - 点击 **重置** 获取 **AppSecret**（仅显示一次，立即保存）

### 配置 IP 白名单

1. 在 **微信开发者平台** → 公众号详情页 → **IP 白名单**
2. 添加你的本地 IP（运行脚本的机器）
3. 如用 GitHub Actions，需添加 GitHub Actions 的出口 IP 范围

### 注意事项

- 个人订阅号 **无自动发布权限**（`freepublish/submit` 返回 48001）
- 草稿会自动提交到 **草稿箱**，需手动登录公众号后台发布
- `thumb_media_id` 参数实际为必填，即使文档标注非必填
- 订阅号每天只能群发 1 次
- JSON 序列化需用 `ensure_ascii=False`，否则中文显示为乱码

---

## 本地自动化

### Windows 任务计划程序

1. 打开"任务计划程序"
2. 创建基本任务
3. 设置触发器：每天 8:00
4. 操作：启动程序
   - 程序：`python`
   - 参数：`main.py ai --publish`
   - 起始于：`C:\Users\Lenovo\Desktop\ai-daily`

### Linux/Mac Crontab

```bash
# 编辑 crontab
crontab -e

# 添加（每天北京时间 8:00 运行，UTC+8）
0 0 * * * cd /path/to/ai-daily && python main.py ai --publish
```

---

## GitHub Pages（用于"阅读原文"跳转）

1. 进入仓库 Settings → Pages
2. Source: **Deploy from a branch**
3. Branch: `main` → `/ (root)`
4. URL: `https://vv0rfr.github.io/ai-daily/output/{日期}-{模式}.html`

---

## Server酱配置

1. 访问 https://sct.ftqq.com/
2. 微信扫码登录
3. 复制 SendKey
4. 添加到 GitHub Secrets 的 `SERVERCHAN_KEY`

配置后，每次日报生成会自动推送微信通知。

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

### Q: 公众号草稿创建失败 40007？
A: 需要上传封面图获取 `thumb_media_id`，代码已默认生成 `templates/thumb.jpg`。

### Q: 发布到微信显示中文乱码？
A: JSON 序列化需使用 `ensure_ascii=False`，代码已修复。
