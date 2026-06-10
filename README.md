# AI 日报全自动化生成系统

> 作者：张尧 | 独立开发 | Python + DeepSeek API + GitHub Actions

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![DeepSeek](https://img.shields.io/badge/AI-DeepSeek%20V4-4A6CF7)](https://deepseek.com)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-CI/CD-2088FF)](https://github.com/features/actions)
[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Online-brightgreen)](https://vv0rfr.github.io/ai-daily/)

多源 RSS 资讯抓取 → LLM 智能分类 → AI 双语写作 → 自动配图 → 公众号发布 + GitHub Pages 归档。

**在线体验：** https://vv0rfr.github.io/ai-daily/
**RSS 订阅：** https://vv0rfr.github.io/ai-daily/feed.xml

---

## 功能列表

| 功能 | 说明 |
|------|------|
| 多源资讯采集 | 8 个 AI 源 + 6 个科技源 + B站视频，共 15 个数据源 |
| LLM 智能分类 | DeepSeek → Claude → 关键词三级降级，自动归类到模型/产品/行业/论文/技巧 |
| AI 双语写作 | DeepSeek 生成中英双语标题和摘要，预翻译非运行时 |
| 趋势洞察 | AI 分析当日新闻关联性，输出中英文趋势分析 |
| 自动配图 | Unsplash API 按关键词选图，无 Key 时 Picsum 兜底 |
| SQLite 持久化 | 记录每次运行和所有文章，支持统计查询 |
| 暖米色编辑风页面 | Jinja2 模板，Instrument Serif + DM Sans 字体，深色/浅色切换 |
| 定时自动化 | GitHub Actions 每日 8:00 自动触发 |
| 今日重点 | AI 生成一句话概括，支持中英切换 |
| 阅读统计 | 自动计算字数和预计阅读时间 |
| 历史对比 | 与昨日文章数和分类变化对比 |
| 分享按钮 | 一键复制线上链接 |
| RSS 订阅 | Atom 格式 feed.xml |
| 历史归档 | 自动生成 index.html 列表页 |
| 双端发布 | 公众号草稿箱 + GitHub Pages 归档 |

---

## 架构设计

```
RSS 数据源 ──→ fetcher.py ──→ filter.py ──→ writer.py ──→ publisher.py
                    │              │              │
              并行抓取         LLM 分类       AI 文章生成
              8 AI + 6 科技    三级降级        双语字段
              B站视频搜索      时效过滤        趋势洞察
                              杂糅去重        Jinja2 HTML
                                              ↘ SQLite
```

### 核心流程

1. **采集** — `fetcher.py` 并行抓取多源 RSS，SSL 失败自动重试
2. **过滤** — `filter.py` LLM 分类 + 48h 时效过滤 + 杂糅合集去重
3. **写作** — `writer.py` DeepSeek 生成文章 + 双语字段提取 + 趋势洞察
4. **存储** — `database.py` SQLite 记录运行和文章数据
5. **渲染** — Jinja2 模板生成暖米色 HTML 页面
6. **发布** — `publisher.py` 提交公众号草稿箱 + GitHub Pages

---

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 API Key（推荐 DeepSeek）
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY

# 生成 AI 日报
python main.py ai        # AI 垂直日报
python main.py tech      # 科技综合日报
python main.py all       # 全频道日报
python main.py stats     # 查看数据库统计
python main.py check-sources  # 诊断 RSS 源
```

---

## 项目结构

```
ai-daily/
├── main.py                 # CLI 入口
├── fetcher.py              # RSS 抓取（并行多源 + SSL 重试）
├── filter.py               # LLM 分类（三级降级）
├── writer.py               # AI 文章生成 + 双语 + 趋势洞察 + HTML 渲染
├── database.py             # SQLite 持久化
├── publisher.py            # 公众号发布
├── imager.py               # 自动配图
├── config.py               # 数据源配置
├── templates/
│   ├── daily.html          # HTML 页面 Jinja2 模板
│   ├── daily.css           # 暖米色编辑风样式
│   ├── daily.js            # 交互逻辑（语言切换、进度条）
│   └── index.html          # 历史日报列表页模板
├── scripts/
│   └── generate_index.py   # 归档页生成
├── output/                 # 生成的 HTML/MD 文件
├── .github/workflows/      # GitHub Actions
└── DEPLOY.md               # 部署文档
```

---

## 技术栈

- **语言：** Python 3.11
- **AI：** DeepSeek V4 API（首选）/ Claude API（备用）
- **数据库：** SQLite
- **模板：** Jinja2
- **自动化：** GitHub Actions
- **数据采集：** Feedparser + Requests
- **发布：** 微信公众平台 API / GitHub Pages

---

## 配置

### 环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥（文章生成 + LLM 分类） | 是 |
| `ANTHROPIC_API_KEY` | Claude API 密钥（备用） | 否 |
| `WECHAT_APP_ID` | 公众号 AppID | 否 |
| `WECHAT_APP_SECRET` | 公众号 AppSecret | 否 |
| `SERVERCHAN_KEY` | Server酱 推送 Key | 否 |
| `UNSPLASH_ACCESS_KEY` | Unsplash 配图 API（可选，无则用 Picsum） | 否 |

### 数据源
编辑 `config.py` 中 `AI_FEEDS` 和 `TECH_FEEDS`，支持添加自定义 RSS 源。

### 文章数量
```python
TOP_N = 5        # 文章数量
VIDEO_TOP_N = 3  # 视频数量
```
