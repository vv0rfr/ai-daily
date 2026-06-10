"""从多个 RSS 源抓取数据，支持 AI / 科技两种模式"""

import re
import time
import hashlib
import urllib.parse
import requests
import feedparser
from datetime import datetime, timezone, timedelta
from config import AI_FEEDS, TECH_FEEDS, BILIBILI_KEYWORDS, TIME_FILTER_HOURS

MAX_SUMMARY_LEN = 120

# 杂糅合集类标题，直接过滤
ROUNDUP_PATTERNS = [
    r"\d+点\d+氪", r"晚报", r"早报", r"午报", r"速报",
    r"热点导览", r"热点速览", r"大新闻", r"快讯合集",
    r"一周回顾", r"每日\d+条", r"今日热点",
    r"要闻\d+条", r"速览", r"合集",
]

# AI 相关关键词
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

JUNK_PATTERNS = [
    r"钓[鱼马]", r"去温榆河", r"晚上再测", r"不管什么",
    r"额度重置", r"异常改期", r"周四.*周五",
]

ACCESSIBLE_DOMAINS = [
    "ithome.com", "36kr.com", "sspai.com", "juejin.cn",
    "zhihu.com", "bilibili.com", "mp.weixin.qq.com",
    "cnbeta.com", "pingwest.com", "leiphone.com",
    "jiqizhixin.com", "techcrunch.cn", "infoq.cn",
    "huggingface.co", "github.com", "arxiv.org",
    "simonwillison.net", "the-decoder.com", "techcrunch.com",
]


def clean_summary(text: str) -> str:
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
    chinese_chars = len(re.findall(r"[一-鿿]", text))
    return chinese_chars >= 5


def is_junk(title: str, summary: str) -> bool:
    text = title + " " + summary
    for pattern in JUNK_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def is_accessible(url: str) -> bool:
    from urllib.parse import urlparse
    domain = urlparse(url).netloc.lower().replace("www.", "")
    return any(d in domain for d in ACCESSIBLE_DOMAINS)


def is_ai_related(title: str, summary: str) -> bool:
    text = (title + " " + summary).lower()
    for kw in AI_KEYWORDS:
        if kw.lower() in text:
            return True
    return False


def deduplicate_similar(items: list[dict]) -> list[dict]:
    """对同一主题的多条报道只保留最详细的一条，打印被去重的文章对"""
    seen_keys = {}
    result = []
    deduped_pairs = []
    for item in items:
        short = re.sub(r"[^一-龥a-zA-Z0-9]", "", item["title"][:20]).lower()
        if short in seen_keys:
            existing = seen_keys[short]
            if len(item["summary"]) > len(existing["summary"]):
                deduped_pairs.append((existing["title"][:40], item["title"][:40], "保留后者"))
                result[result.index(existing)] = item
                seen_keys[short] = item
            else:
                deduped_pairs.append((item["title"][:40], existing["title"][:40], "保留前者"))
        else:
            seen_keys[short] = item
            result.append(item)
    if deduped_pairs:
        print(f"  [fetcher] 同主题去重：{len(items)} → {len(result)} 条")
        for old, new, reason in deduped_pairs[:5]:
            print(f"    去重: [{old}] vs [{new}] ({reason})")
        if len(deduped_pairs) > 5:
            print(f"    ...还有 {len(deduped_pairs) - 5} 对")
    return result


def _extract_entry(entry) -> dict | None:
    """从 feed entry 中统一提取字段，兼容 Atom / RSS 2.0"""
    title = entry.get("title", "").strip()
    if not title:
        return None

    # 摘要：兼容多种字段（Atom / RSS 2.0）
    raw_summary = (
        entry.get("summary")
        or entry.get("description")
        or entry.get("summary_detail", {}).get("value", "")
        or ""
    )
    # Atom 格式可能用 content 字段
    if not raw_summary or len(raw_summary) < 10:
        content = entry.get("content")
        if isinstance(content, list) and content:
            raw_summary = content[0].get("value", "")
        elif isinstance(content, str):
            raw_summary = content
        # content_detail 兜底
        if not raw_summary or len(raw_summary) < 10:
            cd = entry.get("content_detail") or entry.get("content", [])
            if isinstance(cd, list) and cd:
                raw_summary = cd[0].get("value", "")

    # 链接
    link = entry.get("link", "")
    if not link:
        links = entry.get("links", [])
        if links:
            link = links[0].get("href", "")

    # 发布时间：兼容多种字段
    pub_date = None
    for date_field in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = getattr(entry, date_field, None) or entry.get(date_field)
        if parsed:
            try:
                pub_date = datetime(*parsed[:6], tzinfo=timezone.utc)
            except Exception:
                pass
            break

    # guid
    guid = entry.get("guid", entry.get("id", ""))

    return {
        "title": title,
        "link": link,
        "raw_summary": raw_summary,
        "pub_date": pub_date,
        "guid": guid,
        "author": entry.get("author", ""),
    }


def fetch_feed(name: str, url: str, ai_only: bool = False) -> tuple[list[dict], int, str]:
    """抓取单个 RSS feed，返回 (items, 被时间过滤丢弃数, 错误信息)"""
    feed = None
    http_status = None
    error_msg = ""

    # 先用 requests 拉内容
    try:
        resp = requests.get(url, headers={"User-Agent": "ai-daily/1.0"},
                            timeout=(5, 10))
        http_status = resp.status_code
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
    except requests.exceptions.SSLError:
        print(f"  [fetcher] SSL 证书验证失败，重试（verify=False）：{url}")
        try:
            resp = requests.get(url, headers={"User-Agent": "ai-daily/1.0"},
                                timeout=(5, 10), verify=False)
            http_status = resp.status_code
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as e2:
            error_msg = f"SSL 重试失败: {type(e2).__name__}"
            return [], 0, error_msg
    except requests.exceptions.ConnectTimeout:
        error_msg = "连接超时 (5s)"
        return [], 0, error_msg
    except requests.exceptions.ReadTimeout:
        error_msg = "读取超时 (10s)"
        return [], 0, error_msg
    except requests.exceptions.ConnectionError as e:
        if "Name or service not known" in str(e) or "getaddrinfo" in str(e):
            error_msg = "DNS 解析失败"
        else:
            error_msg = f"连接异常: {e}"
        return [], 0, error_msg
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP {http_status}"
        return [], 0, error_msg
    except Exception as e:
        error_msg = f"请求异常: {type(e).__name__}"
        # 回退到 feedparser 直接解析
        try:
            feed = feedparser.parse(url)
        except Exception:
            return [], 0, error_msg

    if feed is None:
        return [], 0, "feed 解析失败"

    # 检查 feed 解析是否有异常
    if feed.bozo and not feed.entries:
        # 某些 feed 有 XML 格式问题但仍能解析出条目
        if hasattr(feed, 'bozo_exception'):
            exc_name = type(feed.bozo_exception).__name__
            error_msg = f"feed 解析异常: {exc_name}"
        else:
            error_msg = "feed 解析异常"
        return [], 0, error_msg

    items = []
    time_filtered = 0
    cutoff = datetime.now(timezone.utc) - timedelta(hours=TIME_FILTER_HOURS)

    for entry in feed.entries:
        extracted = _extract_entry(entry)
        if not extracted:
            continue

        title = extracted["title"]
        summary = clean_summary(extracted["raw_summary"])

        if is_roundup(title):
            continue
        if len(summary) < 10:
            continue
        if is_junk(title, summary):
            continue
        if ai_only and not is_ai_related(title, summary):
            continue

        # 时间过滤
        if extracted["pub_date"] and extracted["pub_date"] < cutoff:
            time_filtered += 1
            continue

        link = extracted["link"]
        lang = "zh" if is_chinese(title + summary) else "en"
        items.append({
            "title": title,
            "link": link,
            "summary": summary,
            "source": name,
            "author": extracted["author"] or name,
            "pub_date": extracted["pub_date"],
            "guid": extracted["guid"],
            "accessible": is_accessible(link),
            "lang": lang,
        })

    return items, time_filtered, ""


def fetch_from(feeds: dict, label: str, ai_only: bool = False) -> list[dict]:
    """从指定的 feeds 字典抓取所有数据"""
    all_items = []
    total_sources = len(feeds)
    success_count = 0
    fail_count = 0
    source_stats = []

    for name, url in feeds.items():
        items, time_filtered, error = fetch_feed(name, url, ai_only=ai_only)

        if error:
            print(f"  [fetcher] {name}: 失败 - {error}")
            fail_count += 1
            source_stats.append((name, 0, error))
        elif not items and time_filtered == 0:
            print(f"  [fetcher] {name}: feed 解析成功但无条目")
            success_count += 1
            source_stats.append((name, 0, "无条目"))
        elif not items and time_filtered > 0:
            print(f"  [fetcher] {name}: 抓到 {time_filtered} 条但全部被时间过滤丢弃")
            success_count += 1
            source_stats.append((name, 0, f"时间过滤丢弃 {time_filtered}"))
        else:
            msg = f"{len(items)} 条"
            if time_filtered > 0:
                msg += f"（另有 {time_filtered} 条被时间过滤丢弃）"
            print(f"  [fetcher] {name}: {msg}")
            all_items.extend(items)
            success_count += 1
            source_stats.append((name, len(items), ""))

    # 汇总
    print(f"\n  [fetcher] 源汇总：共 {total_sources} 个，成功 {success_count}，失败 {fail_count}")
    ranked = [(n, c) for n, c, e in source_stats if c > 0]
    if ranked:
        ranked.sort(key=lambda x: x[1], reverse=True)
        print(f"  [fetcher] 条目排名：", end="")
        for n, c in ranked:
            print(f"  {n}({c})", end="")
        print()

    # 按 guid 去重
    seen = set()
    unique = []
    for item in all_items:
        key = item["guid"] or item["link"]
        if key and key not in seen:
            seen.add(key)
            unique.append(item)

    before_dedup = len(unique)
    unique = deduplicate_similar(unique)

    print(f"  [fetcher] {label} 合计：{len(unique)} 条（去重前 {before_dedup}）")
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


def check_sources():
    """诊断所有 RSS 源的可访问性和解析状态"""
    print(f"\n{'='*80}")
    print("  RSS 源诊断")
    print(f"{'='*80}\n")

    all_feeds = {**AI_FEEDS, **TECH_FEEDS}
    results = []

    for name, url in all_feeds.items():
        print(f"  测试 {name} ...", end="", flush=True)
        http_status = "-"
        parsed_count = 0
        latest_pub = "-"
        time_dropped = 0
        error = ""

        try:
            resp = requests.get(url, headers={"User-Agent": "ai-daily/1.0"},
                                timeout=(5, 10))
            http_status = resp.status_code
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            parsed_count = len(feed.entries)

            # 找最新发布时间
            latest = None
            for entry in feed.entries[:3]:
                for field in ("published_parsed", "updated_parsed"):
                    p = getattr(entry, field, None)
                    if p:
                        try:
                            dt = datetime(*p[:6], tzinfo=timezone.utc)
                            if not latest or dt > latest:
                                latest = dt
                        except Exception:
                            pass
                        break
            if latest:
                age_hours = (datetime.now(timezone.utc) - latest).total_seconds() / 3600
                latest_pub = f"{age_hours:.0f}h前"

            # 统计被时间过滤丢弃的
            cutoff = datetime.now(timezone.utc) - timedelta(hours=TIME_FILTER_HOURS)
            for entry in feed.entries:
                for field in ("published_parsed", "updated_parsed"):
                    p = getattr(entry, field, None)
                    if p:
                        try:
                            dt = datetime(*p[:6], tzinfo=timezone.utc)
                            if dt < cutoff:
                                time_dropped += 1
                        except Exception:
                            pass
                        break

            print(f" OK ({parsed_count}条)")
        except requests.exceptions.ConnectTimeout:
            error = "连接超时"
            print(f" FAIL: {error}")
        except requests.exceptions.ReadTimeout:
            error = "读取超时"
            print(f" FAIL: {error}")
        except requests.exceptions.ConnectionError as e:
            if "getaddrinfo" in str(e) or "Name or service" in str(e):
                error = "DNS解析失败"
            else:
                error = "连接异常"
            print(f" FAIL: {error}")
        except requests.exceptions.SSLError:
            print(f" SSL，重试...", end="", flush=True)
            try:
                resp = requests.get(url, headers={"User-Agent": "ai-daily/1.0"},
                                    timeout=(5, 10), verify=False)
                http_status = resp.status_code
                resp.raise_for_status()
                feed = feedparser.parse(resp.content)
                parsed_count = len(feed.entries)
                print(f" OK ({parsed_count}条, SSL跳过验证)")
            except Exception as e2:
                error = f"SSL重试失败: {type(e2).__name__}"
                print(f" FAIL: {error}")
        except requests.exceptions.HTTPError:
            error = f"HTTP {http_status}"
            print(f" FAIL: {error}")
        except Exception as e:
            error = f"{type(e).__name__}"
            print(f" FAIL: {error}")

        results.append((name, url, str(http_status), parsed_count, latest_pub, time_dropped, error))

    # 打印表格
    print(f"\n  {'源名':<16} {'HTTP':>4} {'条目':>4} {'最新':>6} {'丢弃':>4} {'状态'}")
    print(f"  {'-'*60}")
    for name, url, status, count, latest, dropped, error in results:
        status_str = error if error else "OK"
        print(f"  {name:<16} {status:>4} {count:>4} {latest:>6} {dropped:>4} {status_str}")

    # 单独测试三个问题源
    print(f"\n  {'='*60}")
    print("  重点测试：三个零贡献源")
    print(f"  {'='*60}")
    problem_sources = [
        ("Simon Willison", "https://simonwillison.net/atom/everything/"),
        ("The Decoder", "https://the-decoder.com/feed/"),
        ("Hugging Face", "https://huggingface.co/blog/feed.xml"),
    ]
    for name, url in problem_sources:
        print(f"\n  [{name}]")
        print(f"  URL: {url}")
        try:
            resp = requests.get(url, headers={"User-Agent": "ai-daily/1.0"},
                                timeout=(5, 10))
            print(f"  状态码: {resp.status_code}")
            print(f"  响应前300字符: {resp.text[:300]}")
        except Exception as e:
            print(f"  错误: {e}")

    print(f"\n{'='*80}\n")


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
    mixin_key = _get_mixin_key(img_key + sub_key)
    params["wts"] = round(time.time())
    params = dict(sorted(params.items()))
    params = {k: "".join(ch for ch in str(v) if ch not in "!'()*") for k, v in params.items()}
    query = urllib.parse.urlencode(params)
    params["w_rid"] = hashlib.md5((query + mixin_key).encode()).hexdigest()
    return params


def _get_bilibili_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.bilibili.com",
    })
    spi = session.get("https://api.bilibili.com/x/frontend/finger/spi", timeout=10).json()
    session.cookies.set("buvid3", spi["data"]["b_3"], domain=".bilibili.com")
    session.cookies.set("buvid4", spi["data"]["b_4"], domain=".bilibili.com")
    nav = session.get("https://api.bilibili.com/x/web-interface/nav", timeout=10).json()
    img_url = nav["data"]["wbi_img"]["img_url"]
    sub_url = nav["data"]["wbi_img"]["sub_url"]
    img_key = img_url.rsplit("/", 1)[-1].split(".")[0]
    sub_key = sub_url.rsplit("/", 1)[-1].split(".")[0]
    return session, img_key, sub_key


def _search_bilibili(session, img_key: str, sub_key: str, keyword: str, page: int = 1) -> list[dict]:
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
            params=params, timeout=15,
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
    return re.sub(r"<[^>]+>", "", title)


def fetch_bilibili_videos(keywords: list[str] = None) -> list[dict]:
    if keywords is None:
        keywords = BILIBILI_KEYWORDS

    print("  [fetcher] B站视频搜索...")
    try:
        session, img_key, sub_key = _get_bilibili_session()
    except Exception as e:
        print(f"  [fetcher] B站初始化失败：{e}")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=TIME_FILTER_HOURS)
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
                pub_ts = r.get("pubdate", 0)
                if pub_ts:
                    pub_dt = datetime.fromtimestamp(pub_ts, tz=timezone.utc)
                    if pub_dt < cutoff:
                        continue
                seen_bvids.add(bvid)
                title = _clean_bili_title(r.get("title", ""))
                desc = r.get("description", "")
                combined = (title + " " + desc).upper()
                ai_hits = sum(1 for kw in AI_KEYWORDS if kw.upper() in combined)
                if ai_hits == 0:
                    continue
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

    all_videos.sort(key=lambda x: x.get("play", 0), reverse=True)
    print(f"  [fetcher] B站视频合计：{len(all_videos)} 条")
    return all_videos
