import argparse
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_cinemeta_meta(query=None, imdb_id=None):
    if not imdb_id and query:
        search_url = "https://v3-cinemeta.strem.io/catalog/movie/top/search=" + urllib.parse.quote(query) + ".json"
        req = urllib.request.Request(search_url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                metas = data.get("metas", [])
                if not metas:
                    return None
                imdb_id = metas[0].get("id")
        except Exception as e:
            print(f"Error searching Cinemeta: {e}")
            return None

    if not imdb_id:
        return None

    meta_url = f"https://v3-cinemeta.strem.io/meta/movie/{imdb_id}.json"
    req = urllib.request.Request(meta_url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get("meta", {})
    except Exception as e:
        print(f"Error fetching meta for {imdb_id}: {e}")
        return None

def load_config():
    with open(os.path.join(ROOT_DIR, "lists.json"), "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config):
    with open(os.path.join(ROOT_DIR, "lists.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

def rebuild():
    build_script = os.path.join(ROOT_DIR, "scripts", "build.py")
    subprocess.run([sys.executable, build_script], check=True)

def cmd_create_list(list_id, name):
    config = load_config()
    for cat in config.get("catalogs", []):
        if cat["id"] == list_id:
            print(f"List with ID '{list_id}' already exists.")
            return

    cat_file_rel = f"catalogs/{list_id}.json"
    cat_file_abs = os.path.join(ROOT_DIR, cat_file_rel)
    if not os.path.exists(cat_file_abs):
        with open(cat_file_abs, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)

    config.setdefault("catalogs", []).append({
        "id": list_id,
        "name": name,
        "type": "movie",
        "file": cat_file_rel
    })
    save_config(config)
    rebuild()
    print(f"Created new list '{name}' ({list_id}).")

def cmd_add_movie(list_id, title=None, imdb_id=None):
    config = load_config()
    cat_entry = None
    for cat in config.get("catalogs", []):
        if cat["id"] == list_id:
            cat_entry = cat
            break

    if not cat_entry:
        print(f"Error: List '{list_id}' not found in lists.json.")
        return

    meta = fetch_cinemeta_meta(query=title, imdb_id=imdb_id)
    if not meta:
        print(f"Error: Could not find movie '{title or imdb_id}' on Cinemeta.")
        return

    mid = meta.get("id")
    mname = meta.get("name")
    myear = meta.get("year")
    mrating = meta.get("imdbRating")

    cat_file = os.path.join(ROOT_DIR, cat_entry["file"])
    if os.path.exists(cat_file):
        with open(cat_file, "r", encoding="utf-8") as f:
            items = json.load(f)
    else:
        items = []

    # Check for duplicate
    if any(item.get("id") == mid for item in items):
        print(f"Movie '{mname}' ({mid}) already exists in '{list_id}'.")
        return

    items.append({
        "id": mid,
        "type": "movie",
        "name": mname,
        "year": myear,
        "imdbRating": mrating,
        "poster": meta.get("poster"),
        "background": meta.get("background"),
        "logo": meta.get("logo"),
        "genres": meta.get("genres", [])
    })

    with open(cat_file, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)

    rebuild()
    print(f"Successfully added '{mname}' ({myear}) [IMDb: {mrating}] to list '{list_id}'.")

def cmd_remove_movie(list_id, title=None, imdb_id=None):
    config = load_config()
    cat_entry = None
    for cat in config.get("catalogs", []):
        if cat["id"] == list_id:
            cat_entry = cat
            break

    if not cat_entry:
        print(f"Error: List '{list_id}' not found.")
        return

    cat_file = os.path.join(ROOT_DIR, cat_entry["file"])
    if not os.path.exists(cat_file):
        print(f"List file does not exist: {cat_file}")
        return

    with open(cat_file, "r", encoding="utf-8") as f:
        items = json.load(f)

    target_id = imdb_id
    if not target_id and title:
        for item in items:
            if item.get("name", "").lower() == title.lower():
                target_id = item.get("id")
                break

    new_items = [i for i in items if i.get("id") != target_id and i.get("name", "").lower() != (title or "").lower()]
    removed_count = len(items) - len(new_items)
    if removed_count == 0:
        print(f"Movie '{title or imdb_id}' not found in '{list_id}'.")
        return

    with open(cat_file, "w", encoding="utf-8") as f:
        json.dump(new_items, f, indent=2)

    rebuild()
    print(f"Removed {removed_count} movie(s) from '{list_id}'.")

def cmd_git_push(commit_msg="Update Stremio catalogs"):
    print("Staging and pushing changes to GitHub...")
    subprocess.run(["git", "add", "."], cwd=ROOT_DIR, check=True)
    res = subprocess.run(["git", "commit", "-m", commit_msg], cwd=ROOT_DIR, capture_output=True, text=True)
    if "nothing to commit" in res.stdout:
        print("Nothing to commit (working tree clean).")
    else:
        print(res.stdout)
    subprocess.run(["git", "push", "origin", "main"], cwd=ROOT_DIR, check=True)
    print("Push to GitHub complete!")

def main():
    parser = argparse.ArgumentParser(description="Manage Stremio Custom Catalogs")
    subparsers = parser.add_subparsers(dest="command")

    add_p = subparsers.add_parser("add", help="Add movie to list")
    add_p.add_argument("--list", required=True, help="List ID")
    add_p.add_argument("--title", help="Movie title")
    add_p.add_argument("--imdb", help="IMDb ID (tt...)")

    rem_p = subparsers.add_parser("remove", help="Remove movie from list")
    rem_p.add_argument("--list", required=True, help="List ID")
    rem_p.add_argument("--title", help="Movie title")
    rem_p.add_argument("--imdb", help="IMDb ID")

    create_p = subparsers.add_parser("create-list", help="Create new list")
    create_p.add_argument("--id", required=True, help="List ID (e.g. sci_fi)")
    create_p.add_argument("--name", required=True, help="Display Name")

    subparsers.add_parser("build", help="Rebuild manifest and catalog JSONs")
    subparsers.add_parser("push", help="Commit and push to GitHub")

    args = parser.parse_args()
    if args.command == "add":
        cmd_add_movie(args.list, title=args.title, imdb_id=args.imdb)
    elif args.command == "remove":
        cmd_remove_movie(args.list, title=args.title, imdb_id=args.imdb)
    elif args.command == "create-list":
        cmd_create_list(args.id, args.name)
    elif args.command == "build":
        rebuild()
    elif args.command == "push":
        cmd_git_push()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
