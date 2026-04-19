import cloudscraper
from bs4 import BeautifulSoup
import json
import re
import time
from datetime import datetime

# Semua domain yang akan di-scrape
BASE_URLS = [
    "https://tv1.lk21official.love",
    "http://139.59.72.171",
    "https://bioskop2l.lk21.in.net",
    "https://tv10.lk21official.cc",
    "http://139.59.34.5",
    "https://packplace.org",
]

PLAYER_DOMAIN = "https://playeriframe.sbs/iframe/p2p/"
PLAYER_PARAMS = ["?player=1", "?player=2", "?player=3"]

MAX_PAGES = 50


def get_player_url(scraper, detail_url):
    """
    Coba ambil player ID asli dari iframe playeriframe.sbs.
    Kalau tidak ketemu, coba ?player=1/2/3 dan cek mana yang ada iframe-nya.
    Kalau semua gagal, fallback ke ?player=3.
    """
    # Cara 1: Coba ambil player ID asli dari halaman detail
    for attempt in range(2):
        try:
            res = scraper.get(detail_url, timeout=20)
            if res.status_code != 200:
                break

            soup = BeautifulSoup(res.text, "html.parser")

            # Cari iframe playeriframe.sbs
            for iframe in soup.find_all("iframe"):
                src = iframe.get("src", "") or iframe.get("data-src", "")
                if "playeriframe.sbs" in src:
                    match = re.search(r"/iframe/p2p/([^/?&\"']+)", src)
                    if match:
                        player_id = match.group(1)
                        print(f"✅ ID: {player_id[:20]}...")
                        return PLAYER_DOMAIN + player_id

            # Cari di script tag
            for script in soup.find_all("script"):
                text = script.string or ""
                match = re.search(r"playeriframe\.sbs/iframe/p2p/([^/?&\"'\s]+)", text)
                if match:
                    player_id = match.group(1)
                    print(f"✅ ID (script): {player_id[:20]}...")
                    return PLAYER_DOMAIN + player_id

        except Exception as e:
            print(f"   Attempt {attempt+1} gagal: {e}")
            time.sleep(1)

    # Cara 2: Coba ?player=1/2/3 dan cek mana yang ada iframe
    for param in PLAYER_PARAMS:
        try:
            test_url = detail_url.rstrip("/") + param
            res = scraper.get(test_url, timeout=15)
            if res.status_code != 200:
                continue

            soup = BeautifulSoup(res.text, "html.parser")
            for iframe in soup.find_all("iframe"):
                src = iframe.get("src", "")
                if src and len(src) > 20:
                    print(f"✅ player param: {param}")
                    return test_url

        except Exception:
            continue

        time.sleep(0.5)

    # Fallback terakhir
    print(f"   ⚠️ fallback ?player=3")
    return detail_url.rstrip("/") + "?player=3"


def detect_pagination_format(scraper, base_url):
    """Deteksi format pagination domain secara otomatis."""
    test_formats = [
        base_url.rstrip("/") + "/page/2/",
        base_url.rstrip("/") + "/release/page/2/",
        base_url.rstrip("/") + "/film/page/2/",
        base_url.rstrip("/") + "/movies/page/2/",
    ]
    for fmt in test_formats:
        try:
            res = scraper.get(fmt, timeout=15)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                films = soup.select("a[itemprop='url'], article.item a, .gmr-box-content a")
                if films:
                    print(f"   Pagination: {fmt}")
                    return fmt.replace("/2/", "/{n}/")
        except Exception:
            continue
    return base_url.rstrip("/") + "/page/{n}/"


def scrape_all_pages(scraper, base_url, seen_global):
    """Ambil semua film dari semua halaman, skip slug yang sudah ada di seen_global."""
    all_films = []
    seen_local = set()
    pagination_fmt = detect_pagination_format(scraper, base_url)
    page = 1

    while page <= MAX_PAGES:
        url = base_url if page == 1 else pagination_fmt.replace("{n}", str(page))
        print(f"  → Hal {page}: {url}")

        try:
            res = scraper.get(url, timeout=25)

            if res.status_code == 404:
                print(f"     404, berhenti.")
                break

            if res.status_code != 200:
                print(f"     Status {res.status_code}, berhenti.")
                break

            soup = BeautifulSoup(res.text, "html.parser")
            films = soup.select("a[itemprop='url'], article.item a, .gmr-box-content a, article.item, .gmr-box-content, .post")

            new_count = 0
            for film in films:
                # Support dua tipe selector: langsung <a> atau parent element
                if film.name == "a":
                    link_tag = film
                else:
                    link_tag = film.select_one("a[href]")

                if not link_tag:
                    continue

                href = link_tag.get("href", "").strip()
                if (not href or href == "#"
                        or any(x in href for x in ["/category/", "/year/", "/page/", "/tag/", "/genre/", "/author/"])):
                    continue

                slug = href.strip("/").split("/")[-1]
                if not slug or len(slug) < 3 or slug in seen_local or slug in seen_global:
                    continue

                seen_local.add(slug)

                title_tag = film.select_one("h3.poster-title, h2, h3, .entry-title")
                title = title_tag.text.strip() if title_tag else "Unknown Title"

                year_tag = film.select_one("span.year")
                year = year_tag.text.strip() if year_tag else ""

                rating_tag = film.select_one("span[itemprop='ratingValue']")
                rating = rating_tag.text.strip() if rating_tag else ""

                poster_tag = film.select_one("img[itemprop='image'], img")
                poster = ""
                if poster_tag:
                    poster = poster_tag.get("src") or poster_tag.get("data-src", "")

                duration_tag = film.select_one("span.duration")
                duration = duration_tag.text.strip() if duration_tag else ""

                quality_tag = film.select_one("span.label")
                quality = quality_tag.text.strip() if quality_tag else ""

                detail_url = href if href.startswith("http") else base_url.rstrip("/") + "/" + slug

                all_films.append({
                    "title": title,
                    "slug": slug,
                    "year": year,
                    "rating": rating,
                    "poster": poster,
                    "duration": duration,
                    "quality": quality,
                    "detail_url": detail_url,
                })
                new_count += 1

            print(f"     +{new_count} film baru | Total domain ini: {len(all_films)}")

            if new_count == 0:
                print(f"     Tidak ada film baru, berhenti.")
                break

            page += 1
            time.sleep(2)

        except Exception as e:
            print(f"     Error halaman {page}: {e}")
            break

    return all_films


def scrape_films():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Mulai scrape semua domain LK21...")

    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False},
        delay=10
    )

    all_movie_list = []
    seen_global = set()  # Track slug global biar tidak duplikat antar domain

    for base_url in BASE_URLS:
        try:
            print(f"\n{'='*60}")
            print(f"→ Domain: {base_url}")
            res = scraper.get(base_url, timeout=25)

            if res.status_code != 200:
                print(f"   Status: {res.status_code} → skip")
                continue

            print(f"✅ Terkoneksi ke {base_url}")

            unique_films = scrape_all_pages(scraper, base_url, seen_global)

            if not unique_films:
                print("   Tidak ada film baru dari domain ini.")
                continue

            print(f"\n{len(unique_films)} film baru dari {base_url}. Mengambil player URL...")

            domain_count = 0
            for i, film in enumerate(unique_films, 1):
                print(f"  [{i}/{len(unique_films)}] {film['title'][:55]}... ", end="", flush=True)

                player_url = get_player_url(scraper, film["detail_url"])

                all_movie_list.append({
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

                seen_global.add(film["slug"])
                domain_count += 1
                time.sleep(1.5)

            print(f"\n✅ {domain_count} film dari {base_url} berhasil ditambahkan.")

        except Exception as e:
            print(f"   Error di {base_url}: {e}")
            time.sleep(3)
            continue

    if not all_movie_list:
        print("\n❌ Tidak ada film yang berhasil di-scrape dari semua domain.")
        return False

    # Simpan ke movies.json
    with open("movies.json", "w", encoding="utf-8") as f:
        json.dump({
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total": len(all_movie_list),
            "movies": all_movie_list
        }, f, ensure_ascii=False, indent=2)

    # Simpan ke direct_links.txt
    with open("direct_links.txt", "w", encoding="utf-8") as f:
        f.write(f"DAFTAR FILM LANGSUNG (Auto Update)\n")
        f.write(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total: {len(all_movie_list)} film\n")
        f.write("=" * 80 + "\n\n")
        for movie in all_movie_list:
            f.write(f"[{movie['title']}]({movie['player_url']})\n")

    print(f"\n🎉 Total {len(all_movie_list)} film dari semua domain berhasil disimpan!")
    return True


if __name__ == "__main__":
    scrape_films()
