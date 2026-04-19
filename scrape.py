import cloudscraper
from bs4 import BeautifulSoup
import json
import re
import time
from datetime import datetime

# Daftar domain cadangan (update sesuai kondisi terkini)
BASE_URLS = [
    "https://tv1.lk21official.love",
    "http://139.59.72.171",
    "https://bioskop2l.lk21.in.net",
    "https://lk21official.pro",
    "https://lk21official.my",
]

PLAYER_DOMAIN = "https://playeriframe.sbs/iframe/p2p/"
PLAYER_PARAMS = ["?player=3", "?player=2", "?player=1"]   # prioritas player=3 dulu

def get_player_url(scraper, detail_url):
    """Coba ambil player ID dari playeriframe.sbs, kalau gagal fallback ke ?player=3"""
    for attempt in range(3):
        try:
            res = scraper.get(detail_url, timeout=20)
            if res.status_code != 200:
                continue

            soup = BeautifulSoup(res.text, "html.parser")

            # Cara 1: Cari iframe playeriframe.sbs
            iframes = soup.find_all("iframe")
            for iframe in iframes:
                src = iframe.get("src", "") or iframe.get("data-src", "")
                if "playeriframe.sbs" in src:
                    match = re.search(r"/iframe/p2p/([^/?&\"']+)", src)
                    if match:
                        player_id = match.group(1)
                        print(f"✅ player_id ditemukan: {player_id[:15]}...")
                        return PLAYER_DOMAIN + player_id

            # Cara 2: Cari di script tag
            scripts = soup.find_all("script")
            for script in scripts:
                text = script.string or ""
                match = re.search(r"playeriframe\.sbs/iframe/p2p/([^/?&\"'\\s]+)", text)
                if match:
                    player_id = match.group(1)
                    print(f"✅ player_id dari script: {player_id[:15]}...")
                    return PLAYER_DOMAIN + player_id

        except Exception as e:
            print(f"   Attempt {attempt+1} gagal: {e}")
            time.sleep(2)

    # Fallback ke ?player=3 (paling sering berhasil di mirror)
    print(f"   ⚠️ Tidak menemukan player_id → fallback ke {PLAYER_PARAMS[0]}")
    return detail_url.rstrip("/") + PLAYER_PARAMS[0]


def scrape_films():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Mulai scrape LK21...")

    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False},
        delay=10
    )

    for base_url in BASE_URLS:
        try:
            print(f"→ Mencoba domain: {base_url}")
            res = scraper.get(base_url, timeout=25)

            if res.status_code != 200:
                print(f"   Status: {res.status_code} → skip")
                continue

            print(f"✅ Berhasil terkoneksi ke {base_url}")
            soup = BeautifulSoup(res.text, "html.parser")

            # Selector utama (bisa berubah tergantung tema)
            films = soup.select("a[itemprop='url'], article.item a, .gmr-box-content a")

            unique_films = []
            seen = set()

            for film in films:
                href = film.get("href", "").strip()
                if not href or href == "#" or "/category/" in href or "/year/" in href:
                    continue

                slug = href.strip("/").split("/")[-1]
                if not slug or slug in seen:
                    continue
                seen.add(slug)

                title_tag = film.select_one("h3.poster-title, h2, .entry-title")
                title = title_tag.text.strip() if title_tag else "Unknown Title"

                year = film.select_one("span.year")
                year = year.text.strip() if year else ""

                rating = film.select_one("span[itemprop='ratingValue']")
                rating = rating.text.strip() if rating else ""

                poster = film.select_one("img[itemprop='image'], img")
                poster = poster.get("src", "") if poster else ""

                # Buat detail URL
                detail_url = href if href.startswith("http") else base_url.rstrip("/") + "/" + slug

                unique_films.append({
                    "title": title,
                    "slug": slug,
                    "year": year,
                    "rating": rating,
                    "poster": poster,
                    "detail_url": detail_url,
                })

            if not unique_films:
                print("   Tidak menemukan film di domain ini, coba domain lain...")
                continue

            print(f"Ditemukan {len(unique_films)} film unik. Mengambil player...")

            # Step 2: Ambil player untuk tiap film
            movie_list = []
            for i, film in enumerate(unique_films, 1):
                print(f" [{i}/{len(unique_films)}] {film['title'][:70]}...", end=" ", flush=True)
                
                player_url = get_player_url(scraper, film["detail_url"])
                
                movie_list.append({
                    "title": film["title"],
                    "slug": film["slug"],
                    "year": film["year"],
                    "rating": film["rating"],
                    "poster": film["poster"],
                    "player_url": player_url,
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                time.sleep(1.5)   # anti rate limit

            # Simpan hasil
            with open("movies.json", "w", encoding="utf-8") as f:
                json.dump({
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "base_url_used": base_url,
                    "total": len(movie_list),
                    "movies": movie_list
                }, f, ensure_ascii=False, indent=2)

            with open("direct_links.txt", "w", encoding="utf-8") as f:
                f.write(f"DAFTAR FILM LANGSUNG (Auto Update)\n")
                f.write(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Domain: {base_url}\n")
                f.write("=" * 80 + "\n\n")
                for movie in movie_list:
                    f.write(f"[{movie['title']}]({movie['player_url']})\n")

            print(f"\n🎉 Berhasil update {len(movie_list)} film dari {base_url}")
            return True

        except Exception as e:
            print(f"   Error di {base_url}: {e}")
            time.sleep(3)

    print("❌ Semua domain gagal dicoba.")
    return False


if __name__ == "__main__":
    scrape_films()
