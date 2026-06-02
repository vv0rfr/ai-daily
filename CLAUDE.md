# AI 日报生成器 — CLAUDE.md

## 项目概述
Python 项目，每日自动抓取多源 AI/科技 RSS 资讯，生成 Markdown 文章和 HTML 阅读页，自动提交到微信公众号草稿箱。

## 快速命令
```bash
python main.py ai           # AI 垂直日报（默认）
python main.py ai --publish # 生成并提交到公众号草稿箱
python main.py tech         # 科技综合日报
python main.py all          # 全频道日报
streamlit run app_streamlit.py  # 启动 Web 管理界面（http://localhost:8501）
```

## 关键文件
| 文件 | 用途 |
|------|------|
| `main.py` | 入口，CLI 调度 |
| `app_streamlit.py` | Streamlit Web 界面（科幻风、中英文切换、卡片排版） |
| `fetcher.py` | RSS 抓取 + B站视频搜索 |
| `filter.py` | 去重、时效过滤、分类、AI 相关性 |
| `writer.py` | 文章生成（Claude API 或模板） |
| `publisher.py` | 微信公众号 API 发布（草稿箱） |
| `config.py` | 数据源 + 所有配置常量和环境变量 |
| `notifier.py` | Server酱 微信通知 |
| `.github/workflows/daily.yml` | GitHub Actions 定时任务 |

## 配置（.env）
```
DEEPSEEK_API_KEY=     # 推荐，DeepSeek API，AI 写文章（比模板质量高）
ANTHROPIC_API_KEY=    # 可选，Claude API，DeepSeek 的备用
WECHAT_APP_ID=        # 公众号 AppID
WECHAT_APP_SECRET=    # 公众号 AppSecret
SERVERCHAN_KEY=       # Server酱通知
```

## GitHub Secrets（同名）
- `DEEPSEEK_API_KEY`, `ANTHROPIC_API_KEY`, `WECHAT_APP_ID`, `WECHAT_APP_SECRET`, `SERVERCHAN_KEY`

## 架构流程
```
RSS 数据源 → Fetcher → Filter → Writer → Publisher → 公众号草稿箱
                                    ↘ HTML 阅读页 → GitHub Pages
```

## 红线 / 注意事项
- `thumb_media_id` 微信 API 实际为必填，不要省略（否则 40007）
- 个人订阅号无 `freepublish/submit` 权限（48001），只能到草稿箱手动发布
- JSON 序列化必须 `ensure_ascii=False`，否则中文乱码
- 每日 8:00 GitHub Actions 自动运行（UTC 00:00）
- 本地发布需 IP 在白名单内（当前：221.13.206.75）

## TOP_N 配置
- `config.py` 中 `TOP_N = 5`（文章），`VIDEO_TOP_N = 3`（视频）
- 精简排版，提升可读性

## 公众号信息
- 个人订阅号，无自动群发权限
- 草稿箱 API `/cgi-bin/draft/add` 可正常使用
- "阅读原文"链接指向 GitHub Pages（https://vv0rfr.github.io/ai-daily/output/{日期}-{模式}.html）

## 深入文档
- [DEPLOY.md](DEPLOY.md) — 部署和配置详情
- [README.md](README.md) — 功能概览
