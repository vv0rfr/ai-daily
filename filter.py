"""按分类分组、筛选排序，支持 AI / 科技两种模式"""

from config import TOP_N

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


def classify(text: str, keywords: dict, default: str) -> str:
    """根据关键词匹配分类"""
    text_lower = text.lower()
    scores = {}
    for cat, kws in keywords.items():
        score = sum(1 for kw in kws if kw.lower() in text_lower)
        if score > 0:
            scores[cat] = score
    if scores:
        return max(scores, key=scores.get)
    return default


def filter_and_group(items: list[dict], top_n: int = TOP_N, mode: str = "ai", video_top_n: int = 0) -> dict:
    """
    对条目进行分类分组，取 Top N。
    mode: "ai" | "tech"
    video_top_n: 视频取 Top N（0 表示不单独处理视频）
    返回: {"分类名": [条目列表], ...}
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

    # 文章分类
    for item in article_items:
        text = item["title"] + " " + item.get("summary", "")
        item["category"] = classify(text, keywords, default_cat)

    # 国内可访问的源优先排前面
    article_items.sort(key=lambda x: (0 if x.get("accessible") else 1))

    # 文章取前 top_n 条
    selected_articles = article_items[:top_n]

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

    return groups
