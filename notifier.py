"""通知模块 — 支持 Server酱微信推送"""

import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

import requests
from datetime import datetime


# Server酱推送地址
SERVERCHAN_URL = "https://sctapi.ftqq.com/{key}.send"


def get_serverchan_key() -> str:
    """获取 Server酱 Key"""
    return os.getenv("SERVERCHAN_KEY", "")


def send_serverchan(title: str, content: str = "") -> bool:
    """通过 Server酱发送微信通知"""
    key = get_serverchan_key()
    if not key:
        print("  [notifier] 未配置 SERVERCHAN_KEY，跳过通知")
        return False

    try:
        url = SERVERCHAN_URL.format(key=key)
        data = {
            "title": title[:100],  # 标题限制 100 字符
            "desp": content,
        }
        resp = requests.post(url, data=data, timeout=10)
        result = resp.json()

        if result.get("code") == 0:
            print(f"  [notifier] 通知发送成功")
            return True
        else:
            print(f"  [notifier] 通知发送失败: {result}")
            return False

    except Exception as e:
        print(f"  [notifier] 通知发送异常: {e}")
        return False


def notify_daily_report(mode: str, stats: dict = None):
    """发送日报生成通知"""
    today = datetime.now().strftime("%Y-%m-%d")

    # 构建标题
    mode_labels = {
        "ai": "AI 垂直日报",
        "tech": "科技综合日报",
        "all": "全频道日报",
    }
    label = mode_labels.get(mode, mode)
    title = f"📰 {label}已生成 ({today})"

    # 构建内容
    content_parts = [f"## {label} · {today}\n"]

    if stats:
        if "total" in stats:
            content_parts.append(f"- 共筛选 **{stats['total']}** 条内容")
        if "categories" in stats:
            for cat, count in stats["categories"].items():
                content_parts.append(f"- {cat}: {count} 条")
        if "duration" in stats:
            content_parts.append(f"- 耗时: {stats['duration']:.1f} 秒")

    content_parts.append(f"\n[查看日报](https://github.com/{os.getenv('GITHUB_REPOSITORY', '')}/tree/main/output)")

    content = "\n".join(content_parts)

    return send_serverchan(title, content)


def notify_error(error_msg: str):
    """发送错误通知"""
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = f"❌ AI 日报生成失败 ({today})"
    content = f"## 错误信息\n\n```\n{error_msg}\n```"

    return send_serverchan(title, content)


def notify_stats(mode: str, groups: dict, duration: float):
    """发送统计通知（带详细数据）"""
    stats = {
        "total": sum(len(v) for v in groups.values()),
        "categories": {k: len(v) for k, v in groups.items()},
        "duration": duration,
    }
    return notify_daily_report(mode, stats)


if __name__ == "__main__":
    # 测试通知
    print("测试 Server酱通知...")
    result = send_serverchan("测试通知", "这是一条测试消息\n\n**加粗** 和 [链接](https://example.com)")
    print(f"结果: {'成功' if result else '失败'}")
