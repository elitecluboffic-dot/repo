import cloudscraper
from bs4 import BeautifulSoup
import json
from datetime import datetime

BASE_URL = "https://tv10.lk21official.cc"
PLAYER_BASE = "https://playeriframe.sbs/iframe/p2p/"


def scrape_films():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Mengambil daftar film dari lk21...")
    try:
        scraper = cloudscraper.create_scraper()
        res = scraper.get(BASE_URL, timeout=15)

        if res.status_code != 200:
            print(f"Gagal scrape: Status {res.status_code}")
            return False

        soup = BeautifulSoup(res.text, "html.parser")
        films = soup.select("a[itemprop='url']")

        movie_list = []
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

            direct_player = PLAYER_BASE + slug

            movie_list.append({
                "title": title,
                "slug": slug,
                "year": year,
                "rating": rating,
                "poster": poster,
                "duration": duration,
                "quality": quality,
                "player_url": direct_player,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

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

        print(f"Berhasil update {len(movie_list)} film")
        return True

    except Exception as e:
        print(f"Error saat scrape: {e}")
        return False


if __name__ == "__main__":
    scrape_films()
