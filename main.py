"""AI 日报生成器 — 支持 AI 垂直 / 科技综合两种频道"""

import os
import sys
import time
import argparse
from datetime import datetime

from config import OUTPUT_DIR, TOP_N, VIDEO_TOP_N
from fetcher import fetch_ai, fetch_tech, fetch_all, fetch_bilibili_videos
from filter import filter_and_group
from writer import generate_article, generate_redirect_html


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

    # 1. 抓取数据
    print("[1/4] 抓取数据...")
    items = fetcher()
    if not items:
        print("  没有抓取到数据，退出")
        sys.exit(1)
    print(f"  共抓取 {len(items)} 条\n")

    # 1.5 抓取 B站视频
    videos = fetch_bilibili_videos()
    items.extend(videos)
    print(f"  文章+视频合计：{len(items)} 条\n")

    # 2. 筛选分组
    print("[2/4] 筛选排序...")
    groups = filter_and_group(items, top_n=TOP_N, mode=filter_mode, video_top_n=VIDEO_TOP_N)
    print()

    # 3. 生成文章
    print("[3/4] 生成文章...")
    article = generate_article(groups)

    # 4. 保存 Markdown
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    md_path = os.path.join(OUTPUT_DIR, f"{today}-{mode}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(article)

    # 5. 生成多语言跳转 HTML 页面
    html_content = generate_redirect_html(groups, today, label=label)
    html_path = os.path.join(OUTPUT_DIR, f"{today}-{mode}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    duration = time.time() - start_time
    total = sum(len(v) for v in groups.values())

    print(f"\n{'='*50}")
    print(f"  Markdown：{md_path}")
    print(f"  HTML：    {html_path}")
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


def main():
    parser = argparse.ArgumentParser(description="AI 日报生成器")
    parser.add_argument(
        "mode",
        nargs="?",
        default="ai",
        choices=["ai", "tech", "all"],
        help="运行模式：ai=AI垂直 | tech=科技综合 | all=全部（默认 ai）",
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
    run(args.mode, publish=args.publish, notify=not args.no_notify)


if __name__ == "__main__":
    main()
