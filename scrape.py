import cloudscraper
from bs4 import BeautifulSoup
import json
import re
import time
from datetime import datetime

BASE_URLS = [
    "https://tv1.lk21official.love",
    "http://139.59.72.171",
    "https://bioskop2l.lk21.in.net",
    "https://tv10.lk21official.cc",
]

PLAYER_DOMAIN = "https://playeriframe.sbs/iframe/p2p/"
PLAYER_PARAMS = ["?player=3", "?player=2", "?player=1"]

def get_player_url(scraper, detail_url):
    for attempt in range(3):
        try:
            res = scraper.get(detail_url, timeout=20)
            if res.status_code != 200:
                continue
            soup = BeautifulSoup(res.text, "html.parser")

            # Cari iframe playeriframe.sbs
            for iframe in soup.find_all("iframe"):
                src = iframe.get("src", "") or iframe.get("data-src", "")
                if "playeriframe.sbs" in src:
                    match = re.search(r"/iframe/p2p/([^/?&\"']+)", src)
                    if match:
                        return PLAYER_DOMAIN + match.group(1)

            # Cari di script tag
            for script in soup.find_all("script"):
                text = script.string or ""
                match = re.search(r"playeriframe\.sbs/iframe/p2p/([^/?&\"'\\s]+)", text)
                if match:
                    return PLAYER_DOMAIN + match.group(1)

        except Exception as e:
            print(f"   Attempt {attempt+1} gagal: {e}")
            time.sleep(2)

    # Fallback
    print(f"   ⚠️ Fallback ke player=3")
    return detail_url.rstrip("/") + PLAYER_PARAMS[0]


def scrape_films():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Mulai scrape LK21 dengan pagination...")

    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False},
        delay=10
    )

    for base_url in BASE_URLS:
        movie_list = []
        seen = set()
        max_pages = 50   # Ubah jadi 10-12 kalau mau lebih banyak

        print(f"→ Mencoba domain: {base_url}")

        for page in range(1, max_pages + 1):
            if page == 1:
                url = base_url
            else:
                url = f"{base_url}/page/{page}/"     # pola umum pagination

            try:
                res = scraper.get(url, timeout=25)
                if res.status_code != 200:
                    print(f"   Halaman {page} → Status {res.status_code}, stop pagination")
                    break

                soup = BeautifulSoup(res.text, "html.parser")

                # Selector yang lebih longgar (cocok untuk banyak tema LK21)
                film_elements = soup.select("article.item, .gmr-box-content, .post, .item, div[class*='box'], a[href*='/']")

                print(f"   Halaman {page}: menemukan {len(film_elements)} elemen potensial")

                for element in film_elements:
                    # Cari link detail
                    link_tag = element.select_one("a[href]") or element
                    href = link_tag.get("href", "").strip() if hasattr(link_tag, "get") else ""

                    if not href or href == "#" or any(x in href for x in ["/category/", "/year/", "/tag/", "/author/"]):
                        continue

                    if href.startswith("http"):
                        detail_url = href
                    else:
                        detail_url = base_url.rstrip("/") + "/" + href.strip("/")

                    slug = detail_url.strip("/").split("/")[-1]
                    if not slug or slug in seen or len(slug) < 3:
                        continue
                    seen.add(slug)

                    # Ambil judul
                    title_tag = element.select_one("h2, h3, .entry-title, .gmr-title, .poster-title")
                    title = title_tag.text.strip() if title_tag else slug.replace("-", " ").title()

                    # Ambil poster
                    img = element.select_one("img")
                    poster = img.get("src", "") or img.get("data-src", "") if img else ""

                    print(f"     → {title[:60]}...")

                    player_url = get_player_url(scraper, detail_url)

                    movie_list.append({
                        "title": title,
                        "slug": slug,
                        "poster": poster,
                        "player_url": player_url,
                        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })

                time.sleep(2)  # jeda antar halaman

            except Exception as e:
                print(f"   Error halaman {page}: {e}")
                break

        if movie_list:
            print(f"\n🎉 Berhasil scrape {len(movie_list)} film dari {base_url}")
            
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
                f.write(f"Domain: {base_url} | Halaman: 1-{max_pages}\n")
                f.write("=" * 90 + "\n\n")
                for m in movie_list:
                    f.write(f"[{m['title']}]({m['player_url']})\n")

            return True

    print("❌ Semua domain gagal.")
    return False


if __name__ == "__main__":
    scrape_films()
