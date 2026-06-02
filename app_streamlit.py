"""AI 日报 — Streamlit Web 界面（科幻风）
科技感暗色主题 · 中英文切换 · 卡片式排版
"""

import os
import sys
import re
import subprocess
import urllib.parse
from datetime import datetime
from pathlib import Path

import streamlit as st

# ========== 页面配置 ==========
st.set_page_config(
    page_title="AI 日报 · 终端",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"


# ========== 工具函数 ==========

def list_daily_files() -> list[dict]:
    records = []
    for f in sorted(OUTPUT_DIR.glob("*.md"), reverse=True):
        if f.stat().st_size == 0:
            continue
        parts = f.stem.split("-", 2)
        if len(parts) < 3:
            continue
        date_str = f"{parts[0]}-{parts[1]}-{parts[2].rsplit('-', 1)[0]}"
        mode = parts[2].rsplit("-", 1)[-1] if "-" in parts[2] else "ai"
        html_path = f.with_suffix(".html")
        records.append({
            "date": date_str,
            "mode": mode,
            "md_path": str(f),
            "html_path": str(html_path) if html_path.exists() else None,
            "size": f.stat().st_size,
        })
    return records


def parse_md_article(md_text: str) -> dict:
    """解析 Markdown 日报为结构化数据"""
    lines = md_text.split("\n")
    title = ""
    overview_items = []
    sections = []

    current_section = None
    current_item = None
    in_overview = False
    after_overview = False

    for line in lines:
        # 标题
        if line.startswith("# ") and not line.startswith("## "):
            title = line[2:].strip()
            continue

        # 今日看点区域标记
        if "今日看点" in line and not line.startswith("#"):
            in_overview = True
            continue
        if in_overview and line.startswith("---"):
            in_overview = False
            after_overview = True
            continue

        # 概览条目
        if in_overview and line.strip().startswith("- "):
            overview_items.append(line.strip())
            continue

        # 分隔线后才是正文
        if not after_overview and not line.startswith("##"):
            continue

        # 分类标题 ##
        if line.startswith("## ") and not line.startswith("### "):
            if current_section:
                if current_item:
                    current_section["items"].append(current_item)
                sections.append(current_section)
            cat_name = line[3:].strip()
            # 去掉 emoji
            cat_clean = re.sub(r"[^\w一-鿿/]", "", cat_name).strip()
            current_section = {"category": cat_name, "items": []}
            current_item = None
            continue

        # 条目标题 ###
        if line.startswith("### "):
            if current_section and current_item:
                current_section["items"].append(current_item)
            current_item = {
                "title": line[4:].strip().lstrip("🎬 "),
                "summary": "",
                "source": "",
                "link": "",
                "is_video": "🎬" in line[4:],
            }
            continue

        if current_item is None:
            continue

        # 摘要（非 blockquote 的第一段文字）
        if not line.startswith(">") and line.strip() and not current_item["summary"]:
            current_item["summary"] = line.strip()
            continue

        # 来源/blockquote
        if line.startswith(">"):
            text = line.strip("> ").strip()
            if "来源" in text or "UP主" in text:
                current_item["source"] = text
            # 从 blockquote 里也提取链接
            m = re.search(r'\((https?://[^)]+)\)', text)
            if m and not current_item["link"]:
                current_item["link"] = m.group(1)
            continue

        # 链接
        m = re.search(r'\((https?://[^)]+)\)', line)
        if m and not current_item["link"]:
            current_item["link"] = m.group(1)

    # 收尾
    if current_section:
        if current_item:
            current_section["items"].append(current_item)
        sections.append(current_section)

    return {"title": title, "overview": overview_items, "sections": sections}


# ========== CSS 主题（科幻暗色） ==========

THEME_CSS = """
<style>
/* ===== 全局 ===== */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

.cyber-wrap {
    font-family: 'Inter', -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
    background: #f5f6f8;
    color: #1d1d2a;
    line-height: 1.7;
    min-height: 100vh;
    padding: 0;
    margin: 0;
    overflow-x: hidden;
}

/* ===== 顶栏 ===== */
.cyber-header {
    background: linear-gradient(135deg, #1a1a3e 0%, #2d2d5e 50%, #1a1a3e 100%);
    padding: 18px 28px 14px;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: 0 2px 16px rgba(26,26,62,0.15);
}
.cyber-header-inner {
    max-width: 1000px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
}
.cyber-logo {
    display: flex;
    align-items: center;
    gap: 12px;
}
.cyber-logo-icon {
    width: 34px; height: 34px;
    background: linear-gradient(135deg, #60a5fa, #34d399);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; font-weight: 800; color: #fff;
    box-shadow: 0 0 16px rgba(96,165,250,0.25);
}
.cyber-logo-text {
    font-size: 17px; font-weight: 700; color: #eef2ff;
    letter-spacing: 0.5px;
}
.cyber-logo-sub {
    font-size: 11px; color: #a5b4fc; font-weight: 400; margin-left: 4px;
}
.cyber-header-right {
    display: flex; align-items: center; gap: 10px;
}
.cyber-mode-badge {
    font-size: 11px; padding: 4px 12px;
    border-radius: 20px;
    background: rgba(255,255,255,0.08);
    color: #a5b4fc;
    border: 1px solid rgba(255,255,255,0.1);
    font-weight: 600;
    letter-spacing: 0.5px;
}
.cyber-lang-btn {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.12);
    color: #c7d2fe;
    padding: 5px 14px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    font-family: inherit;
}
.cyber-lang-btn:hover {
    background: rgba(96,165,250,0.15);
    border-color: rgba(96,165,250,0.3);
    color: #93c5fd;
}
.cyber-lang-btn.active {
    background: rgba(96,165,250,0.2);
    border-color: #60a5fa;
    color: #93c5fd;
}

/* ===== 内容区 ===== */
.cyber-body {
    max-width: 1000px;
    margin: 0 auto;
    padding: 24px 28px 60px;
}

/* 日期行 */
.cyber-datebar {
    display: flex; align-items: center; gap: 10px;
    margin-bottom: 20px;
    font-size: 13px; color: #6b7280;
}
.cyber-datebar .dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: #34d399; display: inline-block;
    animation: pulse-dot 2s infinite;
}
@keyframes pulse-dot {
    0%,100% { opacity: 1; }
    50% { opacity: 0.3; }
}
.cyber-datebar .live { color: #10b981; font-weight: 700; font-size: 11px; letter-spacing: 1px; }
.cyber-datebar .sep { color: #d1d5db; }

/* ===== 概览卡片 ===== */
.cyber-overview {
    background: linear-gradient(135deg, #eef2ff 0%, #f0fdf4 100%);
    border: 1px solid #e0e7ff;
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 24px;
}
.cyber-overview-title {
    font-size: 11px; font-weight: 700; color: #6366f1;
    letter-spacing: 2px; text-transform: uppercase;
    margin-bottom: 10px;
}
.cyber-overview-grid {
    display: flex; flex-direction: column; gap: 6px;
}
.cyber-ov-item {
    font-size: 13.5px; color: #374151; line-height: 1.6;
    padding: 3px 0;
}
.cyber-ov-item strong {
    color: #1e1b4b; font-weight: 600;
}

/* ===== 分类标题 ===== */
.cyber-cat-title {
    font-size: 15px; font-weight: 700; color: #1e1b4b;
    margin: 28px 0 14px; padding-bottom: 6px;
    border-bottom: 2px solid #e0e7ff;
    display: flex; align-items: center; gap: 8px;
}

/* ===== 文章卡片 ===== */
.cyber-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 10px;
    transition: all 0.18s;
}
.cyber-card:hover {
    border-color: #c7d2fe;
    box-shadow: 0 2px 12px rgba(99,102,241,0.08);
    transform: translateY(-1px);
}
.cyber-card-title {
    font-size: 15px; font-weight: 600; color: #1e1b4b;
    line-height: 1.5; margin-bottom: 6px;
    word-break: break-word;
}
.cyber-card-title .en-text {
    font-weight: 500;
    word-break: break-word;
    hyphens: auto;
}
.cyber-card-summary {
    font-size: 13px; color: #6b7280;
    line-height: 1.6; margin-bottom: 0;
    word-break: break-word;
}
.cyber-card-summary-wrap {
    display: flex; justify-content: space-between; align-items: flex-end;
    gap: 12px;
}
.cyber-card-link {
    color: #6366f1; text-decoration: none;
    font-size: 12px; font-weight: 600; white-space: nowrap;
    padding: 3px 10px; border-radius: 6px;
    transition: all 0.15s;
    flex-shrink: 0;
}
.cyber-card-link:hover {
    background: #eef2ff;
    color: #4f46e5;
}
.cyber-card-source {
    font-size: 11px; color: #9ca3af; margin-top: 6px; display: inline-block;
}

/* ===== 视频卡片 ===== */
.cyber-card.video {
    border-left: 3px solid #8b5cf6;
    background: linear-gradient(135deg, #faf5ff 0%, #ffffff 100%);
}
.cyber-card.video .cyber-card-title::before {
    content: "▶ ";
    color: #8b5cf6;
    font-size: 12px;
}

.cyber-footer {
    text-align: center; font-size: 11px; color: #d1d5db;
    padding: 28px 0 12px;
    border-top: 1px solid #f3f4f6;
    margin-top: 28px;
}

/* ===== 响应式 ===== */
@media (max-width: 640px) {
    .cyber-header { padding: 12px 14px 10px; }
    .cyber-body { padding: 14px 12px 40px; }
    .cyber-card-title { font-size: 14px; }
    .cyber-card-summary { font-size: 12px; }
    .cyber-logo-text { font-size: 14px; }
    .cyber-ov-item { font-size: 12.5px; }
    .cyber-card-summary-wrap { flex-direction: column; align-items: flex-start; gap: 6px; }
    .cyber-card-link { align-self: flex-end; }
}
</style>
"""


# ========== JS 语言切换（MyMemory API） ==========

LANG_TOGGLE_JS = """
<script>
let currentLang = 'zh';

async function toggleLang() {
    const btn = document.getElementById('langToggleBtn');
    currentLang = currentLang === 'zh' ? 'en' : 'zh';
    btn.textContent = currentLang === 'en' ? '🌐 中文' : '🌐 English';
    btn.classList.toggle('active');

    // 翻译所有标记了 data-original 的元素
    const els = document.querySelectorAll('[data-original]');
    for (const el of els) {
        await translateTextEl(el);
    }
}

async function translateTextEl(el) {
    const original = el.dataset.original;
    if (!original || !original.trim()) return;

    const origHasChinese = /[\\u4e00-\\u9fff]/.test(original);

    // 切回原文语言 → 直接恢复原文，不调 API
    if (currentLang === 'zh' && origHasChinese) {
        el.textContent = original;
        return;
    }
    if (currentLang === 'en' && !origHasChinese) {
        el.textContent = original;
        return;
    }

    // 查缓存
    if (el.dataset.cache) {
        try {
            const cache = JSON.parse(el.dataset.cache);
            if (cache[currentLang]) {
                el.textContent = cache[currentLang];
                return;
            }
        } catch(e) {}
    }

    // 不需要翻译的情况
    if (currentLang === 'zh' && !origHasChinese) { /* 英文→中文翻译 */ }
    else if (currentLang === 'en' && origHasChinese) { /* 中文→英文翻译 */ }
    else return;

    const sourceLang = currentLang === 'zh' ? 'en' : 'zh-CN';
    const targetLang = currentLang === 'zh' ? 'zh-CN' : 'en';

    try {
        const url = 'https://api.mymemory.translated.net/get?q=' +
            encodeURIComponent(original.substring(0, 500)) +
            '&langpair=' + sourceLang + '|' + targetLang;
        const resp = await fetch(url);
        const data = await resp.json();
        const translated = data.responseData.translatedText;

        const cache = JSON.parse(el.dataset.cache || '{}');
        cache[currentLang] = translated;
        el.dataset.cache = JSON.stringify(cache);

        el.textContent = translated;
    } catch(e) {
        console.warn('翻译失败:', e);
    }
}
</script>
"""


def build_cyber_html(article: dict, date_str: str, mode_label: str) -> str:
    """构建科幻风 HTML 文章页面"""
    sections_html = []

    # 概览
    if article["overview"]:
        ov_items = "".join(
            f'<div class="cyber-ov-item" data-role="translatable" data-original="{html_escape(item)}">{item}</div>'
            for item in article["overview"]
        )
        sections_html.append(f"""
        <div class="cyber-overview">
            <div class="cyber-overview-title">◈ 今日看点</div>
            <div class="cyber-overview-grid">{ov_items}</div>
        </div>
        """)

    # 各分类
    for sec in article["sections"]:
        cat = sec["category"]
        is_video_cat = "视频" in cat

        items_html = ""
        for item in sec["items"]:
            title_html = html_escape(item["title"])
            summary_html = html_escape(item["summary"]) if item["summary"] else ""
            source_html = html_escape(item["source"]) if item["source"] else ""
            link = html_escape(item["link"]) if item["link"] else ""

            # 判断标题是否含英文较多
            en_chars = len(re.findall(r'[a-zA-Z]', title_html))
            cn_chars = len(re.findall(r'[一-鿿]', title_html))
            is_en_title = en_chars > cn_chars and cn_chars < 5

            title_extra = ' class="en-text"' if is_en_title else ""

            link_html = f'<a class="cyber-card-link" href="{link}" target="_blank">⟶ 阅读原文</a>' if link else ""

            video_cls = " video" if (item["is_video"] or is_video_cat) else ""

            # 有摘要：原文链接放在摘要右下角
            if summary_html:
                items_html += f"""
            <div class="cyber-card{video_cls}" data-role="translatable">
                <div class="cyber-card-title"{title_extra} data-original="{title_html}">{title_html}</div>
                <div class="cyber-card-summary-wrap">
                    <div class="cyber-card-summary" data-original="{summary_html}">{summary_html}</div>
                    {link_html}
                </div>
                {f'<span class="cyber-card-source">{source_html}</span>' if source_html else ''}
            </div>"""
            else:
                # 无摘要：原文链接放到标题下方
                items_html += f"""
            <div class="cyber-card{video_cls}" data-role="translatable">
                <div class="cyber-card-title"{title_extra} data-original="{title_html}">{title_html}</div>
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    {f'<span class="cyber-card-source">{source_html}</span>' if source_html else '<span></span>'}
                    {link_html}
                </div>
            </div>"""

        cat_clean = re.sub(r'^[^\w一-鿿]*', '', cat)
        sections_html.append(f"""
        <div class="cyber-cat-title">⦿ {cat_clean}</div>
        {items_html}
        """)

    mode_emoji = {"ai": "🤖", "tech": "💻", "all": "📡"}
    short_mode = mode_label.replace("日报", "").strip()

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>AI 日报 · {date_str}</title>
{THEME_CSS}
</head>
<body class="cyber-wrap">
    <div class="cyber-header">
        <div class="cyber-header-inner">
            <div class="cyber-logo">
                <div class="cyber-logo-icon">AI</div>
                <div>
                    <span class="cyber-logo-text">AI 日报</span>
                    <span class="cyber-logo-sub">· 终端</span>
                </div>
            </div>
            <div class="cyber-header-right">
                <span class="cyber-mode-badge">{mode_emoji.get(mode_label[:2], '📡')} {short_mode}</span>
                <button class="cyber-lang-btn" id="langToggleBtn" onclick="toggleLang()">🌐 切换英文</button>
            </div>
        </div>
    </div>
    <div class="cyber-body">
        <div class="cyber-datebar">
            <span class="dot"></span>
            <span>LIVE</span> · {date_str} · {sum(len(sec["items"]) for sec in article["sections"])} 条精选
        </div>
        {''.join(sections_html)}
        <div class="cyber-footer">◈ 由 AI 自动整理 · 每日更新 ◈</div>
    </div>
    {LANG_TOGGLE_JS}
</body>
</html>"""


def html_escape(text: str) -> str:
    """HTML 转义"""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))


# ========== 侧边栏 ==========

st.sidebar.markdown(
    """<div style="text-align:center;margin-bottom:20px;padding:12px 0;">
        <div style="width:40px;height:40px;margin:0 auto 8px;
            background:linear-gradient(135deg,#58a6ff,#3fb950);border-radius:10px;
            display:flex;align-items:center;justify-content:center;
            font-size:20px;font-weight:800;color:#0d1117;">AI</div>
        <p style="font-size:14px;font-weight:700;color:#e0e4f0;margin:0;">AI 日报</p>
        <p style="font-size:11px;color:#8b949e;margin:2px 0 0;">管理终端</p>
    </div>""",
    unsafe_allow_html=True,
)

page = st.sidebar.radio(
    "导航",
    ["◈ 今日日报", "📚 历史记录", "⚡ 生成日报"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    f"<p style='font-size:10px;color:#30363d;text-align:center;'>"
    f"v1.0 · {datetime.now().strftime('%Y-%m-%d')}</p>",
    unsafe_allow_html=True,
)


# ========== 页面：今日日报 ==========

if page == "◈ 今日日报":
    files = list_daily_files()
    if not files:
        st.info("还没有生成过日报，去左侧「⚡ 生成日报」生成一份吧！")
        st.stop()

    latest = files[0]

    # 模式选择器（切换不同模式）
    date_files = [f for f in files if f["date"] == latest["date"]]
    mode_options = {f["mode"]: f for f in date_files}
    if not mode_options:
        mode_options = {latest["mode"]: latest}

    mode_label_map = {"ai": "🤖 AI 垂直", "tech": "💻 科技综合", "all": "📡 全频道"}

    if len(mode_options) > 1:
        cols = st.columns([1, 3])
        with cols[0]:
            selected_mode = st.selectbox(
                "切换模式",
                options=list(mode_options.keys()),
                format_func=lambda m: mode_label_map.get(m, m),
                label_visibility="collapsed",
            )
            display_file = mode_options[selected_mode]
        with cols[1]:
            pass
    else:
        display_file = latest
        selected_mode = latest["mode"]

    try:
        with open(display_file["md_path"], "r", encoding="utf-8") as f:
            md_content = f.read()
    except Exception as e:
        st.error(f"读取失败：{e}")
        st.stop()

    article = parse_md_article(md_content)
    total_items = sum(len(s["items"]) for s in article["sections"])

    # 渲染为科幻风 HTML
    mode_short = mode_label_map.get(display_file["mode"], display_file["mode"])
    cyber_html = build_cyber_html(article, display_file["date"], mode_short)

    # 用 component 展示（全屏高度）
    st.components.v1.html(cyber_html, height=900, scrolling=True)

    # 底部操作栏
    col1, col2, col3, col4 = st.columns([1, 1, 1, 4])
    with col1:
        if display_file["html_path"] and os.path.exists(display_file["html_path"]):
            with open(display_file["html_path"], "r", encoding="utf-8") as f:
                st.download_button("📥 HTML", f.read(),
                                   file_name=os.path.basename(display_file["html_path"]),
                                   mime="text/html")
    with col2:
        st.download_button("📥 MD", md_content,
                           file_name=os.path.basename(display_file["md_path"]),
                           mime="text/markdown")
    with col3:
        st.button("🔄 刷新", on_click=lambda: None)


# ========== 页面：历史记录 ==========

elif page == "📚 历史记录":
    st.markdown("""<h2 style="color:#e0e4f0;font-size:20px;font-weight:700;">📚 历史日报</h2>""",
                unsafe_allow_html=True)

    files = list_daily_files()
    if not files:
        st.info("还没有生成过日报。")
        st.stop()

    by_date: dict[str, list] = {}
    for f in files:
        by_date.setdefault(f["date"], []).append(f)

    mode_label_map = {"ai": "🤖 AI 垂直", "tech": "💻 科技综合", "all": "📡 全频道"}

    for date_str, entries in sorted(by_date.items(), reverse=True):
        header = f"""<div style="display:flex;align-items:center;gap:8px;margin:16px 0 8px;">
            <span style="color:#58a6ff;font-weight:600;font-size:14px;">📅 {date_str}</span>
            <span style="color:#484f58;font-size:12px;">{len(entries)} 条</span>
        </div>"""
        st.markdown(header, unsafe_allow_html=True)

        for entry in entries:
            label = mode_label_map.get(entry["mode"], entry["mode"])
            size_kb = entry["size"] / 1024

            cols = st.columns([2, 1, 1, 1, 1])
            with cols[0]:
                st.markdown(f'<span style="font-size:13px;color:#c9d1d9;">{label}</span>',
                            unsafe_allow_html=True)
            with cols[1]:
                st.markdown(f'<span style="font-size:12px;color:#484f58;">{size_kb:.1f} KB</span>',
                            unsafe_allow_html=True)
            with cols[2]:
                try:
                    with open(entry["md_path"], "r", encoding="utf-8") as f:
                        md_content = f.read()
                    st.download_button("📥 MD", md_content,
                                       file_name=os.path.basename(entry["md_path"]),
                                       mime="text/markdown",
                                       key=f"md_{date_str}_{entry['mode']}")
                except Exception:
                    pass
            with cols[3]:
                if entry["html_path"] and os.path.exists(entry["html_path"]):
                    try:
                        with open(entry["html_path"], "r", encoding="utf-8") as f:
                            st.download_button("📥 HTML", f.read(),
                                               file_name=os.path.basename(entry["html_path"]),
                                               mime="text/html",
                                               key=f"html_{date_str}_{entry['mode']}")
                    except Exception:
                        pass
            with cols[4]:
                # 查看按钮：跳转到今日日报（用 session state）
                if st.button("👁 查看", key=f"view_{date_str}_{entry['mode']}"):
                    st.session_state["view_file"] = entry
                    st.rerun()

    # 处理查看按钮
    if "view_file" in st.session_state:
        vf = st.session_state["view_file"]
        try:
            with open(vf["md_path"], "r", encoding="utf-8") as f:
                md_content = f.read()
            article = parse_md_article(md_content)
            mode_short = mode_label_map.get(vf["mode"], vf["mode"])
            cyber_html = build_cyber_html(article, vf["date"], mode_short)
            st.markdown("---")
            st.markdown(f"""<h3 style="color:#58a6ff;font-size:16px;">📖 {vf['date']} {mode_short}</h3>""",
                        unsafe_allow_html=True)
            st.components.v1.html(cyber_html, height=800, scrolling=True)
        except Exception as e:
            st.error(f"加载失败：{e}")


# ========== 页面：生成日报 ==========

elif page == "⚡ 生成日报":
    st.markdown("""<h2 style="color:#e0e4f0;font-size:20px;font-weight:700;">⚡ 生成日报</h2>""",
                unsafe_allow_html=True)

    st.markdown("""<p style="color:#8b949e;font-size:13px;margin-bottom:20px;">
    选择模式，点击生成。RSS 抓取 + AI 生成约需 <strong>30–60 秒</strong>。</p>""",
                unsafe_allow_html=True)

    mode_map = {
        "ai": ("🤖 AI 垂直日报", "仅 AI 相关源，内容精炼"),
        "tech": ("💻 科技综合日报", "综合科技资讯"),
        "all": ("📡 全频道日报", "AI + 科技合并，内容最丰富"),
    }

    with st.form("generate_form"):
        cols = st.columns(3)
        with cols[0]:
            mode_ai = st.checkbox("🤖 AI 垂直", value=True, help=mode_map["ai"][1])
        with cols[1]:
            mode_tech = st.checkbox("💻 科技综合", value=False, help=mode_map["tech"][1])
        with cols[2]:
            mode_all = st.checkbox("📡 全频道", value=False, help=mode_map["all"][1])

        modes_to_run = []
        if mode_ai: modes_to_run.append("ai")
        if mode_tech: modes_to_run.append("tech")
        if mode_all: modes_to_run.append("all")
        if not modes_to_run:
            modes_to_run = ["ai"]

        st.caption(f"将生成 {len(modes_to_run)} 个模式：{', '.join(modes_to_run)}")

        submitted = st.form_submit_button("⚡ 开始生成", type="primary", use_container_width=True)

    if submitted:
        for mode in modes_to_run:
            with st.status(f"⏳ 生成 {mode_map[mode][0]}...", expanded=True) as status:
                try:
                    cmd = [sys.executable, str(BASE_DIR / "main.py"), mode]
                    result = subprocess.run(
                        cmd, capture_output=True, text=True,
                        timeout=120, cwd=str(BASE_DIR),
                    )
                    if result.stdout:
                        st.code(result.stdout[-400:], language="text")
                    if result.returncode == 0:
                        status.update(label=f"✅ {mode_map[mode][0]} 成功", state="complete")
                    else:
                        status.update(label=f"❌ {mode_map[mode][0]} 失败", state="error")
                except subprocess.TimeoutExpired:
                    st.error("超时")
                except Exception as e:
                    st.error(f"异常：{e}")

        st.success("✅ 全部完成！去「◈ 今日日报」查看。")
        st.balloons()
