"""微信公众号自动发布模块"""

import os
import re
import json
import time
import requests
from datetime import datetime
from config import WECHAT_APP_ID, WECHAT_APP_SECRET, OUTPUT_DIR


# 公众号 API 地址
TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
UPLOAD_URL = "https://api.weixin.qq.com/cgi-bin/material/add_material"
DRAFT_URL = "https://api.weixin.qq.com/cgi-bin/draft/add"
PUBLISH_URL = "https://api.weixin.qq.com/cgi-bin/freepublish/submit"


def get_access_token() -> str:
    """获取公众号 access_token"""
    if not WECHAT_APP_ID or not WECHAT_APP_SECRET:
        raise ValueError("未配置 WECHAT_APP_ID 或 WECHAT_APP_SECRET")

    params = {
        "grant_type": "client_credential",
        "appid": WECHAT_APP_ID,
        "secret": WECHAT_APP_SECRET,
    }
    resp = requests.get(TOKEN_URL, params=params, timeout=10)
    data = resp.json()

    if "access_token" not in data:
        raise ValueError(f"获取 access_token 失败: {data}")

    return data["access_token"]


def md_to_html(md_content: str) -> str:
    """将 Markdown 转换为公众号兼容的 HTML"""
    lines = md_content.split("\n")
    html_parts = []
    in_list = False

    for line in lines:
        line = line.strip()

        # 跳过空行
        if not line:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append("<p><br/></p>")
            continue

        # 标题
        if line.startswith("# "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            text = line[2:]
            html_parts.append(f'<h1 style="font-size:22px;font-weight:bold;color:#333;margin:20px 0 10px;">{text}</h1>')
        elif line.startswith("## "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            text = line[3:]
            html_parts.append(f'<h2 style="font-size:18px;font-weight:bold;color:#333;margin:16px 0 8px;border-bottom:1px solid #eee;padding-bottom:4px;">{text}</h2>')
        elif line.startswith("### "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            text = line[4:]
            html_parts.append(f'<h3 style="font-size:16px;font-weight:bold;color:#333;margin:12px 0 6px;">{text}</h3>')
        # 引用
        elif line.startswith("> "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            text = line[2:]
            html_parts.append(f'<blockquote style="border-left:3px solid #0071e3;padding:8px 12px;margin:8px 0;color:#666;background:#f8f9fa;">{text}</blockquote>')
        # 分割线
        elif line == "---":
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append('<hr style="border:none;border-top:1px solid #eee;margin:16px 0;"/>')
        # 无序列表
        elif line.startswith("- ") or line.startswith("* "):
            if not in_list:
                html_parts.append('<ul style="margin:8px 0;padding-left:20px;">')
                in_list = True
            text = line[2:]
            text = _parse_inline(text)
            html_parts.append(f'<li style="margin:4px 0;">{text}</li>')
        # 有序列表
        elif re.match(r"^\d+\.\s", line):
            if not in_list:
                html_parts.append('<ul style="margin:8px 0;padding-left:20px;">')
                in_list = True
            text = re.sub(r"^\d+\.\s", "", line)
            text = _parse_inline(text)
            html_parts.append(f'<li style="margin:4px 0;">{text}</li>')
        # 普通段落
        else:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            text = _parse_inline(line)
            html_parts.append(f'<p style="margin:8px 0;line-height:1.8;">{text}</p>')

    if in_list:
        html_parts.append("</ul>")

    return "\n".join(html_parts)


def _parse_inline(text: str) -> str:
    """解析行内格式（加粗、链接）"""
    # 链接
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2" style="color:#0071e3;text-decoration:none;">\1</a>',
        text
    )
    # 加粗
    text = re.sub(
        r"\*\*([^*]+)\*\*",
        r'<strong style="font-weight:bold;">\1</strong>',
        text
    )
    # 行内代码
    text = re.sub(
        r"`([^`]+)`",
        r'<code style="background:#f5f5f7;padding:2px 4px;border-radius:3px;font-size:0.9em;">\1</code>',
        text
    )
    return text


def upload_thumb(access_token: str, image_path: str) -> str:
    """上传封面图，返回 media_id"""
    if not os.path.exists(image_path):
        # 使用默认封面
        return ""

    with open(image_path, "rb") as f:
        resp = requests.post(
            UPLOAD_URL,
            params={"access_token": access_token, "type": "image"},
            files={"media": f},
            timeout=30,
        )

    data = resp.json()
    if "media_id" not in data:
        print(f"  [publisher] 上传封面失败: {data}")
        return ""

    return data["media_id"]


def create_draft(access_token: str, title: str, content: str, thumb_media_id: str = "") -> str:
    """创建草稿，返回 media_id"""
    article = {
        "title": title,
        "author": "AI 日报",
        "content": content,
        "need_open_comment": 1,
        "only_fans_can_comment": 0,
    }
    if thumb_media_id:
        article["thumb_media_id"] = thumb_media_id
    articles = [article]

    resp = requests.post(
        DRAFT_URL,
        params={"access_token": access_token},
        json={"articles": articles},
        timeout=30,
    )

    data = resp.json()
    if "media_id" not in data:
        raise ValueError(f"创建草稿失败: {data}")

    return data["media_id"]


def publish_draft(access_token: str, media_id: str) -> str:
    """发布草稿，返回 publish_id"""
    resp = requests.post(
        PUBLISH_URL,
        params={"access_token": access_token},
        json={"media_id": media_id},
        timeout=30,
    )

    data = resp.json()
    if "publish_id" not in data:
        raise ValueError(f"发布失败: {data}")

    return data["publish_id"]


def publish_article(md_path: str, mode: str = "ai") -> dict:
    """完整的发布流程：读取 MD → 转 HTML → 创建草稿 → 发布"""
    result = {
        "success": False,
        "mode": mode,
        "file": md_path,
        "error": None,
    }

    try:
        # 读取 Markdown
        with open(md_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        # 提取标题
        today = datetime.now().strftime("%Y-%m-%d")
        title = f"AI 日报 · {today}"
        if mode == "tech":
            title = f"科技日报 · {today}"
        elif mode == "all":
            title = f"全频道日报 · {today}"

        # 转换为公众号 HTML
        html_content = md_to_html(md_content)
        # 包装为完整 HTML
        full_html = f"""
<div style="max-width:600px;margin:0 auto;padding:16px;">
{html_content}
<hr style="border:none;border-top:1px solid #eee;margin:16px 0;"/>
<p style="text-align:center;color:#999;font-size:12px;">本文由 AI 自动整理 · 内容仅供参考</p>
</div>
"""

        # 获取 access_token
        print("  [publisher] 获取 access_token...")
        token = get_access_token()

        # 上传封面图（如果有）
        thumb_id = ""
        thumb_path = os.path.join(os.path.dirname(__file__), "templates", "thumb.jpg")
        if os.path.exists(thumb_path):
            print("  [publisher] 上传封面图...")
            thumb_id = upload_thumb(token, thumb_path)

        # 创建草稿
        print("  [publisher] 创建草稿...")
        draft_id = create_draft(token, title, full_html, thumb_id)
        result["draft_id"] = draft_id
        print(f"  [publisher] 草稿创建成功！可在公众号后台手动发布")

        # 尝试发布（个人订阅号可能无此权限）
        try:
            print("  [publisher] 尝试自动发布...")
            publish_id = publish_draft(token, draft_id)
            result["publish_id"] = publish_id
            result["success"] = True
            print(f"  [publisher] 自动发布成功！publish_id: {publish_id}")
        except ValueError as pub_e:
            err_msg = str(pub_e)
            if "48001" in err_msg:
                print("  [publisher] 个人订阅号无自动发布权限，草稿已存入草稿箱，请手动发布")
                result["success"] = True
                result["publish_notice"] = "已存入草稿箱，请手动发布"
            else:
                raise

    except Exception as e:
        result["error"] = str(e)
        print(f"  [publisher] 发布失败: {e}")

    return result


def publish_latest():
    """发布最新的日报（供 GitHub Actions 调用）"""
    today = datetime.now().strftime("%Y-%m-%d")

    # 查找今天的文件
    for mode in ["ai", "tech", "all"]:
        md_path = os.path.join(OUTPUT_DIR, f"{today}-{mode}.md")
        if os.path.exists(md_path):
            print(f"\n[publisher] 发布 {mode} 日报...")
            return publish_article(md_path, mode)

    # 如果今天没有，找最近的
    if os.path.exists(OUTPUT_DIR):
        files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".md")], reverse=True)
        if files:
            md_path = os.path.join(OUTPUT_DIR, files[0])
            mode = "ai" if "-ai" in files[0] else "tech"
            print(f"\n[publisher] 发布最新日报: {files[0]}")
            return publish_article(md_path, mode)

    print("[publisher] 没有找到可发布的日报文件")
    return {"success": False, "error": "没有找到日报文件"}


if __name__ == "__main__":
    # 测试用
    result = publish_latest()
    print(f"\n发布结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
