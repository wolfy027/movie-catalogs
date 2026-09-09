import json
import os
import shutil

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def build():
    lists_path = os.path.join(ROOT_DIR, "lists.json")
    with open(lists_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    catalogs_meta = []
    for cat in config.get("catalogs", []):
        cat_id = cat["id"]
        cat_name = cat["name"]
        cat_type = cat.get("type", "movie")
        cat_file = os.path.join(ROOT_DIR, cat["file"])
        
        catalogs_meta.append({
            "type": cat_type,
            "id": cat_id,
            "name": cat_name,
            "extra": [
                {"name": "search", "isRequired": False},
                {"name": "skip", "isRequired": False}
            ]
        })
        
        # Read source catalog
        if os.path.exists(cat_file):
            with open(cat_file, "r", encoding="utf-8") as f:
                raw_items = json.load(f)
        else:
            raw_items = []
            
        metas = []
        for item in raw_items:
            mid = item.get("id") or item.get("_id")
            if not mid:
                continue
            metas.append({
                "id": mid,
                "type": item.get("type", "movie"),
                "name": item.get("name") or item.get("title"),
                "poster": item.get("poster") or f"https://images.metahub.space/poster/small/{mid}/img",
                "posterShape": item.get("posterShape", "poster"),
                "background": item.get("background") or f"https://images.metahub.space/background/medium/{mid}/img",
                "logo": item.get("logo") or f"https://images.metahub.space/logo/medium/{mid}/img",
                "year": item.get("year"),
                "imdbRating": str(item.get("imdbRating", "")),
                "genres": item.get("genres", [])
            })
            
        # Write to catalog/movie/{cat_id}.json
        out_dir = os.path.join(ROOT_DIR, "catalog", cat_type)
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, f"{cat_id}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump({"metas": metas}, f, indent=2)
        print(f"Generated {out_file} with {len(metas)} items.")

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
    print(f"Generated {manifest_file} with {len(catalogs_meta)} catalogs.")

if __name__ == "__main__":
    build()
