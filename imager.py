"""
自动配图模块 — 为新闻条目智能获取相关配图

使用方式（由 writer.py 调用）：
    from imager import get_image_url
    img_url = get_image_url(item["title"], item["category"])

数据源优先级：
1. Unsplash API（需配置 UNSPLASH_ACCESS_KEY，效果最好）
2. Picsum（免费无Key，随机图但同一关键词结果稳定）
3. 返回 None → 调用方使用纯色渐变兜底
"""
import os
import re
import requests
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# 内存缓存：避免同一批生成中重复请求
_cache = {}


# ── 中文关键词 → 英文搜索词 ──────────────────────────────────
_CATEGORY_EN = {
    "模型": "AI artificial intelligence model",
    "产品": "technology product launch",
    "行业": "technology industry business",
    "论文": "academic research paper",
    "技巧": "tips howto technology",
    "视频": "video creative content",
    "产业": "technology industry",
    "AI/大模型": "AI artificial intelligence",
    "产品/创业": "startup technology",
    "开发/技术": "coding programming",
    "硬件/芯片": "hardware chip processor",
    "行业/商业": "business technology",
}


def _extract_keywords(title: str, category: str) -> str:
    """从标题+分类提取搜索关键词（用于 Unsplash 搜索）"""
    # 移除标点符号
    clean = re.sub(r"[^一-龥a-zA-Z0-9\s]", " ", title)
    # 取前 10 个有意义的字符
    meaningful = clean.split()[:5]
    title_part = ' '.join(meaningful)[:30]

    base = _CATEGORY_EN.get(category, "technology")
    return f"{title_part} {base}"


# ── Unsplash API ──────────────────────────────────────────────

def _unsplash_search(keyword: str):
    """通过 Unsplash API 搜索图片，返回 (url, attribution)"""
    from config import UNSPLASH_ACCESS_KEY

    headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
    params = {
        "query": keyword,
        "per_page": 1,
        "orientation": "landscape",
        "content_filter": "high",
    }

    try:
        resp = requests.get(
            "https://api.unsplash.com/search/photos",
            headers=headers,
            params=params,
            timeout=3,  # 快速失败，走 Picsum 兜底
        )
    except requests.RequestException as e:
        logger.warning(f"Unsplash 请求失败: {e}")
        return None

    if resp.status_code != 200:
        logger.warning(f"Unsplash API 返回 {resp.status_code}: {resp.text[:200]}")
        return None

    data = resp.json()
    if not data.get("results"):
        return None

    result = data["results"][0]
    # 取 regular 尺寸（约 1080px 宽）
    img_url = result["urls"]["regular"]

    # 作者归属信息（Unsplash 要求署名）
    attribution = {
        "name": result["user"]["name"],
        "link": result["links"]["html"],
    }
    logger.info(f"  [imager] Unsplash: {keyword[:20]} → {result['id']} (by {attribution['name']})")
    return img_url, attribution


# ── Picsum 备选 ──────────────────────────────────────────────

def _picsum_fallback(keyword: str) -> str:
    """Picsum.photos 免费随机图（根据 seed 保证稳定性）"""
    seed = keyword.encode("utf-8").hex()[:16]
    return f"https://picsum.photos/seed/{seed}/740/400"


# ── 公开接口 ──────────────────────────────────────────────────

def get_image_url(title: str, category: str) -> tuple:
    """
    获取配图 URL + 归属信息

    返回：
        (image_url, attribution_dict_or_None)
        image_url 为 None 表示无可用图片，调用方应使用渐变色兜底
    """
    from config import UNSPLASH_ACCESS_KEY

    keyword = _extract_keywords(title, category)
    cache_key = keyword[:40]

    if cache_key in _cache:
        return _cache[cache_key]

    result = (None, None)

    if UNSPLASH_ACCESS_KEY:
        try:
            unsplash_result = _unsplash_search(keyword)
            if unsplash_result:
                result = unsplash_result  # (url, attribution)
        except Exception as e:
            logger.warning(f"Unsplash 异常: {e}")

    if not result[0]:
        # 无 API Key 或 API 失败 → 用 Picsum
        picsum_url = _picsum_fallback(keyword)
        result = (picsum_url, None)
        logger.info(f"  [imager] Picsum: {keyword[:20]} → {picsum_url}")

    _cache[cache_key] = result
    return result


def batch_get_images(items: list) -> dict:
    """
    批量获取配图（并行请求，大幅提升速度）

    参数：
        items: list of dict, 每个 dict 须包含 'title' 和 'category'

    返回：
        dict: {item_key: (image_url, attribution)}
        item_key 是 items 中 dict 的 id（若无 id 则用索引）
    """
    if not items:
        return {}

    results = {}

    def _fetch_one(item):
        key = item.get("id", str(id(item)))
        title = item.get("title", "")
        category = item.get("category", "")
        img_url, attr = get_image_url(title, category)
        return key, (img_url, attr)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_fetch_one, item): item for item in items}
        for future in as_completed(futures):
            try:
                key, result = future.result()
                results[key] = result
            except Exception as e:
                logger.warning(f"批量获取图片异常: {e}")

    return results
