import cloudscraper
from bs4 import BeautifulSoup
import json
import re
import time
from datetime import datetime

BASE_URL = "https://tv1.lk21official.love"
PLAYER_DOMAIN = "https://playeriframe.sbs/iframe/p2p/"


def get_player_id(scraper, detail_url, retries=2):
    """Ambil player ID dari halaman detail film."""
    for attempt in range(retries):
        try:
            res = scraper.get(detail_url, timeout=15)
            if res.status_code != 200:
                return None

            soup = BeautifulSoup(res.text, "html.parser")

            # Cari iframe dengan domain playeriframe.sbs
            iframes = soup.find_all("iframe")
            for iframe in iframes:
                src = iframe.get("src", "") or iframe.get("data-src", "")
                if "playeriframe.sbs" in src:
                    # Ambil ID dari URL
                    # Format: https://playeriframe.sbs/iframe/p2p/ID_DISINI
                    match = re.search(r"/iframe/p2p/([^/?&\"']+)", src)
                    if match:
                        return match.group(1)

            # Cari di script tag kalau tidak ada di iframe langsung
            scripts = soup.find_all("script")
            for script in scripts:
                text = script.string or ""
                match = re.search(r"playeriframe\.sbs/iframe/p2p/([^/?&\"'\\s]+)", text)
                if match:
                    return match.group(1)

            return None

        except Exception as e:
            print(f"  ⚠️ Attempt {attempt+1} gagal untuk {detail_url}: {e}")
            time.sleep(2)

    return None


def scrape_films():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Mengambil daftar film dari lk21...")
    try:
        scraper = cloudscraper.create_scraper()

        # Step 1: Ambil list film
        res = scraper.get(BASE_URL, timeout=15)
        if res.status_code != 200:
            print(f"Gagal scrape: Status {res.status_code}")
            return False

        soup = BeautifulSoup(res.text, "html.parser")
        films = soup.select("a[itemprop='url']")

        # Kumpulkan film unik dulu
        unique_films = []
        seen = set()

        for film in films:
            href = film.get("href", "").strip()
            if not href or href == "#":
                continue

            slug = href.strip("/").split("/")[-1]
            if slug in seen:
                continue
            seen.add(slug)

            title_tag = film.select_one("h3.poster-title")
            title = title_tag.text.strip() if title_tag else "Unknown Title"

            year_tag = film.select_one("span.year")
            year = year_tag.text.strip() if year_tag else ""

            rating_tag = film.select_one("span[itemprop='ratingValue']")
            rating = rating_tag.text.strip() if rating_tag else ""

            poster_tag = film.select_one("img[itemprop='image']")
            poster = poster_tag.get("src", "") if poster_tag else ""

            duration_tag = film.select_one("span.duration")
            duration = duration_tag.text.strip() if duration_tag else ""

            quality_tag = film.select_one("span.label")
            quality = quality_tag.text.strip() if quality_tag else ""

            # Buat full URL detail
            if href.startswith("http"):
                detail_url = href
            else:
                detail_url = BASE_URL + "/" + slug

            unique_films.append({
                "title": title,
                "slug": slug,
                "year": year,
                "rating": rating,
                "poster": poster,
                "duration": duration,
                "quality": quality,
                "detail_url": detail_url,
            })

        print(f"Ditemukan {len(unique_films)} film unik. Mengambil player ID...")

        # Step 2: Masuk ke tiap halaman detail, ambil player ID
        movie_list = []
        for i, film in enumerate(unique_films, 1):
            print(f"  [{i}/{len(unique_films)}] {film['title']}...", end=" ", flush=True)

            player_id = get_player_id(scraper, film["detail_url"])

            if player_id:
                player_url = PLAYER_DOMAIN + player_id
                print(f"✅ {player_id[:20]}...")
            else:
                # Fallback ke slug kalau tidak dapat ID
                player_url = PLAYER_DOMAIN + film["slug"]
                print(f"⚠️ fallback ke slug")

            movie_list.append({
                "title": film["title"],
                "slug": film["slug"],
                "year": film["year"],
                "rating": film["rating"],
                "poster": film["poster"],
                "duration": film["duration"],
                "quality": film["quality"],
                "player_url": player_url,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            # Delay antar request biar tidak kena rate limit
            time.sleep(1)

        # Simpan ke movies.json
        with open("movies.json", "w", encoding="utf-8") as f:
            json.dump({
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total": len(movie_list),
                "movies": movie_list
            }, f, ensure_ascii=False, indent=2)

        # Simpan ke direct_links.txt
        with open("direct_links.txt", "w", encoding="utf-8") as f:
            f.write(f"DAFTAR FILM LANGSUNG (Auto Update)\n")
            f.write(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            for movie in movie_list:
                f.write(f"[{movie['title']}]({movie['player_url']})\n")

        print(f"\nBerhasil update {len(movie_list)} film")
        return True

    except Exception as e:
        print(f"Error saat scrape: {e}")
        return False


if __name__ == "__main__":
    scrape_films()
