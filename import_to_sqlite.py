import json
import sqlite3
import os

DB_FILE = "movies.db"
JSON_FILE = "movies.json"
LINKS_FILE = "direct_links.txt"

def init_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            slug TEXT UNIQUE,
            year TEXT,
            rating TEXT,
            poster TEXT,
            duration TEXT,
            quality TEXT,
            player_url TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()

def import_movies(conn, movies):
    inserted = 0
    updated = 0
    for m in movies:
        existing = conn.execute("SELECT id FROM movies WHERE slug = ?", (m.get("slug",""),)).fetchone()
        if existing:
            conn.execute("""
                UPDATE movies SET title=?, year=?, rating=?, poster=?, duration=?, quality=?, player_url=?, updated_at=?
                WHERE slug=?
            """, (m.get("title"), m.get("year"), m.get("rating"), m.get("poster"),
                  m.get("duration"), m.get("quality"), m.get("player_url"), m.get("updated_at"),
                  m.get("slug")))
            updated += 1
        else:
            conn.execute("""
                INSERT INTO movies (title, slug, year, rating, poster, duration, quality, player_url, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (m.get("title"), m.get("slug"), m.get("year"), m.get("rating"),
                  m.get("poster"), m.get("duration"), m.get("quality"),
                  m.get("player_url"), m.get("updated_at")))
            inserted += 1
    conn.commit()
    return inserted, updated

def save_direct_links(conn):
    rows = conn.execute("SELECT title, player_url FROM movies WHERE player_url IS NOT NULL AND player_url != ''").fetchall()
    with open(LINKS_FILE, "w", encoding="utf-8") as f:
        for title, url in rows:
            f.write(f"{title} | {url}\n")
    return len(rows)

def main():
    if not os.path.exists(JSON_FILE):
        print(f"❌ {JSON_FILE} tidak ditemukan!")
        return

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    movies = data.get("movies", [])
    print(f"📂 Total film di JSON: {len(movies)}")

    conn = sqlite3.connect(DB_FILE)
    init_db(conn)

    inserted, updated = import_movies(conn, movies)
    total = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]

    # Simpan direct_links.txt dari semua data di DB
    links_count = save_direct_links(conn)

    conn.close()

    print(f"✅ Selesai! Inserted: {inserted} | Updated: {updated} | Total di DB: {total}")
    print(f"🔗 Direct links tersimpan: {links_count} link → {LINKS_FILE}")

if __name__ == "__main__":
    main()