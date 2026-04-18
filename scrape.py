import cloudscraper
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime

BASE_URL = "http://139.59.72.171"          # Bisa juga "https://bioskop2l.lk21.in.net"
PLAYER_PARAMS = ["?player=1", "?player=2", "?player=3"]

def get_best_player_url(scraper, detail_url):
    """Coba ketiga player, ambil yang paling mungkin berhasil"""
    for param in PLAYER_PARAMS:
        try:
            test_url = detail_url.rstrip("/") + param
            res = scraper.get(test_url, timeout=15)
            
            if res.status_code != 200:
                continue
                
            soup = BeautifulSoup(res.text, "html.parser")
            
            # Cek apakah ada iframe player
            iframes = soup.find_all("iframe")
            for iframe in iframes:
                src = iframe.get("src", "")
                if src and len(src) > 20:   # biasanya short.icu atau link player
                    print(f"   ✅ Player ditemukan: {param}")
                    return test_url
                    
        except:
            continue
            
        time.sleep(1)
    
    # Fallback ke player=3 kalau semua gagal
    print(f"   ⚠️ Pakai fallback {PLAYER_PARAMS[-1]}")
    return detail_url.rstrip("/") + PLAYER_PARAMS[-1]


def scrape_films():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Scraping film dari mirror LK21...")

    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        },
        delay=8
    )

    try:
        res = scraper.get(BASE_URL, timeout=25)
        if res.status_code != 200:
            print(f"Gagal akses homepage: Status {res.status_code}")
            return False

        soup = BeautifulSoup(res.text, "html.parser")

        # Selector untuk daftar film di tema Muvipro
        film_items = soup.select("article.item, .gmr-box-content, .gmr-grid .item, .post")

        movie_list = []
        seen = set()

        print(f"Ditemukan {len(film_items)} elemen potensial film...")

        for i, item in enumerate(film_items, 1):
            link_tag = item.select_one("a[href]")
            if not link_tag:
                continue

            href = link_tag.get("href", "").strip()
            if not href or any(x in href for x in ["/category/", "/year/", "/tag/", "/author/"]):
                continue

            if href.startswith("http"):
                detail_url = href
            else:
                detail_url = BASE_URL.rstrip("/") + "/" + href.strip("/")

            slug = detail_url.strip("/").split("/")[-1]
            if slug in seen or len(slug) < 3:
                continue
            seen.add(slug)

            title_tag = item.select_one("h2, h3, .entry-title")
            title = title_tag.text.strip() if title_tag else "Unknown Title"

            # Ambil poster
            img = item.select_one("img")
            poster = img.get("src") or img.get("data-src", "") if img else ""

            # Dapatkan player URL terbaik
            print(f"[{i}/{len(film_items)}] {title[:60]}...", end=" ")
            player_url = get_best_player_url(scraper, detail_url)
            print("✅")

            movie_list.append({
                "title": title,
                "slug": slug,
                "poster": poster,
                "player_url": player_url,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            time.sleep(1.2)   # delay biar tidak kena block

        # Simpan hasil
        with open("movies.json", "w", encoding="utf-8") as f:
            json.dump({
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total": len(movie_list),
                "base_url": BASE_URL,
                "movies": movie_list
            }, f, ensure_ascii=False, indent=2)

        with open("direct_links.txt", "w", encoding="utf-8") as f:
            f.write(f"DAFTAR FILM LK21 - Auto Update\n")
            f.write(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Base: {BASE_URL}\n")
            f.write("=" * 90 + "\n\n")
            for m in movie_list:
                f.write(f"[{m['title']}]({m['player_url']})\n")

        print(f"\n🎉 Berhasil scrape {len(movie_list)} film!")
        return True

    except Exception as e:
        print(f"\nError besar: {e}")
        return False


if __name__ == "__main__":
    scrape_films()