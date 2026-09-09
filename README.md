# Wolfy's Curated Catalogs (Stremio Addon)

Custom Stremio movie catalogs displayed outside of your library on **Home / Board** and **Discover** screens. Updated programmatically via Antigravity Remote.

---

## 📺 Stremio Addon URL
Once GitHub Pages is enabled, install this URL in Stremio on **any device** (Android TV, Mobile, Desktop):
```text
https://wolfy027.github.io/movie-catalogs/manifest.json
```

---

## 🚀 How to Enable GitHub Pages (One-time Setup)
1. Go to your repository settings on GitHub: `https://github.com/wolfy027/movie-catalogs/settings/pages`
2. Under **Build and deployment**:
   - **Source**: `Deploy from a branch`
   - **Branch**: `main`
   - **Folder**: `/ (root)`
3. Click **Save**.
4. In ~30 seconds, your addon will be live at `https://wolfy027.github.io/movie-catalogs/manifest.json`.

---

## 📁 Repository Structure
```text
movie-catalogs/
├── manifest.json              # Main Stremio Addon manifest
├── lists.json                 # Registry defining all custom catalogs
├── catalogs/                  # Raw movie entries for each catalog
│   ├── antigravity_picks.json
│   └── reddit_masterpieces.json
├── catalog/movie/             # Generated Stremio endpoints
│   ├── antigravity_picks.json
│   └── reddit_masterpieces.json
└── scripts/
    ├── build.py               # Rebuilds manifest and catalog endpoints
    └── manage_list.py         # CLI tool for Antigravity Remote management
```

---

## 🤖 Managing Lists with Antigravity Remote

You can ask Antigravity in chat to update your lists anytime:
* *"Add Interstellar to my Antigravity Picks list"*
* *"Create a new list called Sci-Fi Essentials"*
* *"Remove The Matrix from Reddit Masterpieces"*

Antigravity executes:
```bash
# Add movie by title
python3 scripts/manage_list.py add --list "antigravity_picks" --title "Interstellar"

# Add movie by IMDb ID
python3 scripts/manage_list.py add --list "reddit_masterpieces" --imdb "tt0816692"

# Create a brand new custom list/catalog
python3 scripts/manage_list.py create-list --id "sci_fi" --name "Sci-Fi Essentials"

# Push changes to GitHub Pages
python3 scripts/manage_list.py push
```
