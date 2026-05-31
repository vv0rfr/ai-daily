"""从多个 RSS 源抓取数据，支持 AI / 科技两种模式"""

import re
import time
import hashlib
import urllib.parse
import requests
import feedparser
from datetime import datetime, timezone, timedelta
from config import AI_FEEDS, TECH_FEEDS, BILIBILI_KEYWORDS

MAX_SUMMARY_LEN = 120

# 杂糅合集类标题，直接过滤
ROUNDUP_PATTERNS = [
    r"\d+点\d+氪", r"晚报", r"早报", r"午报", r"速报",
    r"热点导览", r"热点速览", r"大新闻", r"快讯合集",
    r"一周回顾", r"每日\d+条", r"今日热点",
    r"要闻\d+条", r"速览", r"合集",
]

# AI 相关关键词（标题或摘要里有这些才算 AI 内容）
AI_KEYWORDS = [
    "AI", "人工智能", "大模型", "LLM", "GPT", "Claude", "Gemini", "Llama",
    "Qwen", "DeepSeek", "Opus", "Sonnet", "ChatGPT", "Copilot", "Cursor",
    "智能体", "Agent", "机器学习", "深度学习", "神经网络", "Transformer",
    "RAG", "MCP", "token", "推理", "训练", "微调", "开源模型", "benchmark",
    "Sora", "Midjourney", "Stable Diffusion", "Diffusion", "生成式",
    "Anthropic", "OpenAI", "DeepMind", "xAI", "Grok", "Mistral",
    "Hugging Face", "CUDA", "GPU", "NVIDIA", "英伟达", "算力",
    "多模态", "Vision", "embedding", "向量", "fine-tune", "LoRA",
    "prompt", "提示词", "上下文", "context window", "AGI", "ASI",
    "ElevenLabs", "Runway", "Perplexity", "Poe", "Kimi", "豆包",
    "阶跃星辰", "Step", "MiniMax", "智谱", "GLM", "通义",
    "论文", "paper", "arXiv", "benchmark", "评测",
    "vLLM", "SGLang", "Ollama", "llama.cpp", "GGUF",
    "Claude Code", "Codex", "Windsurf", "Cline", "Aider",
    "robot", "机器人", "具身", "自动驾驶", "FSD",
]

# 个人闲聊/非技术内容，过滤掉
JUNK_PATTERNS = [
    r"钓[鱼马]", r"去温榆河", r"晚上再测", r"不管什么",
    r"额度重置", r"异常改期", r"周四.*周五",
]

# 国内可访问的域名
ACCESSIBLE_DOMAINS = [
    "ithome.com", "36kr.com", "sspai.com", "juejin.cn",
    "zhihu.com", "bilibili.com", "mp.weixin.qq.com",
    "cnbeta.com", "pingwest.com", "leiphone.com",
    "jiqizhixin.com", "techcrunch.cn", "infoq.cn",
    "huggingface.co", "github.com", "arxiv.org",
    "simonwillison.net", "the-decoder.com",
]


def clean_summary(text: str) -> str:
    """清理 HTML 标签，截断摘要"""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&[a-z]+;", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > MAX_SUMMARY_LEN:
        text = text[:MAX_SUMMARY_LEN] + "..."
    return text


def is_roundup(title: str) -> bool:
    for pattern in ROUNDUP_PATTERNS:
        if re.search(pattern, title):
            return True
    return False


def is_chinese(text: str) -> bool:
    """判断文本是否包含足够多的中文字符"""
    chinese_chars = len(re.findall(r"[一-鿿]", text))
    return chinese_chars >= 5  # 至少5个中文字符才算中文内容


def is_junk(title: str, summary: str) -> bool:
    """判断是否为垃圾内容（闲聊、非技术）"""
    text = title + " " + summary
    for pattern in JUNK_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def is_accessible(url: str) -> bool:
    """判断链接在国内是否可访问"""
    from urllib.parse import urlparse
    domain = urlparse(url).netloc.lower().replace("www.", "")
    return any(d in domain for d in ACCESSIBLE_DOMAINS)


def is_ai_related(title: str, summary: str) -> bool:
    """判断是否与 AI 相关"""
    text = (title + " " + summary).lower()
    for kw in AI_KEYWORDS:
        if kw.lower() in text:
            return True
    return False


def deduplicate_similar(items: list[dict]) -> list[dict]:
    """对同一主题的多条报道只保留最详细的一条"""
    # 按关键词聚类：标题前15字相同的合并
    seen_keys = {}
    result = []
    for item in items:
        # 用标题前20字作为粗略去重 key
        short = re.sub(r"[^一-龥a-zA-Z0-9]", "", item["title"][:20]).lower()
        if short in seen_keys:
            # 已有同主题，保留摘要更长的
            existing = seen_keys[short]
            if len(item["summary"]) > len(existing["summary"]):
                result[result.index(existing)] = item
                seen_keys[short] = item
        else:
            seen_keys[short] = item
            result.append(item)
    return result


def fetch_feed(name: str, url: str, ai_only: bool = False) -> list[dict]:
    """抓取单个 RSS feed（先用 requests 拉内容，避免 feedparser 的 304 缓存）"""
    try:
        resp = requests.get(url, headers={"User-Agent": "ai-daily/1.0"}, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
    except Exception:
        # 回退到直接解析
        feed = feedparser.parse(url)
    items = []
    for entry in feed.entries:
        pub_date = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

        raw_summary = entry.get("description", entry.get("summary", ""))
        title = entry.get("title", "").strip()
        summary = clean_summary(raw_summary)

        if is_roundup(title):
            continue
        if len(summary) < 10:
            continue
        if is_junk(title, summary):
            continue
        # AI 频道：只保留 AI 相关内容（不限语言）
        if ai_only and not is_ai_related(title, summary):
            continue

        link = entry.get("link", "")
        lang = "zh" if is_chinese(title + summary) else "en"
        items.append({
            "title": title,
            "link": link,
            "summary": summary,
            "source": name,
            "author": entry.get("author", name),
            "pub_date": pub_date,
            "guid": entry.get("guid", entry.get("id", "")),
            "accessible": is_accessible(link),
            "lang": lang,
        })
    return items


def filter_by_time(items: list[dict], hours: int = 24) -> list[dict]:
    """只保留最近 N 小时内的内容"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    filtered = []
    for item in items:
        if item["pub_date"] and item["pub_date"] >= cutoff:
            filtered.append(item)
        elif item["pub_date"] is None:
            filtered.append(item)
    before = len(items)
    after = len(filtered)
    if before != after:
        print(f"  [fetcher] 时间过滤：{before} → {after} 条（保留最近 {hours} 小时）")
    return filtered


def fetch_from(feeds: dict, label: str, ai_only: bool = False) -> list[dict]:
    """从指定的 feeds 字典抓取所有数据"""
    all_items = []
    for name, url in feeds.items():
        try:
            items = fetch_feed(name, url, ai_only=ai_only)
            all_items.extend(items)
            print(f"  [fetcher] {name}: {len(items)} 条")
        except Exception as e:
            print(f"  [fetcher] {name}: 失败 - {e}")

    # 按 guid 去重
    seen = set()
    unique = []
    for item in all_items:
        key = item["guid"] or item["link"]
        if key and key not in seen:
            seen.add(key)
            unique.append(item)

    # 同主题去重
    before_dedup = len(unique)
    unique = deduplicate_similar(unique)
    if before_dedup != len(unique):
        print(f"  [fetcher] 同主题去重：{before_dedup} → {len(unique)} 条")

    # 时间过滤
    unique = filter_by_time(unique, hours=24)

    print(f"  [fetcher] {label} 合计：{len(unique)} 条")
    return unique


def fetch_ai() -> list[dict]:
    """抓取 AI 垂直频道（只保留 AI 相关内容）"""
    return fetch_from(AI_FEEDS, "AI 频道", ai_only=True)


def fetch_tech() -> list[dict]:
    """抓取科技频道"""
    return fetch_from(TECH_FEEDS, "科技频道", ai_only=False)


def fetch_all() -> list[dict]:
    """抓取所有源（AI + 科技）"""
    ai = fetch_ai()
    tech = fetch_tech()
    seen = {item["guid"] or item["link"] for item in ai}
    for item in tech:
        key = item["guid"] or item["link"]
        if key not in seen:
            ai.append(item)
            seen.add(key)
    return ai


# === B站视频搜索 ===

MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
]


def _get_mixin_key(orig: str) -> str:
    return "".join(orig[i] for i in MIXIN_KEY_ENC_TAB)[:32]


def _enc_wbi(params: dict, img_key: str, sub_key: str) -> dict:
    """WBI 签名"""
    mixin_key = _get_mixin_key(img_key + sub_key)
    params["wts"] = round(time.time())
    params = dict(sorted(params.items()))
    params = {k: "".join(ch for ch in str(v) if ch not in "!'()*") for k, v in params.items()}
    query = urllib.parse.urlencode(params)
    params["w_rid"] = hashlib.md5((query + mixin_key).encode()).hexdigest()
    return params


def _get_bilibili_session():
    """创建 B站 session，获取 buvid cookie 和 WBI keys"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.bilibili.com",
    })

    # 获取设备指纹
    spi = session.get("https://api.bilibili.com/x/frontend/finger/spi", timeout=10).json()
    session.cookies.set("buvid3", spi["data"]["b_3"], domain=".bilibili.com")
    session.cookies.set("buvid4", spi["data"]["b_4"], domain=".bilibili.com")

    # 获取 WBI keys
    nav = session.get("https://api.bilibili.com/x/web-interface/nav", timeout=10).json()
    img_url = nav["data"]["wbi_img"]["img_url"]
    sub_url = nav["data"]["wbi_img"]["sub_url"]
    img_key = img_url.rsplit("/", 1)[-1].split(".")[0]
    sub_key = sub_url.rsplit("/", 1)[-1].split(".")[0]

    return session, img_key, sub_key


def _search_bilibili(session, img_key: str, sub_key: str, keyword: str, page: int = 1) -> list[dict]:
    """搜索单个关键词，返回视频列表"""
    params = {
        "keyword": keyword,
        "search_type": "video",
        "page": page,
        "order": "pubdate",
    }
    params = _enc_wbi(params, img_key, sub_key)
    try:
        resp = session.get(
            "https://api.bilibili.com/x/web-interface/wbi/search/all/v2",
            params=params,
            timeout=15,
        )
        data = resp.json()
        if data.get("code") != 0:
            return []
        for item in data.get("data", {}).get("result", []):
            if item.get("result_type") == "video":
                return item.get("data", [])
    except Exception:
        pass
    return []


def _clean_bili_title(title: str) -> str:
    """清理 B站搜索结果中的 HTML 标签"""
    return re.sub(r"<[^>]+>", "", title)


def fetch_bilibili_videos(keywords: list[str] = None) -> list[dict]:
    """从 B站搜索 AI 相关视频，返回统一格式的条目列表"""
    if keywords is None:
        keywords = BILIBILI_KEYWORDS

    print("  [fetcher] B站视频搜索...")
    try:
        session, img_key, sub_key = _get_bilibili_session()
    except Exception as e:
        print(f"  [fetcher] B站初始化失败：{e}")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    seen_bvids = set()
    all_videos = []

    for kw in keywords:
        try:
            results = _search_bilibili(session, img_key, sub_key, kw)
            count = 0
            for r in results:
                bvid = r.get("bvid", "")
                if not bvid or bvid in seen_bvids:
                    continue

                # 时间过滤
                pub_ts = r.get("pubdate", 0)
                if pub_ts:
                    pub_dt = datetime.fromtimestamp(pub_ts, tz=timezone.utc)
                    if pub_dt < cutoff:
                        continue

                seen_bvids.add(bvid)
                title = _clean_bili_title(r.get("title", ""))
                desc = r.get("description", "")

                # AI 相关性过滤：标题或描述必须包含 AI 相关关键词
                combined = (title + " " + desc).upper()
                ai_hits = sum(1 for kw in AI_KEYWORDS if kw.upper() in combined)
                if ai_hits == 0:
                    continue

                # 排除明显非资讯类视频（AI漫剧、AI真人版、AI绘画教程等）
                title_lower = title.lower()
                junk_pats = ["漫剧", "真人版", "免费全集", "一口气看完", "AI绘画教程",
                             "AI画图", "AI作图", "AI写真", "赢麻了", "玄学", "玄门"]
                if any(p in title_lower for p in junk_pats):
                    continue

                if len(desc) > MAX_SUMMARY_LEN:
                    desc = desc[:MAX_SUMMARY_LEN] + "..."

                pic = r.get("pic", "")
                if pic.startswith("//"):
                    pic = "https:" + pic

                all_videos.append({
                    "title": title,
                    "link": r.get("arcurl", f"https://www.bilibili.com/video/{bvid}"),
                    "summary": desc,
                    "source": "B站",
                    "author": r.get("author", ""),
                    "pub_date": pub_dt if pub_ts else None,
                    "guid": bvid,
                    "accessible": True,
                    "lang": "zh",
                    "type": "video",
                    "thumbnail": pic,
                    "play": r.get("play", 0),
                    "duration": r.get("duration", ""),
                })
                count += 1
            print(f"    关键词「{kw}」：{count} 条")
        except Exception as e:
            print(f"    关键词「{kw}」：失败 - {e}")

    # 按播放量排序
    all_videos.sort(key=lambda x: x.get("play", 0), reverse=True)
    print(f"  [fetcher] B站视频合计：{len(all_videos)} 条")
    return all_videos
