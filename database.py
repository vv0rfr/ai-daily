"""SQLite 数据库模块 — 记录运行历史和文章数据"""

import os
import sqlite3

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "ai_daily.db")


def _get_conn():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_conn()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TEXT NOT NULL,
                mode TEXT NOT NULL,
                total_items INTEGER,
                duration_seconds REAL,
                ai_model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER REFERENCES runs(id),
                title TEXT NOT NULL,
                title_en TEXT,
                link TEXT,
                summary TEXT,
                summary_en TEXT,
                source TEXT,
                category TEXT,
                lang TEXT,
                content_type TEXT DEFAULT 'article',
                pub_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
            CREATE INDEX IF NOT EXISTS idx_articles_run_id ON articles(run_id);
        """)
        conn.commit()
        cols = {row[1] for row in conn.execute("PRAGMA table_info(articles)").fetchall()}
        if "title_en" not in cols:
            conn.execute("ALTER TABLE articles ADD COLUMN title_en TEXT")
        if "summary_en" not in cols:
            conn.execute("ALTER TABLE articles ADD COLUMN summary_en TEXT")
        conn.commit()
    except Exception as e:
        print(f"  [db] init_db 失败: {e}")
    finally:
        conn.close()


def create_run(run_date: str, mode: str) -> int | None:
    conn = _get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO runs (run_date, mode) VALUES (?, ?)",
            (run_date, mode),
        )
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        print(f"  [db] create_run 失败: {e}")
        return None
    finally:
        conn.close()


def insert_articles(run_id: int, articles: list[dict]):
    if not run_id or not articles:
        return
    conn = _get_conn()
    try:
        rows = []
        for a in articles:
            rows.append((
                run_id,
                a.get("title", ""),
                a.get("title_en", ""),
                a.get("link", ""),
                a.get("summary", ""),
                a.get("summary_en", ""),
                a.get("source", a.get("author", "")),
                a.get("category", ""),
                a.get("lang", ""),
                a.get("type", "article"),
                a.get("pub_date").isoformat() if a.get("pub_date") else None,
            ))
        conn.executemany(
            "INSERT INTO articles (run_id, title, title_en, link, summary, summary_en, source, category, lang, content_type, pub_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
        print(f"  [db] 写入 {len(rows)} 条文章")
    except Exception as e:
        print(f"  [db] insert_articles 失败: {e}")
    finally:
        conn.close()


def update_run(run_id: int, total_items: int, duration: float, ai_model: str):
    if not run_id:
        return
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE runs SET total_items=?, duration_seconds=?, ai_model=? WHERE id=?",
            (total_items, duration, ai_model, run_id),
        )
        conn.commit()
    except Exception as e:
        print(f"  [db] update_run 失败: {e}")
    finally:
        conn.close()


def get_yesterday_articles(mode: str = "ai") -> dict:
    """获取昨天的文章数据，返回 {count, categories, titles}"""
    from datetime import datetime, timedelta
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    result = {"count": 0, "categories": {}, "titles": []}
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT id FROM runs WHERE run_date=? AND mode=? ORDER BY id DESC LIMIT 1",
            (yesterday, mode),
        ).fetchone()
        if not row:
            return result
        run_id = row["id"]
        rows = conn.execute(
            "SELECT title, category FROM articles WHERE run_id=?", (run_id,)
        ).fetchall()
        result["count"] = len(rows)
        for r in rows:
            result["titles"].append(r["title"])
            cat = r["category"] or "其他"
            result["categories"][cat] = result["categories"].get(cat, 0) + 1
    except Exception as e:
        print(f"  [db] get_yesterday_articles 失败: {e}")
    finally:
        conn.close()
    return result


def get_stats() -> dict:
    stats = {
        "total_runs": 0,
        "total_articles": 0,
        "source_ranking": [],
        "category_dist": [],
    }
    conn = _get_conn()
    try:
        row = conn.execute("SELECT COUNT(*) as cnt FROM runs").fetchone()
        stats["total_runs"] = row["cnt"]
        row = conn.execute("SELECT COUNT(*) as cnt FROM articles").fetchone()
        stats["total_articles"] = row["cnt"]
        rows = conn.execute(
            "SELECT source, COUNT(*) as cnt FROM articles "
            "WHERE source != '' GROUP BY source ORDER BY cnt DESC LIMIT 15"
        ).fetchall()
        stats["source_ranking"] = [(r["source"], r["cnt"]) for r in rows]
        rows = conn.execute(
            "SELECT category, COUNT(*) as cnt FROM articles "
            "WHERE category != '' GROUP BY category ORDER BY cnt DESC"
        ).fetchall()
        stats["category_dist"] = [(r["category"], r["cnt"]) for r in rows]
    except Exception as e:
        print(f"  [db] get_stats 失败: {e}")
    finally:
        conn.close()
    return stats
