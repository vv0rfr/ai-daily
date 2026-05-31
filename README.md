# AI 日报生成器

自动抓取多源 AI / 科技资讯，生成公众号文章草稿和 HTML 阅读页。

## 使用方法

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 API Key（可选，不配则用模板生成）
cp .env.example .env
# 编辑 .env 填入 ANTHROPIC_API_KEY

# 运行
python main.py ai      # AI 垂直日报
python main.py tech    # 科技综合日报
python main.py all     # 全部合并

# 高级选项
python main.py ai --publish    # 生成并发布到公众号
python main.py ai --no-notify  # 不发送通知
```

输出文件在 `output/` 目录下：
- `{日期}-{模式}.md` — Markdown 文章（可粘贴到公众号）
- `{日期}-{模式}.html` — 紧凑布局阅读页（浏览器打开）

## 自动化部署

### GitHub Actions（推荐）

1. Fork 本仓库
2. 在仓库 Settings → Secrets 中添加：
   - `ANTHROPIC_API_KEY` — Claude API 密钥（可选）
   - `WECHAT_APP_ID` — 公众号 AppID（可选）
   - `WECHAT_APP_SECRET` — 公众号 AppSecret（可选）
   - `SERVERCHAN_KEY` — Server酱推送 Key（可选）
3. 启用 GitHub Actions

每天北京时间 8:00 自动运行，也可手动触发。

### 通知配置

使用 [Server酱](https://sct.ftqq.com/) 推送微信通知：
1. 注册并获取 SendKey
2. 添加到 GitHub Secrets 的 `SERVERCHAN_KEY`

### 公众号自动发布

需要认证的微信公众号：
1. 在公众号后台获取 AppID 和 AppSecret
2. 配置 IP 白名单（GitHub Actions 的 IP）
3. 添加到 GitHub Secrets

详细配置请查看 [DEPLOY.md](DEPLOY.md)

## 数据源

**AI 频道：**
- AI HOT 精选 / 日报
- Simon Willison 博客
- The Decoder

**科技频道：**
- 36氪、Hacker News、Product Hunt、掘金、IT之家、少数派

## 功能

- 多源 RSS 抓取，自动去重
- 杂糅合集过滤（"8点1氪"类文章）
- 24 小时时间过滤
- AI 相关性过滤（AI 频道）
- 中英文语言切换
- 可访问源跳转按钮
- 4 种卡片风格紧凑布局

## 流程

```
RSS 数据源 → 筛选过滤 → 分类排序 → 文章生成 → HTML 阅读页
```
