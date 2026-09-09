import urllib.request
import urllib.parse
import json
import re
import html
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "X-Requested-With": "XMLHttpRequest"
}

def fetch_letterboxd_pages(language, max_pages=3):
    print(f"Fetching Letterboxd horror films for language: {language} (pages 1 to {max_pages})...")
    req_headers = dict(HEADERS)
    req_headers["Referer"] = f"https://letterboxd.com/films/genre/horror/language/{language}/"

    films = []
    seen_slugs = set()

    for page in range(1, max_pages + 1):
        if page == 1:
            url = f"https://letterboxd.com/csi/films/films-browser-list/popular/genre/horror/language/{language}/?esiAllowFilters=true"
        else:
            url = f"https://letterboxd.com/csi/films/films-browser-list/popular/genre/horror/language/{language}/page/{page}/?esiAllowFilters=true"

        try:
            req = urllib.request.Request(url, headers=req_headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                content = resp.read().decode("utf-8")

            items = 0
            for m in re.finditer(r"<li class=\"posteritem\"([^>]*)>", content):
                block = content[m.start():m.start() + 1000]
                name_match = re.search(r"data-item-name=\"([^\"]+)\"", block)
                rating_match = re.search(r"data-average-rating=\"([0-9.]+)\"", block)
                slug_match = re.search(r"data-item-slug=\"([^\"]+)\"", block)

                if not name_match:
                    continue

                raw_name = html.unescape(name_match.group(1).strip())
                slug = slug_match.group(1).strip() if slug_match else ""
                rating_str = rating_match.group(1) if rating_match else None

                if slug in seen_slugs:
                    continue

                # Extract year
                year_match = re.search(r"\((\d{4})\)", raw_name)
                year = int(year_match.group(1)) if year_match else None
                title = re.sub(r"\s*\(\d{4}\)$", "", raw_name).strip()

                rating = float(rating_str) if rating_str else None

                items += 1
                seen_slugs.add(slug)

                # Filter: released after 2000 (year >= 2001) and Letterboxd rating >= 3.0
                if year and year > 2000 and rating and rating >= 3.0:
                    films.append({
                        "name": title,
                        "year": year,
                        "letterboxd_rating": rating,
                        "slug": slug,
                        "language": language
                    })

            print(f"  [{language}] Page {page}: {items} parsed, {len(films)} qualifying so far")
            if items == 0:
                break
        except Exception as e:
            print(f"  [{language}] Page {page} error: {e}")
            break

    return films

def get_imdb_id(slug):
    url = f"https://letterboxd.com/film/{slug}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            content = resp.read().decode("utf-8")
            m = re.search(r"imdb\.com/title/(tt\d+)", content)
            if m:
                return slug, m.group(1)
    except Exception as e:
        pass
    return slug, None

def get_cinemeta_meta(imdb_id):
    url = f"https://v3-cinemeta.strem.io/meta/movie/{imdb_id}.json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.load(resp)
            return imdb_id, data.get("meta", {})
    except Exception as e:
        return imdb_id, {}

def main():
    languages = [
        ("malayalam", 3),
        ("polish", 3),
        ("hindi", 3),
        ("english", 3)
    ]

    all_films = []
    for lang, pages in languages:
        films = fetch_letterboxd_pages(lang, max_pages=pages)
        print(f"Finished {lang}: found {len(films)} films.")
        all_films.extend(films)

    print(f"\nTotal raw candidates: {len(all_films)}")

    # Deduplicate by slug
    unique_films = []
    seen = set()
    for f in all_films:
        if f["slug"] not in seen:
            seen.add(f["slug"])
            unique_films.append(f)

    print(f"Unique films to resolve: {len(unique_films)}")

    # Resolve IMDb IDs concurrently
    print("Resolving IMDb IDs from Letterboxd...")
    slug_to_imdb = {}
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(get_imdb_id, f["slug"]): f["slug"] for f in unique_films}
        for future in as_completed(futures):
            slug, imdb_id = future.result()
            if imdb_id:
                slug_to_imdb[slug] = imdb_id

    print(f"Successfully resolved {len(slug_to_imdb)} / {len(unique_films)} IMDb IDs")

    # For any missing IMDb ID, fallback to Cinemeta search by title and year
    missing = [f for f in unique_films if f["slug"] not in slug_to_imdb]
    print(f"Attempting Cinemeta title search fallback for {len(missing)} missing items...")
    for f in missing:
        try:
            q = urllib.parse.quote(f["name"])
            url = f"https://v3-cinemeta.strem.io/catalog/movie/top/search={q}.json"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.load(resp)
                metas = data.get("metas", [])
                for m in metas:
                    m_year = int(m.get("year", 0)) if str(m.get("year", "")).isdigit() else 0
                    if abs(m_year - f["year"]) <= 1:
                        slug_to_imdb[f["slug"]] = m["id"]
                        print(f"  Fallback matched: {f['name']} -> {m['id']}")
                        break
        except Exception:
            pass

    # Filter films to those with valid IMDb ID
    valid_films = [f for f in unique_films if f["slug"] in slug_to_imdb]
    print(f"Total valid films with IMDb IDs: {len(valid_films)}")

    # Fetch Cinemeta metadata concurrently
    print("Fetching Cinemeta metadata (genres, posters, etc.)...")
    imdb_to_meta = {}
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(get_cinemeta_meta, slug_to_imdb[f["slug"]]): slug_to_imdb[f["slug"]] for f in valid_films}
        for future in as_completed(futures):
            imdb_id, meta = future.result()
            if meta:
                imdb_to_meta[imdb_id] = meta

    catalog_items = []
    seen_imdb = set()

    for f in valid_films:
        imdb_id = slug_to_imdb[f["slug"]]
        if imdb_id in seen_imdb:
            continue
        seen_imdb.add(imdb_id)

        meta = imdb_to_meta.get(imdb_id, {})
        # ensure genres includes Horror
        genres = meta.get("genres", [])
        if not genres:
            genres = ["Horror"]
        elif "Horror" not in genres:
            genres.insert(0, "Horror")

        name = meta.get("name") or f["name"]
        year = str(meta.get("year") or f["year"])
        imdb_rating = str(meta.get("imdbRating") or "")
        lb_rating = str(f["letterboxd_rating"])

        poster = meta.get("poster") or f"https://images.metahub.space/poster/small/{imdb_id}/img"
        background = meta.get("background") or f"https://images.metahub.space/background/medium/{imdb_id}/img"
        logo = meta.get("logo") or f"https://images.metahub.space/logo/medium/{imdb_id}/img"

        item = {
            "id": imdb_id,
            "type": "movie",
            "name": name,
            "year": year,
            "imdbRating": imdb_rating,
            "letterboxdRating": lb_rating,
            "language": f["language"],
            "poster": poster,
            "background": background,
            "logo": logo,
            "genres": genres
        }
        catalog_items.append(item)

    # Sort: group by Letterboxd rating descending
    catalog_items.sort(key=lambda x: float(x.get("letterboxdRating", 0)), reverse=True)

    out_file = "/home/kinga/workspace/agy_projects/stremioLibrary/stremio-catalogs/catalogs/letterboxd_horror.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(catalog_items, f, indent=2)

    print(f"\nSuccessfully written {len(catalog_items)} horror movies to {out_file}")
    print("\nSummary by language:")
    by_lang = {}
    for it in catalog_items:
        lang = it.get("language", "unknown")
        by_lang[lang] = by_lang.get(lang, 0) + 1
    for l, c in by_lang.items():
        print(f"  {l.capitalize()}: {c} movies")

if __name__ == "__main__":
    main()
