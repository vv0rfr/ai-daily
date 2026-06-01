"""调用 Claude API 生成公众号文章 + 内嵌阅读 HTML 页面"""

import os
import html
import urllib.parse
from datetime import datetime
from config import ANTHROPIC_API_KEY, OUTPUT_DIR


SYSTEM_PROMPT = """你是一位资深 AI 科技媒体编辑，负责将每日 AI 动态整理成公众号文章。

写作风格要求：
- 标题要有吸引力，不要标题党
- 开头用 1-2 句话概括今天最值得关注的事
- 每条动态用简练的语言概括核心信息，加上你的简短点评
- 语言自然、有观点，不要像机器翻译
- 结尾可以加一段总结或展望
- 适合公众号阅读，段落不要太长

输出格式要求：
- 用 Markdown 格式
- 标题用 # ，分类用 ## ，每条动态用 ### 或加粗标题
- 每条动态附上原文链接
- 不要输出 ```markdown 代码块标记"""


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


def generate_article(groups: dict) -> str:
    """用 Claude API 生成公众号文章"""
    if not ANTHROPIC_API_KEY:
        print("  [writer] 未配置 ANTHROPIC_API_KEY，使用模板生成")
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

    user_prompt = "\n".join(content_lines)

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
        print(f"  [writer] Claude API 生成完成，{len(article)} 字符")
        return article
    except Exception as e:
        print(f"  [writer] Claude API 调用失败：{e}")
        print("  [writer] 回退到模板生成")
        return generate_from_template(groups)


def generate_from_template(groups: dict) -> str:
    """不用 API，直接用模板拼接文章（精排版）"""
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
    return article


def generate_redirect_html(groups: dict, date_str: str, label: str = "AI 日报") -> str:
    """生成杂志风格 HTML 页面"""
    items_flat = []
    for cat, items in groups.items():
        for item in items:
            items_flat.append({**item, "category": cat})

    # 分类渐变色
    gradients = {
        "模型": "linear-gradient(135deg, #0d9488 0%, #0f766e 100%)",
        "产品": "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)",
        "行业": "linear-gradient(135deg, #ea580c 0%, #c2410c 100%)",
        "论文": "linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%)",
        "技巧": "linear-gradient(135deg, #e11d48 0%, #be123c 100%)",
        "视频": "linear-gradient(135deg, #9333ea 0%, #6b21a8 100%)",
    }

    # 先按类型分组：文章在前，视频在后
    article_flat = [it for it in items_flat if it.get("type") != "video"]
    video_flat = [it for it in items_flat if it.get("type") == "video"]

    def _render_item(item, index, in_video_section=False):
        """渲染单个条目卡片"""
        cat = html.escape(item["category"])
        title = html.escape(item["title"])
        summary = html.escape(item["summary"]) if item["summary"] else ""
        link = html.escape(item["link"])
        lang = item.get("lang", "zh")
        accessible = item.get("accessible", True)
        domain = urllib.parse.urlparse(item["link"]).netloc.replace("www.", "")
        color = gradients.get(cat, "#374151").split("#")[1][:6]

        is_video = item.get("type") == "video"

        if is_video:
            # 视频卡片
            thumb = html.escape(item.get("thumbnail", ""))
            play = item.get("play", 0)
            dur = html.escape(item.get("duration", ""))
            author = html.escape(item.get("author", ""))
            play_str = f"{play // 10000}万" if play >= 10000 else str(play)
            return f"""
    <div class="vcard" data-original-lang="{lang}">
      <a href="{link}" target="_blank" class="vcard-img" style="background-image:url('{thumb}')">
        <span class="vcard-dur">{dur}</span>
      </a>
      <div class="vcard-info">
        <div class="vcard-t">{title}</div>
        <div class="vcard-meta">UP主：{author}　｜　{play_str} 播放</div>
      </div>
    </div>"""
        else:
            # 文章卡片
            lang_label = "EN" if lang == "zh" else "中文"
            lang_btn = f'<button class="btn-s" onclick="toggleLang(this)">{lang_label}</button>'
            read_btn = f'<a href="{link}" class="btn-r" target="_blank">原文</a>' if accessible else ""
            btns = f'<span class="btns">{lang_btn}{read_btn}</span>'

            if index == 1:
                grad = gradients.get(cat, "linear-gradient(135deg, #374151 0%, #1f2937 100%)")
                return f"""
    <div class="hero" data-original-lang="{lang}" style="background:{grad}">
      <div class="hero-mask">
        <div class="hero-t">{title}</div>
        <div class="hero-s">{summary}</div>
        <div class="hero-b">{btns}<span class="src">{domain}</span></div>
      </div>
    </div>"""
            elif index <= 5:
                return f"""
    <div class="tile" data-original-lang="{lang}" style="border-top:3px solid #{color}">
      <div class="tile-t">{title}</div>
      <div class="tile-s">{summary}</div>
      <div class="tile-b">{btns}<span class="src">{domain}</span></div>
    </div>"""
            else:
                return f"""
    <div class="row" data-original-lang="{lang}">
      <span class="dot" style="background:#{color}"></span>
      <span class="row-t">{title}</span>
      <span class="row-s">{summary}</span>
      {btns}
    </div>"""

    # 渲染文章部分
    cards_html = ""
    for i, item in enumerate(article_flat, 1):
        if i == 2:
            cards_html += '\n  <div class="tiles">'
        cards_html += _render_item(item, i)
        if i == 5:
            cards_html += '\n  </div>'
    # 如果文章不足5条但tiles已开启，关闭tiles
    if 1 < len(article_flat) < 5:
        cards_html += '\n  </div>'

    # 渲染视频部分
    if video_flat:
        cards_html += '\n  <div class="vsection">'
        cards_html += '\n    <div class="vsection-title">🎬 视频精选</div>'
        cards_html += '\n    <div class="vgrid">'
        for item in video_flat:
            cards_html += _render_item(item, 0, in_video_section=True)
        cards_html += '\n    </div>'
        cards_html += '\n  </div>'

    page_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{label} · {date_str}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
    background: #f5f5f7; color: #1d1d1f; line-height: 1.5;
    max-width: 740px; margin: 0 auto;
  }}

  /* header */
  .hdr {{
    background: linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);
    color:#fff; padding: 36px 24px 28px; text-align:center;
  }}
  .hdr h1 {{ font-size:1.6em; font-weight:800; letter-spacing:2px; }}
  .hdr .sub {{ font-size:0.85em; color:rgba(255,255,255,0.6); margin-top:6px; }}

  .wrap {{ padding: 16px 14px; }}

  /* 概览 */
  .ov {{
    background:#fff; border-radius:10px; padding:14px 16px; margin-bottom:16px;
    box-shadow:0 1px 3px rgba(0,0,0,0.04);
  }}
  .ov h3 {{ font-size:0.8em; color:#86868b; font-weight:600; margin-bottom:8px; letter-spacing:1px; }}
  .ov li {{ font-size:0.82em; color:#47474a; padding:3px 0; list-style:none; }}
  .ov li strong {{ color:#1d1d1f; }}

  /* hero */
  .hero {{
    border-radius:14px; overflow:hidden; margin-bottom:14px;
    min-height:200px; display:flex; align-items:flex-end; color:#fff;
  }}
  .hero-mask {{
    width:100%; padding:22px 20px;
    background: linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.3) 55%, transparent 100%);
  }}
  .hero-t {{ font-size:1.15em; font-weight:700; margin-bottom:6px; line-height:1.35; }}
  .hero-s {{ font-size:0.82em; color:rgba(255,255,255,0.8); margin-bottom:10px; }}
  .hero-b {{ display:flex; align-items:center; gap:6px; }}

  /* tile grid */
  .tiles {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:14px; }}
  .tile {{
    background:#fff; border-radius:10px; padding:14px;
    box-shadow:0 1px 3px rgba(0,0,0,0.04);
    transition: transform 0.15s, box-shadow 0.15s;
  }}
  .tile:hover {{ transform:translateY(-2px); box-shadow:0 4px 12px rgba(0,0,0,0.08); }}
  .tile-t {{ font-size:0.88em; font-weight:700; color:#1d1d1f; margin-bottom:4px; line-height:1.4; }}
  .tile-s {{ font-size:0.76em; color:#86868b; line-height:1.5; margin-bottom:8px;
    display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }}
  .tile-b {{ display:flex; align-items:center; gap:6px; }}

  /* rows */
  .row {{
    background:#fff; border-radius:8px; padding:10px 14px; margin-bottom:6px;
    display:flex; align-items:center; gap:8px;
    box-shadow:0 1px 2px rgba(0,0,0,0.03);
    transition: background 0.15s;
  }}
  .row:hover {{ background:#f0f0f2; }}
  .dot {{ width:6px; height:6px; border-radius:50%; flex-shrink:0; }}
  .row-t {{ font-size:0.82em; font-weight:600; color:#1d1d1f; flex-shrink:0;
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:55%; }}
  .row-s {{ font-size:0.75em; color:#86868b; flex:1; min-width:0;
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}

  /* buttons */
  .btns {{ display:flex; gap:4px; flex-shrink:0; margin-left:auto; }}
  .btn-s {{
    background:#f5f5f7; color:#1d1d1f; border:none; padding:2px 8px;
    border-radius:4px; font-size:0.68em; cursor:pointer; font-weight:600;
  }}
  .btn-s:hover {{ background:#e8e8ed; }}
  .btn-s.active {{ background:#0071e3; color:#fff; }}
  .btn-r {{
    display:inline-block; padding:2px 8px; border-radius:4px;
    font-size:0.68em; text-decoration:none; background:#0071e3; color:#fff; font-weight:600;
  }}
  .btn-r:hover {{ background:#0077ed; }}
  .src {{ font-size:0.68em; color:#aeaeb2; margin-left:4px; }}
  .hero .btn-s {{ background:rgba(255,255,255,0.15); color:#fff; }}
  .hero .btn-s:hover {{ background:rgba(255,255,255,0.25); }}
  .hero .btn-s.active {{ background:#fff; color:#1d1d1f; }}
  .hero .btn-r {{ background:rgba(255,255,255,0.2); color:#fff; }}
  .hero .btn-r:hover {{ background:rgba(255,255,255,0.35); }}
  .hero .src {{ color:rgba(255,255,255,0.4); }}

  .ft {{ text-align:center; color:#aeaeb2; font-size:0.72em; padding:20px 14px 28px; }}

  /* 视频板块 */
  .vsection {{ margin-top:14px; }}
  .vsection-title {{
    font-size:0.95em; font-weight:700; color:#9333ea; margin-bottom:10px;
    padding-left:2px; letter-spacing:0.5px;
  }}
  .vgrid {{ display:flex; flex-direction:column; gap:10px; }}
  .vcard {{
    display:flex; gap:12px; background:#fff; border-radius:10px; overflow:hidden;
    box-shadow:0 1px 3px rgba(0,0,0,0.04);
    transition: transform 0.15s, box-shadow 0.15s;
  }}
  .vcard:hover {{ transform:translateY(-2px); box-shadow:0 4px 12px rgba(0,0,0,0.08); }}
  .vcard-img {{
    width:140px; min-height:80px; flex-shrink:0; background-size:cover; background-position:center;
    background-color:#e5e7eb; position:relative; display:block; text-decoration:none;
  }}
  .vcard-dur {{
    position:absolute; bottom:4px; right:4px; background:rgba(0,0,0,0.75); color:#fff;
    font-size:0.65em; padding:1px 5px; border-radius:3px; font-weight:600;
  }}
  .vcard-info {{ flex:1; padding:10px 12px 10px 0; min-width:0; display:flex; flex-direction:column; justify-content:center; }}
  .vcard-t {{
    font-size:0.85em; font-weight:700; color:#1d1d1f; line-height:1.4; margin-bottom:4px;
    display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;
  }}
  .vcard-meta {{ font-size:0.72em; color:#86868b; }}
</style>
</head>
<body>
  <div class="hdr">
    <h1>{label}</h1>
    <div class="sub">{date_str} · {len(items_flat)} 条精选</div>
  </div>
  <div class="wrap">
  <div class="ov">
    <h3>今日概览</h3>
    <ul>"""

    for cat, items in groups.items():
        titles = "、".join(item["title"] for item in items[:3])
        more = f" 等{len(items)}条" if len(items) > 3 else ""
        page_html += f'\n      <li><strong>{cat}</strong>：{titles}{more}</li>'

    # 将 tiles 2-5 包裹在 grid 容器里
    cards_html = cards_html.replace('<!--TILES-->', '')

    page_html += f"""
    </ul>
  </div>
  {cards_html}
  </div>
  <div class="ft">本文由 AI 自动整理 · 内容仅供参考</div>

  <script>
  async function toggleLang(btn) {{
    var card = btn.closest('[data-original-lang]');
    var content = card.querySelector('.hero-s, .tile-s, .row-s');
    if (!content) content = card;
    var originalLang = card.dataset.originalLang;

    if (card.dataset.translated) {{
      if (card.dataset.showing === 'translated') {{
        content.textContent = card.dataset.originalText;
        card.dataset.showing = 'original';
        btn.textContent = originalLang === 'zh' ? 'EN' : '中文';
        btn.classList.remove('active');
      }} else {{
        content.textContent = card.dataset.translated;
        card.dataset.showing = 'translated';
        btn.textContent = originalLang === 'zh' ? '中文' : 'EN';
        btn.classList.add('active');
      }}
      return;
    }}

    var text = content.textContent;
    card.dataset.originalText = text;
    card.dataset.showing = 'original';
    btn.textContent = '...';
    btn.disabled = true;

    var targetLang = originalLang === 'zh' ? 'en' : 'zh-CN';
    var sourceLang = originalLang === 'zh' ? 'zh-CN' : 'en';

    try {{
      var url = 'https://api.mymemory.translated.net/get?q=' +
                encodeURIComponent(text.substring(0, 500)) +
                '&langpair=' + sourceLang + '|' + targetLang;
      var resp = await fetch(url);
      var data = await resp.json();
      var translated = data.responseData.translatedText;
      card.dataset.translated = translated;
      content.textContent = translated;
      card.dataset.showing = 'translated';
      btn.textContent = originalLang === 'zh' ? '中文' : 'EN';
      btn.classList.add('active');
    }} catch(e) {{
      btn.textContent = '失败';
      setTimeout(function() {{ btn.textContent = originalLang === 'zh' ? 'EN' : '中文'; }}, 2000);
    }}
    btn.disabled = false;
  }}
  </script>
</body>
</html>"""

    return page_html
