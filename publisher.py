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
    """将 Markdown 转换为公众号兼容的 HTML（优化移动端排版）"""
    lines = md_content.split("\n")
    html_parts = []
    in_list = False
    links = []  # 收集原文链接

    for line in lines:
        raw = line
        line = line.strip()

        # 跳过空行
        if not line:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append('<p style="margin:12px 0;"><br/></p>')
            continue

        # 分类标题 ##
        if line.startswith("## "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            text = line[3:]
            emoji_map = {"行业": "🏭", "产品": "🛠️", "论文": "📄", "模型": "🧠", "视频": "🎬", "产业": "🏭"}
            emoji = ""
            for k, v in emoji_map.items():
                if k in text:
                    emoji = v
                    break
            html_parts.append(
                f'<section style="margin:28px 0 14px;padding:8px 16px;background:#f0f7ff;'
                f'border-radius:6px;border-left:4px solid #0071e3;">'
                f'<span style="font-size:17px;font-weight:bold;color:#1a1a1a;">{emoji} {text}</span>'
                f'</section>'
            )
        # 文章标题 #
        elif line.startswith("# "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            text = line[2:]
            html_parts.append(
                f'<h1 style="font-size:20px;font-weight:bold;color:#1a1a1a;'
                f'text-align:center;margin:8px 0 4px;letter-spacing:1px;">{text}</h1>'
            )
        # 引用（区分来源、链接和普通引用）
        elif line.startswith("> "):
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            text = line[2:]
            # 来源/UP主行 → 灰色小字
            if text.startswith("来源：") or text.startswith("UP主"):
                text = _parse_inline(text, links)
                html_parts.append(
                    f'<p style="margin:2px 0;font-size:13px;color:#999;line-height:1.5;">{text}</p>'
                )
            # [🔗 阅读原文] / [🔗 观看视频] → 蓝色链接文字
            elif "🔗" in text:
                text = _parse_inline(text, links)
                html_parts.append(
                    f'<p style="margin:2px 0 12px;font-size:13px;color:#0071e3;line-height:1.5;">{text}</p>'
                )
            # 普通引用
            else:
                html_parts.append(
                    f'<blockquote style="border-left:3px solid #0071e3;padding:10px 14px;'
                    f'margin:14px 0;color:#555;background:#f8f9fa;border-radius:4px;'
                    f'font-size:14px;">{text}</blockquote>'
                )
        # 分割线
        elif line == "---":
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            html_parts.append('<hr style="border:none;border-top:1px solid #e8e8e8;margin:20px 0;"/>')
        # 列表项
        elif line.startswith("- ") or line.startswith("* "):
            if not in_list:
                html_parts.append('<ul style="margin:8px 0 14px;padding-left:18px;">')
                in_list = True
            text = line[2:]
            text = _parse_inline(text, links)
            html_parts.append(f'<li style="margin:6px 0;font-size:15px;line-height:1.6;color:#333;">{text}</li>')
        elif re.match(r"^\d+\.\s", line):
            if not in_list:
                html_parts.append('<ul style="margin:8px 0 14px;padding-left:18px;">')
                in_list = True
            text = re.sub(r"^\d+\.\s", "", line)
            text = _parse_inline(text, links)
            html_parts.append(f'<li style="margin:6px 0;font-size:15px;line-height:1.6;color:#333;">{text}</li>')
        # 普通段落
        else:
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            text = _parse_inline(line, links)
            html_parts.append(
                f'<p style="margin:10px 0;font-size:15px;line-height:1.75;color:#333;">{text}</p>'
            )

    if in_list:
        html_parts.append("</ul>")

    return "\n".join(html_parts)


def _parse_inline(text: str, links: list = None) -> str:
    """解析行内格式（加粗、代码），链接转为纯文本收集"""
    # 链接：提取并转为纯文本，同时收集到 links 列表
    def replace_link(m):
        t, u = m.group(1), m.group(2)
        if links is not None:
            links.append((t, u))
        # 微信不支持外链，显示为带🔗的纯文本
        return f'<span style="color:#0071e3;">🔗 {t}</span>'

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace_link, text)

    # 加粗
    text = re.sub(
        r"\*\*([^*]+)\*\*",
        r'<strong style="font-weight:bold;color:#1a1a1a;">\1</strong>',
        text
    )
    # 行内代码
    text = re.sub(
        r"`([^`]+)`",
        r'<code style="background:#f0f0f0;padding:2px 5px;border-radius:3px;font-size:13px;color:#d63384;">\1</code>',
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


def create_draft(access_token: str, title: str, content: str, thumb_media_id: str = "",
                  content_source_url: str = "") -> str:
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
    if content_source_url:
        article["content_source_url"] = content_source_url
    body = {"articles": [article]}

    # 手动序列化，确保中文不转义为 \uXXXX
    json_data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    resp = requests.post(
        DRAFT_URL,
        params={"access_token": access_token},
        data=json_data,
        headers={"Content-Type": "application/json; charset=utf-8"},
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

        # GitHub HTML 页面作为"阅读原文"链接
        repo_url = "https://vv0rfr.github.io/ai-daily"
        source_url = f"{repo_url}/output/{today}-{mode}.html"
        if mode == "ai":
            repo_display = "AI 频道"
        elif mode == "tech":
            repo_display = "科技频道"
        else:
            repo_display = "全频道"

        # 包装为完整 HTML（微信文章标准样式）
        full_html = f"""
<section style="max-width:640px;margin:0 auto;padding:10px 16px 20px;font-family:-apple-system,BlinkMacSystemFont,'Helvetica Neue',sans-serif;">

<div style="text-align:center;padding:20px 0 8px;">
  <span style="display:inline-block;background:#0071e3;color:#fff;font-size:12px;padding:3px 12px;border-radius:12px;letter-spacing:2px;">{repo_display}</span>
</div>

{html_content}

<hr style="border:none;border-top:1px solid #e8e8e8;margin:24px 0 12px;"/>

<section style="background:#f8f9fa;border-radius:8px;padding:14px 16px;margin:16px 0;">
  <p style="margin:0 0 6px;font-size:13px;color:#666;line-height:1.6;">
    📬 本文由 AI 自动整理 · 每日 8:00 更新<br>
    💡 点击下方「阅读原文」查看带跳转链接的网页版
  </p>
</section>

</section>
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
        draft_id = create_draft(token, title, full_html, thumb_id, source_url)
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
