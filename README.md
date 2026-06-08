# AI 日报全自动化生成系统

> 作者：张尧 | 独立开发 | Python + DeepSeek API + GitHub Actions

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![DeepSeek](https://img.shields.io/badge/AI-DeepSeek%20V4-4A6CF7)](https://deepseek.com)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-CI/CD-2088FF)](https://github.com/features/actions)
[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Online-brightgreen)](https://vv0rfr.github.io/ai-daily/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

多源 RSS 资讯抓取 → AI 智能写作 → 自动配图 → 公众号发布 + GitHub Pages 归档，全链路无人值守。从学习 Python 到系统上线仅用两周，已稳定运行 6 个月+，产出 180+ 篇内容，人工介入率低于 5%。

**在线体验：** https://vv0rfr.github.io/ai-daily/

---

## 功能列表

| 功能 | 说明 |
|------|------|
| 多源资讯采集 | RSS 并行抓取 Hugging Face、Simon Willison、36氪、Hacker News、Product Hunt 等多源，支持自定义扩展 |
| AI 智能写作 | DeepSeek V4 改写 RSS 资讯为高质量日报文章（首选），Claude API 备用降级，无 API Key 时走模板兜底 |
| 自动配图 | 根据文章标签自动选择风格化封面图 |
| 质量评估与修正 | AI 自评文章质量，不合格自动重写，双重保障产出质量 |
| 定时自动化 | GitHub Actions 每日 8:00 自动触发，全流程无人值守 |
| 异常告警 | 企微 + 邮件双通道告警，系统异常实时感知 |
| 双端发布 | 自动提交微信公众号草稿箱 + 同步 GitHub Pages 归档 |
| 管理面板 | Streamlit Web 界面，在线查看日志、重跑任务 |

---

## 架构设计

```
RSS 数据源 ──→ fetcher.py ──→ filter.py ──→ writer.py ──→ publisher.py
                    │              │              │
              并行抓取         24h 时效过滤     AI 文章生成
              多源 RSS         AI 相关性判断    DeepSeek 首选
              B站视频搜索       杂糅去重        Claude 备用降级
                                              模板兜底
```

### 核心流程

1. **采集** — `fetcher.py` 并行抓取多源 RSS，支持视频搜索
2. **过滤** — `filter.py` 去重 + 24h 时效过滤 + AI 相关性判断 + 杂糅合集去重
3. **写作** — `writer.py` 优先调用 DeepSeek V4 生成文章，失败自动降级到 Claude API，再失败走模板，三段容错
4. **发布** — `publisher.py` 自动提交公众号草稿箱 + 推送 GitHub Pages
5. **通知** — `notifier.py` Server酱 推送日报生成状态

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

# Streamlit 管理面板
streamlit run app_streamlit.py
# 访问 http://localhost:8501
```

---

## 项目亮点

### 三段式 AI 容错流水线
DeepSeek V4 为主力模型，不可用时自动降级到 Claude API，仍不可用时走模板生成。三段兜底保障每日日报不中断，零人工值守。

### AI 质量自评 + 自动修正
每篇文章生成后由 AI 自评质量，不合格自动触发二次修正，无需人工干预。稳定运行 6 个月，人工介入率低于 5%。

### 自动化运维体系
- GitHub Actions 定时触发（每日 8:00）
- 企微 + 邮件双通道异常告警
- systemd 进程守护，崩溃自动重启
- 可用率 99%+

### 独立系统设计能力
从学习 Python 到系统上线仅用两周。独立完成架构设计、技术选型（Flask + DeepSeek + GitHub Actions）、服务器搭建（Nginx 反向代理 + systemd）、全流程编码。

---

## 项目结构

```
ai-daily/
├── main.py                 # CLI 入口
├── app_streamlit.py        # Streamlit 管理面板
├── fetcher.py              # RSS 抓取（并行多源）
├── filter.py               # 智能过滤（时效/AI相关性/去重）
├── writer.py               # AI 文章生成（三段容错）
├── publisher.py            # 公众号发布 + GitHub Pages
├── imager.py               # 自动配图
├── notifier.py             # 微信告警通知
├── config.py               # 数据源配置
├── scripts/
│   └── generate_index.py   # 归档页生成
├── output/                 # 生成文件
├── .github/workflows/      # CI/CD 自动部署
└── DEPLOY.md               # 部署文档
```

---

## 技术栈

- **语言：** Python 3.11
- **AI：** DeepSeek V4 API（首选）/ Claude API（备用）
- **自动化：** GitHub Actions
- **Web 界面：** Streamlit
- **数据采集：** Feedparser（RSS）
- **发布：** 微信公众平台 API / GitHub Pages
- **通知：** Server酱 / 企微 / 邮件
- **部署：** Nginx + systemd（Linux 服务器）

---

## 配置

### 数据源
编辑 `config.py`，支持添加自定义 RSS 源。

### 文章数量
```python
TOP_N = 5        # 文章数量
VIDEO_TOP_N = 3  # 视频数量
```

### 环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | 是 |
| `ANTHROPIC_API_KEY` | Claude API 密钥（备用） | 否 |
| `WECHAT_APP_ID` | 公众号 AppID | 否 |
| `WECHAT_APP_SECRET` | 公众号 AppSecret | 否 |
| `SERVERCHAN_KEY` | Server酱 推送 Key | 否 |
