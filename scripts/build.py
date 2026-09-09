import json
import os
import shutil
import urllib.parse

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def build():
    lists_path = os.path.join(ROOT_DIR, "lists.json")
    with open(lists_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    catalogs_meta = []
    
    # Process each catalog
    for cat in config.get("catalogs", []):
        cat_id = cat["id"]
        cat_name = cat["name"]
        cat_type = cat.get("type", "movie")
        cat_file = os.path.join(ROOT_DIR, cat["file"])
        
        # Read source catalog
        if os.path.exists(cat_file):
            with open(cat_file, "r", encoding="utf-8") as f:
                raw_items = json.load(f)
        else:
            raw_items = []

        metas = []
        unique_genres = set()

        for item in raw_items:
            mid = item.get("id") or item.get("_id")
            if not mid:
                continue

            genres = list(item.get("genres", []))
            # If item has language (e.g. in letterboxd_horror), include language tag in genres
            lang = item.get("language")
            if lang:
                lang_cap = lang.capitalize()
                if lang_cap not in genres:
                    genres.append(lang_cap)

            for g in genres:
                if g:
                    unique_genres.add(g)

            meta = {
                "id": mid,
                "type": item.get("type", "movie"),
                "name": item.get("name") or item.get("title"),
                "poster": item.get("poster") or f"https://images.metahub.space/poster/small/{mid}/img",
                "posterShape": item.get("posterShape", "poster"),
                "background": item.get("background") or f"https://images.metahub.space/background/medium/{mid}/img",
                "logo": item.get("logo") or f"https://images.metahub.space/logo/medium/{mid}/img",
                "year": str(item.get("year", "")),
                "imdbRating": str(item.get("imdbRating", "")),
                "genres": genres
            }
            if item.get("letterboxdRating"):
                meta["description"] = f"Letterboxd Rating: ★ {item['letterboxdRating']}" + (f" | IMDb: {item.get('imdbRating')}" if item.get("imdbRating") else "")
            metas.append(meta)

        sorted_genres = sorted(list(unique_genres))

        # Build extra options for manifest
        extra_options = [
            {
                "name": "genre",
                "isRequired": False,
                "options": sorted_genres,
                "optionsLimit": 1
            },
            {"name": "skip", "isRequired": False},
            {"name": "search", "isRequired": False}
        ]

        catalogs_meta.append({
            "type": cat_type,
            "id": cat_id,
            "name": cat_name,
            "extra": extra_options
        })

        # Ensure directory structure:
        # catalog/{cat_type}/{cat_id}.json
        # catalog/{cat_type}/{cat_id}/genre={genre}.json
        base_dir = os.path.join(ROOT_DIR, "catalog", cat_type)
        cat_dir = os.path.join(base_dir, cat_id)
        os.makedirs(cat_dir, exist_ok=True)

        # 1. Base catalog file
        base_file = os.path.join(base_dir, f"{cat_id}.json")
        with open(base_file, "w", encoding="utf-8") as f:
            json.dump({"metas": metas}, f, indent=2)
        print(f"[{cat_id}] Generated base catalog {base_file} ({len(metas)} items).")

        # 2. skip=0.json in catalog folder
        skip_file = os.path.join(cat_dir, "skip=0.json")
        with open(skip_file, "w", encoding="utf-8") as f:
            json.dump({"metas": metas}, f, indent=2)

        # 3. Genre-filtered catalog files
        for g in sorted_genres:
            filtered_metas = [m for m in metas if g in m.get("genres", [])]
            g_filename = f"genre={g}.json"
            g_path = os.path.join(cat_dir, g_filename)
            with open(g_path, "w", encoding="utf-8") as f:
                json.dump({"metas": filtered_metas}, f, indent=2)

            # Also create skip=0 variant: genre={genre}&skip=0.json
            g_skip_path = os.path.join(cat_dir, f"genre={g}&skip=0.json")
            with open(g_skip_path, "w", encoding="utf-8") as f:
                json.dump({"metas": filtered_metas}, f, indent=2)

            # URL-encoded variant if different
            quoted_g = urllib.parse.quote(g)
            if quoted_g != g:
                q_path = os.path.join(cat_dir, f"genre={quoted_g}.json")
                with open(q_path, "w", encoding="utf-8") as f:
                    json.dump({"metas": filtered_metas}, f, indent=2)
                q_skip_path = os.path.join(cat_dir, f"genre={quoted_g}&skip=0.json")
                with open(q_skip_path, "w", encoding="utf-8") as f:
                    json.dump({"metas": filtered_metas}, f, indent=2)

        print(f"[{cat_id}] Generated {len(sorted_genres)} genre endpoints in {cat_dir}.")

    # Generate manifest.json
    manifest = {
        "id": config.get("addon_id", "org.wolfy027.stremio.catalogs"),
        "version": config.get("addon_version", "1.0.0"),
        "name": config.get("addon_name", "Wolfy's Curated Catalogs"),
        "description": config.get("addon_description", "Custom movie lists outside of the library."),
        "resources": ["catalog"],
        "types": ["movie"],
        "catalogs": catalogs_meta
    }

    manifest_file = os.path.join(ROOT_DIR, "manifest.json")
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nGenerated {manifest_file} with {len(catalogs_meta)} catalogs and full genre filters.")

if __name__ == "__main__":
    build()
