"""按分类分组、筛选排序，支持 AI / 科技两种模式。
分类方式：LLM 优先，关键词兜底。"""

import json
from config import TOP_N, DEEPSEEK_API_KEY, DEEPSEEK_API_URL, ANTHROPIC_API_KEY

# === AI 频道分类关键词 ===
AI_KEYWORDS = {
    "模型": ["模型", "LLM", "GPT", "Claude", "Gemini", "Llama", "Qwen", "DeepSeek",
              "Opus", "Sonnet", "Haiku", "开源", "参数", "benchmark", "评测", "训练",
              "微调", "推理", "AlphaProof", "MoE", "权重"],
    "产品": ["发布", "推出", "上线", "更新", "App", "产品", "工具", "平台", "插件",
             "Cursor", "Copilot", "ChatGPT", "Midjourney", "Sora", "Runway", "Windsurf",
             "Grok", "Replit", "Canvas"],
    "行业": ["融资", "收购", "估值", "上市", "监管", "政策", "合规", "安全", "就业", "裁员",
             "谷歌", "Google", "微软", "Microsoft", "苹果", "Apple", "Meta", "英伟达",
             "NVIDIA", "特斯拉", "Tesla", "Anthropic", "OpenAI"],
    "论文": ["论文", "paper", "arXiv", "研究", "实验", "突破", "算法", "架构"],
    "技巧": ["教程", "技巧", "指南", "prompt", "提示词", "workflow", "工作流", "经验", "分享"],
}

# === 科技频道分类关键词 ===
TECH_KEYWORDS = {
    "AI/大模型": ["AI", "大模型", "LLM", "GPT", "Claude", "Gemini", "DeepSeek", "智能体",
                  "Agent", "机器学习", "深度学习", "神经网络", "Transformer", "RAG", "MCP"],
    "产品/创业": ["发布", "上线", "融资", "创业", "产品", "App", "小程序", "SaaS", "增长",
                  "用户", "PMF", "种子轮", "A轮", "IPO", "收购"],
    "开发/技术": ["开源", "GitHub", "框架", "SDK", "API", "前端", "后端", "数据库", "云",
                  "容器", "Docker", "K8s", "Rust", "Go", "Python", "TypeScript", "React"],
    "硬件/芯片": ["芯片", "GPU", "CPU", "内存", "HBM", "手机", "电脑", "服务器", "半导体",
                  "台积电", "TSMC", "高通", "联发科", "苹果M", "骁龙"],
    "行业/商业": ["财报", "营收", "市值", "裁员", "监管", "反垄断", "出海", "全球化",
                  "电商", "短视频", "直播", "支付"],
}

# === LLM 分类 prompt ===
_CLASSIFY_PROMPT_AI = """你是 AI 资讯编辑，负责将文章分到以下 5 个分类之一：

- 模型：大模型发布/更新/评测/训练/微调/推理/架构/开源权重
- 产品：AI 工具/App/平台上线或更新（如 Cursor、ChatGPT、Midjourney）
- 行业：融资/收购/公司动态/政策监管/就业市场
- 论文：学术研究/论文/算法突破/实验结果
- 技巧：教程/指南/prompt 技巧/workflow/使用经验

示例：
- "GPT-5 发布，参数量达 2 万亿" → 模型
- "Cursor 新增多文件编辑功能" → 产品

请对以下文章分类，返回 JSON 数组，每项 {"id": 编号, "category": "分类名"}。
只返回 JSON，不要其他文字。

文章列表：
"""

_CLASSIFY_PROMPT_TECH = """你是科技资讯编辑，负责将文章分到以下 5 个分类之一：

- AI/大模型：AI 技术/大模型/智能体/机器学习相关内容
- 产品/创业：产品发布/创业融资/App 上线/SaaS/用户增长
- 开发/技术：开源项目/框架/编程语言/云服务/DevOps
- 硬件/芯片：芯片/GPU/CPU/手机/电脑/半导体行业
- 行业/商业：财报/营收/裁员/监管/反垄断/商业模式

示例：
- "OpenAI 秘密提交 IPO 申请" → AI/大模型
- "Rust 1.80 发布，新增 async trait 支持" → 开发/技术

请对以下文章分类，返回 JSON 数组，每项 {"id": 编号, "category": "分类名"}。
只返回 JSON，不要其他文字。

文章列表：
"""


def classify(text: str, keywords: dict, default: str) -> str:
    """根据关键词匹配分类（兜底方案）"""
    text_lower = text.lower()
    scores = {}
    for cat, kws in keywords.items():
        score = sum(1 for kw in kws if kw.lower() in text_lower)
        if score > 0:
            scores[cat] = score
    if scores:
        return max(scores, key=scores.get)
    return default


def classify_with_llm(items: list[dict], mode: str) -> tuple[list[dict], str]:
    """用 DeepSeek API 批量分类文章，返回 (更新了 category 的 items, 模型标识)。
    失败时抛出异常，由调用方回退到关键词分类。"""
    if not items:
        return items, "llm"

    # 构建 prompt
    if mode == "tech":
        prompt_prefix = _CLASSIFY_PROMPT_TECH
        valid_cats = set(TECH_KEYWORDS.keys())
        default_cat = "行业/商业"
    else:
        prompt_prefix = _CLASSIFY_PROMPT_AI
        valid_cats = set(AI_KEYWORDS.keys())
        default_cat = "行业"

    article_lines = []
    for i, item in enumerate(items):
        title = item.get("title", "")
        summary = item.get("summary", "")[:100]
        article_lines.append(f"{i}. {title} | {summary}")
    prompt = prompt_prefix + "\n".join(article_lines)

    # 尝试 DeepSeek
    if DEEPSEEK_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_API_URL)
            resp = client.chat.completions.create(
                model="deepseek-chat",
                max_tokens=1024,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.choices[0].message.content.strip()
            results = _parse_classify_json(raw, len(items))
            items = _apply_categories(items, results, valid_cats, default_cat)
            print("  [filter] 使用 LLM 分类 (DeepSeek)")
            return items, "llm"
        except Exception as e:
            print(f"  [filter] DeepSeek 分类失败: {e}")

    # 尝试 Claude
    if ANTHROPIC_API_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            resp = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text.strip()
            results = _parse_classify_json(raw, len(items))
            items = _apply_categories(items, results, valid_cats, default_cat)
            print("  [filter] 使用 LLM 分类 (Claude)")
            return items, "llm"
        except Exception as e:
            print(f"  [filter] Claude 分类失败: {e}")

    raise RuntimeError("无可用 API Key 或全部失败")


def _parse_classify_json(raw: str, expected_count: int) -> list[dict] | None:
    """从 LLM 响应中解析 JSON 数组，容错处理 ```json 包裹"""
    # 去掉可能的 ```json 包裹
    text = raw
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    # 找到 JSON 数组
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        return None
    text = text[start:end + 1]

    try:
        results = json.loads(text)
        if not isinstance(results, list):
            return None
        return results
    except json.JSONDecodeError:
        return None


def _apply_categories(items: list[dict], results: list[dict] | None,
                      valid_cats: set, default_cat: str) -> list[dict]:
    """把 LLM 分类结果应用到 items 上"""
    if results:
        result_map = {}
        for r in results:
            if isinstance(r, dict) and "id" in r and "category" in r:
                result_map[int(r["id"])] = r["category"]

        for i, item in enumerate(items):
            cat = result_map.get(i, "")
            item["category"] = cat if cat in valid_cats else default_cat
    else:
        for item in items:
            item["category"] = default_cat
    return items


def _score_article(item: dict) -> float:
    """给文章打质量分，用于排序优选"""
    score = 0.0
    title = item.get("title", "")
    summary = item.get("summary", "")

    # 可访问的源加分
    if item.get("accessible"):
        score += 3.0

    # 摘要长度加分（信息量）
    score += min(len(summary) / 30, 3.0)

    # 标题含关键 AI 词汇加分
    ai_kw = ["gpt", "claude", "gemini", "llm", "agent", "deepseek", "openai", "anthropic",
              "模型", "发布", "开源", "论文", "benchmark", "评测"]
    for kw in ai_kw:
        if kw.lower() in (title + summary).lower():
            score += 1.5

    # 有发布时间且是最近的加分
    pub = item.get("pub_date")
    if pub:
        from datetime import datetime, timezone
        age_hours = (datetime.now(timezone.utc) - pub).total_seconds() / 3600
        if age_hours < 12:
            score += 2.0
        elif age_hours < 24:
            score += 1.0

    return score


def filter_and_group(items: list[dict], top_n: int = TOP_N, mode: str = "ai",
                     video_top_n: int = 0) -> tuple[dict, str]:
    """
    对条目进行分类分组，取 Top N。
    mode: "ai" | "tech"
    返回: (groups_dict, classify_method)
    """
    if mode == "tech":
        keywords = TECH_KEYWORDS
        default_cat = "行业/商业"
    else:
        keywords = AI_KEYWORDS
        default_cat = "行业"

    # 分离视频和文章
    video_items = [it for it in items if it.get("type") == "video"]
    article_items = [it for it in items if it.get("type") != "video"]

    print(f"  [filter] 输入：{len(article_items)} 篇文章 + {len(video_items)} 个视频")

    # 质量评分排序
    for item in article_items:
        item["_score"] = _score_article(item)
    article_items.sort(key=lambda x: x["_score"], reverse=True)

    # 打印前几条的评分（调试用）
    print(f"  [filter] 文章评分 Top 5：")
    for i, item in enumerate(article_items[:5]):
        print(f"    [{item['_score']:.1f}] {item['title'][:50]}")

    # 取 top_n 条
    selected_articles = article_items[:top_n]
    dropped = article_items[top_n:]

    if dropped:
        print(f"  [filter] 未入选 {len(dropped)} 条（取前 {top_n}）：")
        for item in dropped[:5]:
            print(f"    [{item['_score']:.1f}] {item['title'][:50]}")
        if len(dropped) > 5:
            print(f"    ...还有 {len(dropped) - 5} 条")

    # 文章分类：优先 LLM，失败回退关键词
    classify_method = "keyword"
    try:
        selected_articles, classify_method = classify_with_llm(selected_articles, mode)
    except Exception as e:
        print(f"  [filter] LLM 分类失败，回退到关键词分类: {e}")
        for item in selected_articles:
            text = item["title"] + " " + item.get("summary", "")
            item["category"] = classify(text, keywords, default_cat)
        classify_method = "keyword"

    # 按分类分组
    groups = {}
    for item in selected_articles:
        cat = item["category"]
        if cat not in groups:
            groups[cat] = []
        groups[cat].append(item)

    # 视频单独分组
    if video_items and video_top_n > 0:
        groups["视频"] = video_items[:video_top_n]

    # 打印统计
    total = sum(len(v) for v in groups.values())
    print(f"  [filter] 共筛选 {total} 条，分 {len(groups)} 个分类")
    for cat, group in groups.items():
        print(f"    {cat}: {len(group)} 条")

    return groups, classify_method
