"""调用 AI API 生成公众号文章 + 内嵌阅读 HTML 页面"""

import os
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from config import ANTHROPIC_API_KEY, DEEPSEEK_API_KEY, DEEPSEEK_API_URL
from imager import batch_get_images

# Jinja2 模板环境（相对于项目根目录）
_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
_jinja_env = Environment(loader=FileSystemLoader(_TEMPLATES_DIR))


SYSTEM_PROMPT = """你是一位资深 AI 科技媒体编辑，负责将每日 AI 动态整理成公众号文章。

写作风格要求：
- 标题要有吸引力，不要标题党
- 开头用 1-2 句话概括今天最值得关注的事
- 每条动态用简练的语言概括核心信息，加上你的简短点评
- 语言自然、有观点，不要像机器翻译
- 适合公众号阅读，段落不要太长

输出格式要求：
- 用 Markdown 格式
- 标题用 # ，分类用 ## ，每条动态用 ### 或加粗标题
- 每条动态必须包含以下字段（每行一个，冒号后跟内容）：
  **标题：** 中文标题
  **标题（英文）：** English Title
  **摘要：** 中文摘要，1-2句话概括核心信息
  **摘要（英文）：** English summary, 1-2 sentences, professional tone
  **来源：** 来源名
  **链接：** URL
- 英文标题和摘要需要自然流畅，不是逐字翻译，而是面向英文读者的重新表述
- 不要输出 ```markdown 代码块标记

在输出所有条目之后，新增一个 ## 🔍 趋势洞察 板块，要求：
- 从今天的新闻中发现至少 2 条新闻之间的关联性
- 指出这反映了什么行业趋势
- 给出一个有观点的判断或预测，必须具体，不要泛泛而谈
- 控制在 150-200 字以内
禁止使用以下表达：'值得关注'、'前景广阔'、'未来可期'、'值得期待'、'让我们拭目以待'
必须给出具体证据支撑观点，否则宁可不说

同时输出英文版趋势洞察，格式为：
### 趋势洞察（英文）
English version of the trend analysis, same insights, natural English prose.

在文章最开头（标题之后、正文之前），用以下格式输出今日重点：
### 今日重点
一句话中文概括今天最值得关注的事（不超过30字）
### 今日重点（英文）
English one-liner, same spirit, under 20 words"""


def _parse_bilingual_fields(article_text: str, groups: dict):
    """从 AI 生成的文章中提取英文标题/摘要，注入到 groups 中的每个 item"""
    import re
    all_items = [it for items in groups.values() for it in items]
    idx = 0
    lines = article_text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # 匹配 "### 标题：XXX" 或 "**标题：** XXX"
        m = re.search(r"(?:###\s*)?[*]*标题[：:][*]*\s*(.+)", line)
        if m and "英文" not in line:
            title_en = ""
            summary_en = ""
            j = i + 1
            while j < len(lines) and j < i + 10:
                l2 = lines[j].strip()
                m2 = re.search(r"[*]*标题（英文）[：:][*]*\s*(.+)", l2)
                if m2:
                    title_en = m2.group(1).strip()
                m3 = re.search(r"[*]*摘要（英文）[：:][*]*\s*(.+)", l2)
                if m3:
                    summary_en = m3.group(1).strip()
                if re.match(r"(?:###\s*)?[*]*标题[：:]", l2) and "英文" not in l2 and j > i + 1:
                    break
                if l2.startswith("## "):
                    break
                j += 1
            if idx < len(all_items):
                all_items[idx]["title_en"] = title_en
                all_items[idx]["summary_en"] = summary_en
                idx += 1
        i += 1
    for it in all_items:
        it.setdefault("title_en", "")
        it.setdefault("summary_en", "")


def _extract_highlight(article_text: str) -> tuple[str, str]:
    """从 AI 文章中提取今日重点（中英文），返回 (highlight_zh, highlight_en)"""
    import re
    if not article_text:
        return "", ""
    lines = article_text.split("\n")
    highlight_zh = ""
    highlight_en = ""
    for i, line in enumerate(lines):
        stripped = line.strip()
        # 中文今日重点：匹配 "### 今日重点：xxx" 或 "### 今日重点" + 下一行
        if re.match(r"(?:###\s*)?[*]*今日重点", stripped) and "英文" not in stripped:
            # 提取同行内容（去掉标题标记和冒号）
            content = re.sub(r"^(?:###\s*)?[*]*今日重点[：:]?\s*", "", stripped).strip()
            if content:
                highlight_zh = content
            elif i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].strip().startswith("#"):
                highlight_zh = lines[i + 1].strip()
        # 英文今日重点
        if re.match(r"(?:###\s*)?[*]*今日重点（英文）", stripped):
            content = re.sub(r"^(?:###\s*)?[*]*今日重点（英文）[：:]?\s*", "", stripped).strip()
            if content:
                highlight_en = content
            elif i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].strip().startswith("#"):
                highlight_en = lines[i + 1].strip()
    return highlight_zh, highlight_en


def _calc_read_stats(article_text: str) -> tuple[int, int]:
    """计算文章字数和预计阅读时间（分钟），返回 (word_count, read_minutes)"""
    import re
    if not article_text:
        return 0, 0
    # 去掉 markdown 标记和链接
    clean = re.sub(r'[#*`\[\]()<>|_~\-]', '', article_text)
    clean = re.sub(r'https?://\S+', '', clean)
    # 中文字符数
    cn_chars = len(re.findall(r'[一-鿿]', clean))
    # 英文单词数
    en_words = len(re.findall(r'[a-zA-Z]+', clean))
    # 总字数：中文字符 + 英文单词
    word_count = cn_chars + en_words
    # 平均阅读速度：中文 400字/分钟，英文 200词/分钟
    read_minutes = max(1, round(word_count / 400)) if cn_chars > en_words else max(1, round(word_count / 200))
    return word_count, read_minutes


def _generate_comparison(groups: dict, mode: str = "ai") -> str:
    """生成和昨天的对比摘要"""
    from database import get_yesterday_articles
    yesterday = get_yesterday_articles(mode)
    if yesterday["count"] == 0:
        return ""
    today_count = sum(len(v) for v in groups.values())
    diff = today_count - yesterday["count"]
    # 分类对比
    today_cats = {cat: len(items) for cat, items in groups.items()}
    yest_cats = yesterday["categories"]
    new_cats = [c for c in today_cats if c not in yest_cats]
    gone_cats = [c for c in yest_cats if c not in today_cats]
    parts = []
    if diff > 0:
        parts.append(f"今日 {today_count} 条，比昨日多 {diff} 条")
    elif diff < 0:
        parts.append(f"今日 {today_count} 条，比昨日少 {abs(diff)} 条")
    else:
        parts.append(f"今日 {today_count} 条，与昨日持平")
    if new_cats:
        parts.append(f"新增板块：{'、'.join(new_cats)}")
    if gone_cats:
        parts.append(f"昨日有但今日无：{'、'.join(gone_cats)}")
    return "；".join(parts)


def generate_overview(groups: dict) -> str:
    """生成今日内容概览"""
    lines = ["**📋 今日看点**\n"]
    for cat, items in groups.items():
        emoji_map = {"行业": "🏭", "产品": "🛠️", "论文": "📄", "模型": "🧠", "视频": "🎬", "产业": "🏭"}
        emoji = emoji_map.get(cat, "•")
        titles = "、".join(item["title"] for item in items[:2])
        more = f" 等{len(items)}条" if len(items) > 2 else ""
        lines.append(f"- {emoji} **{cat}**：{titles}{more}")
    return "\n".join(lines)


def generate_article(groups: dict) -> tuple[str, str]:
    """用 AI API（DeepSeek/Claude）生成公众号文章，返回 (文章内容, 使用的模型)"""
    if not DEEPSEEK_API_KEY and not ANTHROPIC_API_KEY:
        print("  [writer] 未配置 API Key（DeepSeek 或 Claude），使用模板生成")
        return generate_from_template(groups)

    today = datetime.now().strftime("%Y-%m-%d")
    overview = generate_overview(groups)
    content_lines = [f"今天是 {today}，以下是今日 AI 领域动态：\n"]

    for cat, items in groups.items():
        content_lines.append(f"\n## {cat}\n")
        for i, item in enumerate(items, 1):
            content_lines.append(f"{i}. **{item['title']}**")
            if item["summary"]:
                content_lines.append(f"   摘要：{item['summary']}")
            content_lines.append(f"   来源：{item['author']}")
            content_lines.append(f"   链接：{item['link']}")
            content_lines.append("")

    content_lines.append("\n请根据以上内容，在文章末尾输出一个'趋势洞察'板块，分析今日多条动态之间的关联和趋势。\n")
    user_prompt = "\n".join(content_lines)

    # 优先使用 DeepSeek（OpenAI 兼容格式）
    if DEEPSEEK_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_API_URL,
            )
            message = client.chat.completions.create(
                model="deepseek-chat",
                max_tokens=4096,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            article = message.choices[0].message.content
            article = article.split("\n", 1)
            if len(article) > 1:
                article = article[0] + "\n\n" + overview + "\n\n" + article[1]
            else:
                article = article[0] + "\n\n" + overview
            _parse_bilingual_fields(article, groups)
            print(f"  [writer] DeepSeek API 生成完成，{len(article)} 字符")
            return article, "deepseek"
        except Exception as e:
            print(f"  [writer] DeepSeek API 调用失败：{e}")
            if not ANTHROPIC_API_KEY:
                print("  [writer] 无备用 API Key，回退到模板生成")
                return generate_from_template(groups)
            print("  [writer] 尝试备用 Claude API...")

    # 备用：Claude API
    if ANTHROPIC_API_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            article = message.content[0].text
            article = article.split("\n", 1)
            if len(article) > 1:
                article = article[0] + "\n\n" + overview + "\n\n" + article[1]
            else:
                article = article[0] + "\n\n" + overview
            _parse_bilingual_fields(article, groups)
            print(f"  [writer] Claude API 生成完成，{len(article)} 字符")
            return article, "claude"
        except Exception as e:
            print(f"  [writer] Claude API 调用失败：{e}")
            print("  [writer] 回退到模板生成")
            return generate_from_template(groups)

    return generate_from_template(groups)


def generate_from_template(groups: dict) -> tuple[str, str]:
    """不用 API，直接用模板拼接文章（精排版），返回 (文章内容, "template")"""
    # 模板模式不调 API，双语字段设为空
    for items in groups.values():
        for item in items:
            item.setdefault("title_en", "")
            item.setdefault("summary_en", "")
    today = datetime.now().strftime("%Y-%m-%d")
    total = sum(len(v) for v in groups.values())
    lines = [f"# AI 日报 · {today}\n"]

    # 开场
    lines.append(f"> 每日 8:00 精选 {total} 条 AI 领域动态，快速了解行业脉搏\n")

    lines.append(generate_overview(groups))
    lines.append("\n---\n")

    cat_index = 0
    link_index = 0
    all_links = []

    for cat, items in groups.items():
        emoji_map = {"行业": "🏭", "产品": "🛠️", "论文": "📄", "模型": "🧠", "视频": "🎬", "产业": "🏭"}
        emoji = emoji_map.get(cat, "📌")
        lines.append(f"## {emoji} {cat}\n")

        for item in items:
            link_index += 1
            title = item["title"]
            summary = item.get("summary", "")

            if item.get("type") == "video":
                play = item.get("play", 0)
                dur = item.get("duration", "")
                play_str = f"{play // 10000}万" if play >= 10000 else str(play)
                author = item.get("author", "")
                lines.append(f"### 🎬 {title}\n")
                if summary:
                    # 摘要精简到 80 字以内
                    short_summary = summary[:80] + "..." if len(summary) > 80 else summary
                    lines.append(f"{short_summary}\n")
                lines.append(f"> UP主：{author}　播放：{play_str}　时长：{dur}")
                lines.append(f"> [🔗 观看视频]({item['link']})\n")
                all_links.append((f"🎬 {title}", item['link']))
            else:
                lines.append(f"### {title}\n")
                if summary:
                    # 摘要精简到 100 字以内
                    short_summary = summary[:100] + "..." if len(summary) > 100 else summary
                    lines.append(f"{short_summary}\n")
                source = item.get("author", "")
                if source:
                    lines.append(f"> 来源：{source}")
                lines.append(f"> [🔗 阅读原文]({item['link']})\n")
                all_links.append((title, item['link']))

    # 趋势洞察占位
    lines.append("---\n")
    lines.append("## 🔍 趋势洞察\n")
    lines.append("> 💡 需配置 DeepSeek API Key 后自动生成趋势分析\n")

    # 原文链接汇总
    lines.append("---\n")
    lines.append("### 📎 原文链接\n")
    for i, (t, url) in enumerate(all_links, 1):
        lines.append(f"{i}. [{t}]({url})")
    lines.append("")

    lines.append("---\n")
    lines.append("*本文由 AI 自动整理 · 每日 8:00 更新*")

    article = "\n".join(lines)
    print(f"  [writer] 模板生成完成，{len(article)} 字符")
    return article, "template"


def _extract_trend_html(article_text: str) -> tuple[str, str]:
    """从 Markdown 文章中提取趋势洞察板块（中文和英文），转为 HTML。
    返回 (trend_zh_html, trend_en_html)"""
    import re
    if not article_text or "趋势洞察" not in article_text:
        return "", ""
    lines = article_text.split("\n")
    in_trend = False
    in_en = False
    trend_zh_lines = []
    trend_en_lines = []

    for line in lines:
        # 英文趋势洞察子标题
        if "趋势洞察（英文）" in line or "Trend Insight" in line:
            if line.startswith("###") or line.startswith("##"):
                in_en = True
                in_trend = False
                continue
        # 中文趋势洞察标题
        if "趋势洞察" in line and ("##" in line or "###" in line) and "英文" not in line:
            in_trend = True
            in_en = False
            continue
        if in_trend or in_en:
            if line.startswith("## ") or (line.startswith("# ") and not line.startswith("###")):
                in_trend = False
                in_en = False
                continue
            if line.strip():
                if in_en:
                    trend_en_lines.append(line.strip())
                else:
                    trend_zh_lines.append(line.strip())

    def _to_html(trend_lines):
        if not trend_lines:
            return ""
        body = "<br>".join(trend_lines)
        body = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", body)
        return body

    zh_body = _to_html(trend_zh_lines)
    en_body = _to_html(trend_en_lines)
    return zh_body, en_body


def generate_redirect_html(groups: dict, date_str: str, label: str = "AI 日报",
                           article_text: str = "") -> str:
    """用 Jinja2 模板生成杂志风格 HTML 页面"""
    # 提取今日重点
    highlight_zh, highlight_en = _extract_highlight(article_text)
    # 计算字数和阅读时间
    word_count, read_minutes = _calc_read_stats(article_text)
    # 分类渐变色
    gradients = {
        "模型": "linear-gradient(135deg, #0d9488 0%, #0f766e 100%)",
        "产品": "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)",
        "行业": "linear-gradient(135deg, #ea580c 0%, #c2410c 100%)",
        "论文": "linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%)",
        "技巧": "linear-gradient(135deg, #e11d48 0%, #be123c 100%)",
        "视频": "linear-gradient(135deg, #9333ea 0%, #6b21a8 100%)",
    }
    colors = {
        "模型": "0d9488", "产品": "2563eb", "行业": "ea580c",
        "论文": "7c3aed", "技巧": "e11d48", "视频": "9333ea",
    }

    # 概览数据：{分类: [标题1, 标题2, ...]}
    overview_items = {cat: [it["title"] for it in items[:3]] for cat, items in groups.items()}

    # 展开条目并附加分类、颜色、域名
    items_flat = []
    for cat, items in groups.items():
        for item in items:
            item["category"] = cat
            items_flat.append(item)

    # 按类型分组：文章在前，视频在后
    article_flat = [it for it in items_flat if it.get("type") != "video"]
    video_flat = [it for it in items_flat if it.get("type") == "video"]

    # 给文章注入 color 和 domain，避免模板里做字符串处理
    for item in article_flat:
        cat = item["category"]
        item["color"] = colors.get(cat, "374151")
        item["gradient"] = gradients.get(cat, "linear-gradient(135deg, #374151 0%, #1f2937 100%)")
        domain = item["link"].split("/")[2] if len(item["link"].split("/")) > 2 else ""
        item["domain"] = domain.replace("www.", "")

    # 批量并行获取配图
    card_images = {}
    img_results = batch_get_images(article_flat)
    article_images = []
    for item in article_flat:
        item_key = str(id(item))
        img_url, attr = img_results.get(item_key, (None, None))
        article_images.append(img_url)
        if attr and img_url:
            card_images[img_url] = attr

    # 图片署名
    creds = ""
    if card_images:
        names = []
        for url, attr in card_images.items():
            name = attr.get("name", "")
            link = attr.get("link", "")
            if name and link:
                names.append(f'<a href="{link}" target="_blank" style="color:#aeaeb2;text-decoration:underline;">{name}</a>')
        if names:
            creds = " · 配图：" + "、".join(names) + "（Unsplash）"

    # 提取趋势洞察（中文和英文）
    trend_zh, trend_en = _extract_trend_html(article_text)

    # 生成和昨天的对比
    comparison = _generate_comparison(groups)

    # 线上页面地址（分享按钮和 RSS 用）
    page_url = f"https://vv0rfr.github.io/ai-daily/{date_str}-ai.html"

    # 渲染模板
    template = _jinja_env.get_template("daily.html")
    return template.render(
        groups=groups,
        date_str=date_str,
        label=label,
        items_flat=items_flat,
        article_flat=article_flat,
        video_flat=video_flat,
        article_images=article_images,
        overview_items=overview_items,
        gradients=gradients,
        colors=colors,
        creds=creds,
        trend_zh=trend_zh,
        trend_en=trend_en,
        highlight_zh=highlight_zh,
        highlight_en=highlight_en,
        word_count=word_count,
        read_minutes=read_minutes,
        comparison=comparison,
        page_url=page_url,
    )


def generate_feed(groups: dict, date_str: str, label: str = "AI 日报",
                  base_url: str = "https://vv0rfr.github.io/ai-daily") -> str:
    """生成 Atom 格式的 feed.xml"""
    from xml.etree.ElementTree import Element, SubElement, tostring
    from xml.dom.minidom import parseString

    NS = "http://www.w3.org/2005/Atom"
    root = Element("feed", xmlns=NS)
    SubElement(root, "title").text = label
    SubElement(root, "subtitle").text = "AI-Powered Daily Digest"
    SubElement(root, "id").text = f"{base_url}/"
    SubElement(root, "updated").text = f"{date_str}T08:00:00+08:00"
    link_self = SubElement(root, "link", rel="self", type="application/atom+xml",
                           href=f"{base_url}/feed.xml")
    link_alt = SubElement(root, "link", rel="alternate", type="text/html",
                           href=f"{base_url}/{date_str}-ai.html")

    author = SubElement(root, "author")
    SubElement(author, "name").text = "AI Daily Bot"

    for cat, items in groups.items():
        for item in items:
            entry = SubElement(root, "entry")
            SubElement(entry, "title").text = item["title"]
            SubElement(entry, "id").text = item["link"]
            SubElement(entry, "link", href=item["link"])
            SubElement(entry, "updated").text = f"{date_str}T08:00:00+08:00"
            summary = item.get("summary", "")
            if summary:
                SubElement(entry, "summary", type="html").text = summary
            cat_el = SubElement(entry, "category", term=cat)

    raw_xml = tostring(root, encoding="unicode", xml_declaration=False)
    xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + raw_xml
    # 格式化
    try:
        dom = parseString(xml_str)
        return dom.toprettyxml(indent="  ", encoding=None).replace(
            '<?xml version="1.0" ?>\n', '<?xml version="1.0" encoding="UTF-8"?>\n'
        )
    except Exception:
        return xml_str


def generate_index(output_dir: str = None):
    """扫描 output/ 下的 *-ai.html，生成历史日报列表页 index.html"""
    import glob as _glob
    import re
    from database import _get_conn

    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

    pattern = os.path.join(output_dir, "*-ai.html")
    files = _glob.glob(pattern)

    entries = []
    for f in files:
        basename = os.path.basename(f)
        m = re.match(r"(\d{4}-\d{2}-\d{2})-ai\.html", basename)
        if not m:
            continue
        date_str = m.group(1)
        # 从数据库查该日期的文章数
        count = 0
        try:
            conn = _get_conn()
            row = conn.execute(
                "SELECT total_items FROM runs WHERE run_date=? AND mode='ai' ORDER BY id DESC LIMIT 1",
                (date_str,),
            ).fetchone()
            if row:
                count = row["total_items"] or 0
            conn.close()
        except Exception:
            pass
        entries.append({"date": date_str, "filename": basename, "count": count})

    entries.sort(key=lambda e: e["date"], reverse=True)

    # 日期范围
    date_range = ""
    if len(entries) >= 2:
        date_range = f"{entries[-1]['date']} ~ {entries[0]['date']}"

    total = len(entries)
    template = _jinja_env.get_template("index.html")
    html = template.render(entries=entries, total=total, date_range=date_range)

    index_path = os.path.join(output_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  [writer] 历史列表页：{index_path}（{total} 期）")
    return index_path
