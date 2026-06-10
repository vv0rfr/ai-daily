# AI 日报生成器 — CLAUDE.md

## 项目概述
Python 项目，每日自动抓取多源 AI/科技 RSS 资讯，经 LLM 分类后生成双语 Markdown 文章和暖米色编辑风 HTML 阅读页，提交到微信公众号草稿箱 + GitHub Pages 归档。

## 快速命令
```bash
python main.py ai           # AI 垂直日报（默认）
python main.py ai --publish # 生成并提交到公众号草稿箱
python main.py tech         # 科技综合日报
python main.py all          # 全频道日报
python main.py stats        # 数据库统计
python main.py check-sources # 诊断 RSS 源可用性
```

## 关键文件
| 文件 | 用途 |
|------|------|
| `main.py` | 入口，CLI 调度 |
| `fetcher.py` | RSS 抓取 + B站视频搜索 + SSL 重试 |
| `filter.py` | 去重、时效过滤、LLM 分类（DeepSeek → Claude → 关键词三级降级） |
| `writer.py` | 文章生成 + 双语字段提取 + 趋势洞察 + Jinja2 HTML 渲染 + RSS feed + 历史列表页 |
| `database.py` | SQLite 持久化（runs + articles 表） |
| `config.py` | 数据源 + 所有配置常量和环境变量 |
| `imager.py` | 自动配图（Unsplash API / Picsum 兜底） |
| `publisher.py` | 微信公众号 API 发布（草稿箱） |
| `templates/daily.html` | HTML 页面 Jinja2 模板（暖米色编辑风） |
| `templates/daily.css` | 页面样式（Instrument Serif + DM Sans 字体） |
| `templates/daily.js` | 交互逻辑（语言切换、进度条、pill 导航、分享按钮） |
| `templates/index.html` | 历史日报列表页 Jinja2 模板 |
| `scripts/generate_index.py` | 生成 GitHub Pages 归档页 index.html（旧版，已迁移到 writer.py） |
| `.github/workflows/daily.yml` | GitHub Actions 定时任务 + Pages 部署 |

## 数据源（8 AI + 6 科技 + B站视频）
- AI：AI HOT（精选+日报）、Hugging Face、Simon Willison、The Decoder、机器之心、量子位、TechCrunch AI
- 科技：36氪、Hacker News、Product Hunt、掘金、IT之家、少数派
- B站：关键词搜索（config.py 中 BILIBILI_KEYWORDS）

## 配置（.env）
```
DEEPSEEK_API_KEY=     # 推荐，DeepSeek API，AI 写文章 + LLM 分类
ANTHROPIC_API_KEY=    # 可选，Claude API，DeepSeek 的备用
WECHAT_APP_ID=        # 公众号 AppID
WECHAT_APP_SECRET=    # 公众号 AppSecret
SERVERCHAN_KEY=       # Server酱通知
UNSPLASH_ACCESS_KEY=  # 可选，配图用；无则用 Picsum
```

## 架构流程
```
RSS 数据源 → Fetcher → Filter（LLM分类） → Writer（AI生成+双语） → Publisher → 公众号草稿箱
                                              ↘ HTML 阅读页（Jinja2） → GitHub Pages
                                              ↘ SQLite（runs + articles）
```

## 红线 / 注意事项
- `thumb_media_id` 微信 API 实际为必填，不要省略（否则 40007）
- 个人订阅号无 `freepublish/submit` 权限（48001），只能到草稿箱手动发布
- JSON 序列化必须 `ensure_ascii=False`，否则中文乱码
- 每日 8:00 GitHub Actions 自动运行（UTC 00:00）
- 本地发布需 IP 在白名单内（当前：221.13.206.75）
- B站 CDN 防盗链：HTML `<head>` 必须有 `<meta name="referrer" content="no-referrer">`
- SSL 证书问题：Hugging Face 等源可能 SSL 失败，fetcher 有 verify=False 重试
- 数据库连接：所有 database.py 函数用 try/finally 确保关闭连接
- Windows GBK 编码：stats 输出不能含 emoji，否则 UnicodeEncodeError

## 深入文档
- [DEPLOY.md](DEPLOY.md) — 部署和配置详情
- [README.md](README.md) — 功能概览
