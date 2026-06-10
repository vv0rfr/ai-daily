"""AI 日报生成器 — 支持 AI 垂直 / 科技综合两种频道"""

import os
import sys
import time
import glob
import argparse
from datetime import datetime

from config import OUTPUT_DIR, TOP_N, VIDEO_TOP_N
from fetcher import fetch_ai, fetch_tech, fetch_all, fetch_bilibili_videos, check_sources
from filter import filter_and_group
from writer import generate_article, generate_redirect_html, generate_feed, generate_index
from database import init_db, create_run, insert_articles, update_run, get_stats


MODES = {
    "ai": ("AI 垂直日报", fetch_ai, "ai"),
    "tech": ("科技综合日报", fetch_tech, "tech"),
    "all": ("全频道日报", fetch_all, "tech"),
}


def run(mode: str, publish: bool = False, notify: bool = True):
    start_time = time.time()
    today = datetime.now().strftime("%Y-%m-%d")
    label, fetcher, filter_mode = MODES[mode]

    print(f"\n{'='*50}")
    print(f"  {label} · {today}")
    print(f"{'='*50}\n")

    # 0. 初始化数据库
    init_db()
    run_id = create_run(today, mode)

    # 1. 抓取数据
    print("[1/4] 抓取数据...")
    items = fetcher()
    print(f"  共抓取 {len(items)} 条\n")

    # 1.5 抓取 B站视频
    videos = fetch_bilibili_videos()
    items.extend(videos)
    print(f"  文章+视频合计：{len(items)} 条\n")

    if not items:
        print("[main] 警告：本次抓取无任何内容，跳过生成")
        return None, None

    # 2. 筛选分组
    print("[2/4] 筛选排序...")
    groups, classify_method = filter_and_group(items, top_n=TOP_N, mode=filter_mode, video_top_n=VIDEO_TOP_N)
    print()

    if not groups or all(len(v) == 0 for v in groups.values()):
        print("[main] 警告：筛选后无内容，请检查 filter 配置")
        return None, None

    # 写入数据库
    all_articles = [it for cat_items in groups.values() for it in cat_items]
    insert_articles(run_id, all_articles)

    # 3. 生成文章
    print("[3/4] 生成文章...")
    article, model_used = generate_article(groups)

    # 4. 保存 Markdown
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 删除同一天同一模式的旧文件
    for old_file in glob.glob(os.path.join(OUTPUT_DIR, f"{today}-{mode}.*")):
        os.remove(old_file)
        print(f"  删除旧文件：{os.path.basename(old_file)}")

    md_path = os.path.join(OUTPUT_DIR, f"{today}-{mode}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(article)

    # 5. 生成多语言跳转 HTML 页面
    html_content = generate_redirect_html(groups, today, label=label, article_text=article)
    html_path = os.path.join(OUTPUT_DIR, f"{today}-{mode}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # 5.5 生成 RSS feed
    feed_content = generate_feed(groups, today, label=label)
    feed_path = os.path.join(OUTPUT_DIR, "feed.xml")
    with open(feed_path, "w", encoding="utf-8") as f:
        f.write(feed_content)

    # 5.6 生成历史列表页
    generate_index(OUTPUT_DIR)

    duration = time.time() - start_time
    total = sum(len(v) for v in groups.values())

    # 更新运行记录
    ai_model = f"{model_used}+llm_classify" if classify_method == "llm" else model_used
    update_run(run_id, total, duration, ai_model)

    print(f"\n{'='*50}")
    print(f"  Markdown：{md_path}")
    print(f"  HTML：    {html_path}")
    print(f"  Feed：    {feed_path}")
    print(f"  字数：{len(article)} 字符")
    print(f"  耗时：{duration:.1f} 秒")
    print(f"{'='*50}\n")

    # 6. 发送通知
    if notify:
        try:
            from notifier import notify_stats
            notify_stats(mode, groups, duration)
        except Exception as e:
            print(f"  [通知] 发送失败: {e}")

    # 7. 发布到公众号
    if publish:
        try:
            from publisher import publish_article
            result = publish_article(md_path, mode)
            if result["success"]:
                print(f"  [发布] 公众号发布成功！")
            else:
                print(f"  [发布] 公众号发布失败: {result.get('error')}")
        except Exception as e:
            print(f"  [发布] 公众号发布异常: {e}")

    return md_path, html_path


def show_stats():
    """打印数据库统计数据"""
    stats = get_stats()
    print(f"\n{'='*50}")
    print(f"  AI 日报 · 数据统计")
    print(f"{'='*50}\n")
    print(f"  总运行次数：{stats['total_runs']}")
    print(f"  总文章数：  {stats['total_articles']}\n")

    if stats["source_ranking"]:
        print("  [来源排名 Top 15]")
        print(f"  {'来源':<25} {'数量':>5}")
        print(f"  {'-'*32}")
        for source, cnt in stats["source_ranking"]:
            print(f"  {source:<25} {cnt:>5}")

    if stats["category_dist"]:
        print(f"\n  [分类分布]")
        print(f"  {'分类':<15} {'数量':>5}")
        print(f"  {'-'*22}")
        for cat, cnt in stats["category_dist"]:
            print(f"  {cat:<15} {cnt:>5}")

    print(f"\n{'='*50}\n")


def main():
    parser = argparse.ArgumentParser(description="AI 日报生成器")
    parser.add_argument(
        "mode",
        nargs="?",
        default="ai",
        choices=["ai", "tech", "all", "stats", "check-sources"],
        help="运行模式：ai=AI垂直 | tech=科技综合 | all=全部 | stats=统计数据 | check-sources=诊断RSS源（默认 ai）",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="发布到微信公众号",
    )
    parser.add_argument(
        "--no-notify",
        action="store_true",
        help="不发送通知",
    )
    args = parser.parse_args()

    if args.mode == "stats":
        show_stats()
        return

    if args.mode == "check-sources":
        check_sources()
        return

    run(args.mode, publish=args.publish, notify=not args.no_notify)


if __name__ == "__main__":
    main()
