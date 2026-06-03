"""扫描 output/ 目录，生成 index.html（GitHub Pages 首页）"""
import os
import re
from datetime import datetime

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output')
INDEX_PATH = os.path.join(OUTPUT_DIR, 'index.html')

MODE_LABELS = {
    'ai': ('AI', '#2563EB'),
    'tech': ('科技', '#0D9488'),
    'all': ('综合', '#D4763A'),
}

def parse_filename(name):
    """从文件名解析日期和模式，返回 (日期, 模式, 显示日期)"""
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})-([a-z]+)\.html$', name)
    if not m:
        return None
    y, mo, d, mode = m.groups()
    try:
        dt = datetime(int(y), int(mo), int(d))
    except ValueError:
        return None
    weekday_map = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    weekday = weekday_map[dt.weekday()]
    return (dt, mode, f'{y}-{mo}-{d} {weekday}', f'{y}年{mo}月{d}日')

def build_html(entries):
    mode_labels = MODE_LABELS
    cards = []
    for dt, mode, short_date, full_date in entries:
        label, color = mode_labels.get(mode, (mode.upper(), '#6B7280'))
        filename = dt.strftime('%Y-%m-%d-%a')  # not used
        fname = f"{dt.strftime('%Y-%m-%d')}-{mode}.html"
        cards.append(f'''    <a href="{fname}" class="card" data-date="{dt.strftime('%Y-%m-%d')}">
      <div class="card-top">
        <span class="date">{short_date}</span>
        <span class="mode-tag" style="--tag-color: {color}">{label}</span>
      </div>
      <div class="card-title">{full_date} · {label}日报</div>
    </a>''')

    cards_html = '\n'.join(cards)

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI 日报归档</title>
<style>
  :root {{
    --bg-page: #f5f5f7;
    --bg-card: #fff;
    --bg-card-hover: #fafafa;
    --text-primary: #1d1d1f;
    --text-secondary: #86868b;
    --text-tertiary: #aeaeb2;
    --bdr-card: #e5e5e7;
    --shadow: 0 1px 3px rgba(0,0,0,0.04);
    --shadow-hover: 0 4px 12px rgba(0,0,0,0.1);
    --accent: #2563EB;
  }}
  .dark-mode {{
    --bg-page: #0f172a;
    --bg-card: #1e293b;
    --bg-card-hover: #263348;
    --text-primary: #e2e8f0;
    --text-secondary: #94a3b8;
    --text-tertiary: #64748b;
    --bdr-card: #334155;
    --shadow: 0 1px 3px rgba(0,0,0,0.3);
    --shadow-hover: 0 4px 12px rgba(0,0,0,0.5);
    --accent: #60a5fa;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
    background: var(--bg-page);
    color: var(--text-primary);
    max-width: 700px;
    margin: 0 auto;
    padding: 48px 20px 80px;
    transition: background 0.2s, color 0.2s;
  }}
  .header {{
    margin-bottom: 36px;
  }}
  .header h1 {{
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.3px;
  }}
  .header p {{
    color: var(--text-secondary);
    font-size: 15px;
    margin-top: 6px;
  }}
  .theme-toggle {{
    position: fixed;
    top: 16px;
    right: 20px;
    background: var(--bg-card);
    border: 1px solid var(--bdr-card);
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 14px;
    cursor: pointer;
    color: var(--text-secondary);
    box-shadow: var(--shadow);
    transition: all 0.15s;
  }}
  .theme-toggle:hover {{
    box-shadow: var(--shadow-hover);
    color: var(--text-primary);
  }}
  .cards {{
    display: flex;
    flex-direction: column;
    gap: 12px;
  }}
  .card {{
    display: block;
    background: var(--bg-card);
    border: 1px solid var(--bdr-card);
    border-radius: 12px;
    padding: 18px 20px;
    text-decoration: none;
    color: inherit;
    transition: all 0.15s;
    box-shadow: var(--shadow);
  }}
  .card:hover {{
    background: var(--bg-card-hover);
    box-shadow: var(--shadow-hover);
    transform: translateY(-1px);
    border-color: var(--accent);
  }}
  .card-top {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
  }}
  .date {{
    font-size: 13px;
    color: var(--text-tertiary);
    font-weight: 500;
  }}
  .mode-tag {{
    font-size: 11px;
    font-weight: 600;
    color: var(--tag-color, #6B7280);
    background: color-mix(in srgb, var(--tag-color, #6B7280) 12%, transparent);
    padding: 2px 10px;
    border-radius: 100px;
  }}
  .card-title {{
    font-size: 16px;
    font-weight: 600;
  }}
  .footer {{
    margin-top: 48px;
    text-align: center;
    font-size: 13px;
    color: var(--text-tertiary);
  }}
  .footer a {{ color: var(--accent); text-decoration: none; }}
</style>
</head>
<body>
  <button class="theme-toggle" onclick="toggleTheme()">🌓 切换主题</button>
  <div class="header">
    <h1>📡 AI 日报归档</h1>
    <p>每日 AI 资讯精选 · 共 {len(entries)} 期</p>
  </div>
  <div class="cards">
{cards_html}
  </div>
  <div class="footer">
    由 <a href="https://github.com/vv0rfr/ai-daily">AI 日报生成器</a> 自动生成
  </div>
  <script>
  const stored = localStorage.getItem('theme');
  if (stored === 'dark' || (!stored && window.matchMedia('(prefers-color-scheme: dark)').matches)) {{
    document.body.classList.add('dark-mode');
  }}
  function toggleTheme() {{
    document.body.classList.toggle('dark-mode');
    localStorage.setItem('theme', document.body.classList.contains('dark-mode') ? 'dark' : 'light');
  }}
  </script>
</body>
</html>'''

def main():
    files = []
    for f in os.listdir(OUTPUT_DIR):
        if not f.endswith('.html') or f == 'index.html':
            continue
        parsed = parse_filename(f)
        if parsed:
            files.append(parsed)
    files.sort(key=lambda x: x[0], reverse=True)

    html = build_html(files)
    with open(INDEX_PATH, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'OK: index.html generated, {len(files)} reports total')

if __name__ == '__main__':
    main()
