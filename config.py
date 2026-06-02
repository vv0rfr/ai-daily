import os
from dotenv import load_dotenv

load_dotenv()

# AI API（支持 DeepSeek 或 Claude）
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")  # Claude API（备用）
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")    # DeepSeek API（优先使用）
DEEPSEEK_API_URL = "https://api.deepseek.com"

# === AI 垂直频道数据源 ===
AI_FEEDS = {
    "AI HOT 精选": "https://aihot.virxact.com/feed.xml",
    "AI HOT 日报": "https://aihot.virxact.com/feed/daily.xml",
    "Hugging Face": "https://huggingface.co/blog/feed.xml",
    "Simon Willison": "https://simonwillison.net/atom/everything/",
    "The Decoder": "https://the-decoder.com/feed/",
}

# === 科技频道数据源 ===
TECH_FEEDS = {
    "36氪": "https://36kr.com/feed",
    "Hacker News": "https://hnrss.org/frontpage",
    "Product Hunt": "https://www.producthunt.com/feed",
    "掘金": "https://juejin.cn/rss",
    "IT之家": "https://www.ithome.com/rss/",
    "少数派": "https://sspai.com/feed",
}

# 筛选配置
TOP_N = 5  # 每次生成文章取 Top N 条（精简排版）
VIDEO_TOP_N = 3  # 视频取 Top N 条

# B站视频搜索关键词
BILIBILI_KEYWORDS = [
    "AI 采访",
    "AI 访谈",
    "人工智能 采访",
    "人工智能 访谈",
    "AI agent 采访",
    "大模型 采访",
    "AI 深度访谈",
    "AI CEO 访谈",
]

# AI 频道分类
AI_CATEGORIES = ["模型", "产品", "行业", "论文", "技巧"]

# 科技频道分类
TECH_CATEGORIES = ["AI/大模型", "产品/创业", "开发/技术", "硬件/芯片", "行业/商业"]

# 公众号配置
WECHAT_APP_ID = os.getenv("WECHAT_APP_ID", "")
WECHAT_APP_SECRET = os.getenv("WECHAT_APP_SECRET", "")

# 配图配置
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")  # Unsplash API（免费，可选）
# 无 Key 时自动使用 Picsum 随机图（免费，无需注册）

# 输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
