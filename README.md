# Instagram Downloader Skill

> Download Instagram media — reels, carousels, photos — via **Apify Actor data** with optional **instagrapi carousel enhancement** (no login required).

[![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Apify](https://img.shields.io/badge/Apify-Actor-orange)](https://apify.com/unseenuser/IG-posts)

---

## Table of Contents

- [Why This Tool Exists](#why-this-tool-exists)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Guide](#usage-guide)
  - [Input Sources](#input-sources)
  - [Filters](#filters)
  - [Output Modes](#output-modes)
  - [Carousel Enhancement](#carousel-enhancement)
- [Examples](#examples)
- [Output Structure](#output-structure)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Contributing](#contributing)
- [License](#license)

---

## Why This Tool Exists

Traditional Instagram downloaders (`instaloader`, `gallery-dl`) rely on Instagram's internal APIs and GraphQL endpoints. Since mid-2025, Instagram aggressively blocks these:
- **`403 Forbidden`** on `graphql/query` (instaloader)
- **`403`** on CDN / direct media URLs
- **`NotFound`** on profile pages scraped without browser cookies
- **`__INITIAL_STATE__`** removed from page HTML (fully client-side rendered)

This tool takes a **different approach**: it uses [Apify](https://apify.com), a reliable web scraping platform, as the primary data source. An Apify Actor (`unseenuser/IG-posts`) runs as a headless browser, logs into Instagram serverside, and returns structured JSON with all post metadata — including CDN URLs that actually work.

For **carousel posts** (multi-image), the Apify dataset only provides a single `thumbnail_url`. This tool optionally uses `instagrapi`'s GraphQL endpoint to fetch ALL carousel images without logging in — no cookies, no session, no credentials needed.

---

## Architecture

```
┌─────────────────────────┐     ┌──────────────────┐     ┌──────────────────────┐
│  Apify Actor            │────▶│  Apify Dataset   │────▶│  instagram_downloader │
│  unseenuser/IG-posts    │     │  <DATASET_ID>    │     │  .py                 │
│  (headless browser)     │     │  (JSON items)    │     │                      │
└─────────────────────────┘     └──────────────────┘     └──────────────────────┘
                                                                  │
                                      ┌───────────────────────────┴──────────┐
                                      ▼                                       ▼
                            ┌──────────────────────┐              ┌──────────────────────┐
                            │  requests.get()       │              │  instagrapi GQL      │
                            │  (reels, photos)      │              │  (carousels only)    │
                            │  Apify CDN URLs       │              │  fbcdn.net URLs      │
                            └──────────────────────┘              └──────────────────────┘
                                      │                                       │
                                      ▼                                       ▼
                            ┌───────────────────────────────────────────────────────┐
                            │              Download Output                         │
                            │  instagram_<username>/                               │
                            │  ├── YYYY-MM-DD/                                     │
                            │  │   ├── <SHORTCODE>/                                │
                            │  │   │   ├── <SHORTCODE>.mp4 (reel)                 │
                            │  │   │   ├── <SHORTCODE>_01.jpg (carousel img)      │
                            │  │   │   ├── <SHORTCODE>_02.jpg (carousel img)      │
                            │  │   │   └── post_info.txt                          │
                            │  └── ...                                             │
                            └───────────────────────────────────────────────────────┘
```

### Data Flow

1. **Apify Actor** scrapes Instagram profile → saves structured data to dataset
2. **`instagram_downloader.py`** fetches dataset items (via API or MCP toon file)
3. **For each post**:
   - **Reels**: Download `video_url_no_watermark` (MP4) + thumbnail (JPG) via `requests`
   - **Photos**: Download `thumbnail_url` (JPG) via `requests`
   - **Carousels**: Try `instagrapi` GQL first. If successful → download ALL images (JPGs). If GQL fails → fallback to Apify thumbnail (single image)
4. Files organized by date and shortcode into output directory

---

## Prerequisites

### 1. Apify Account & Actor Run

This tool does **not** scrape Instagram directly. It requires a pre-existing Apify dataset from the [`unseenuser/IG-posts`](https://apify.com/unseenuser/IG-posts) Actor:

1. Create a free [Apify account](https://console.apify.com/sign-up)
2. Go to [unseenuser/IG-posts](https://apify.com/unseenuser/IG-posts)
3. Click **"Try"** or **"Run"**
4. Enter the Instagram **username** (e.g., `username`)
5. Configure optional settings (post limit, date range)
6. Run the Actor
7. After completion, copy the **Dataset ID** from the output (e.g., `DATASET_ID`)

You'll need this Dataset ID to download media.

> **Note**: The Apify API token is only required if using `--dataset` mode. The `--toon-file` mode works without any token.

### 2. Python 3.10+

```powershell
python --version  # Should be 3.10+
```

### 3. Install Dependencies

```powershell
pip install requests instagrapi
```

---

## Installation

### Pip install (direct)

```powershell
pip install git+https://github.com/USERNAME/ig-downloader-skill.git
ig-downloader --help
```

### Or clone and install locally

```powershell
git clone https://github.com/USERNAME/ig-downloader-skill.git
cd ig-downloader-skill
pip install -r requirements.txt
python instagram_downloader.py --help
```

---

## Quick Start

### 1. Export dataset items from Apify

Get your Apify Dataset ID from a completed Actor run, then export directly:

```powershell
# Option A: Download JSON via Apify API
curl "https://api.apify.com/v2/datasets/<DATASET_ID>/items?format=json" -o dataset.json

# Option B: Use the MCP tool (if you have Apify MCP configured)
# mcp_get-dataset-items datasetId="<DATASET_ID>" → save output as toon file
```

### 2. Download all media

```powershell
python instagram_downloader.py `
    --toon-file dataset.json `
    --profile username `
    --output ./my_downloads
```

Or with the Apify API directly (requires API token):

```powershell
python instagram_downloader.py `
    --dataset <DATASET_ID> `
    --api-token apify_api_xxxxxxxxx `
    --profile username `
    --output ./my_downloads
```

---

## Usage Guide

### Input Sources

| Flag | Description | Requires |
|------|-------------|----------|
| `--dataset ID` | Apify Dataset ID (fetch direct from API) | `--api-token` |
| `--api-token KEY` | Apify API token | `--dataset` |
| `--toon-file PATH` | Local JSON or toon-format file from MCP output | None |

**Choosing between modes:**

- **`--toon-file`**: Use when you already exported the dataset as JSON or have MCP output saved locally. No API token needed after export.
- **`--dataset` + `--api-token`**: Use when you want fresh data each run. Requires Apify API token from [console.apify.com](https://console.apify.com/account#/integrations)

### Filters

| Flag | Values | Default | Description |
|------|--------|---------|-------------|
| `--profile HANDLE` | Instagram handle | None | Used to classify OWN vs MENTION posts |
| `--date-start YYYY-MM-DD` | Date | None | Earliest post date (inclusive) |
| `--date-end YYYY-MM-DD` | Date | None | Latest post date (inclusive) |
| `--type T` | `reel`, `carousel`, `photo`, `all` | `all` | Filter by post type |
| `--own-only` | Flag | Off | Only posts by `--profile` (excludes mentions) |
| `--mentions-only` | Flag | Off | Only mentions from other accounts |
| `--no-instagrapi` | Flag | Off | Disable instagrapi GQL carousel enhancement |

### Output Modes

| Flag | Description |
|------|-------------|
| `--output DIR` / `-o DIR` | Output directory (default: `./instagram_downloads`) |
| `--flat` | Flatten to single directory instead of `YYYY-MM-DD/shortcode/` |

### Carousel Enhancement

By default, the script uses `instagrapi` to fetch all images in carousel posts:

- **Success**: Downloads `_01.jpg`, `_02.jpg`, ..., `_NN.jpg` for each carousel
- **Failure** (GQL query error): Falls back to a single `_01.jpg` from the Apify thumbnail

The GQL endpoint works for **recent posts** (typically last ~3-4 weeks). For older posts, instagrapi falls back automatically. Use `--no-instagrapi` to skip GQL entirely.

---

## Examples

### Download all posts from a profile (last month)

```powershell
python instagram_downloader.py `
    --toon-file dataset.json `
    --profile username `
    --date-start YYYY-MM-DD `
    --date-end YYYY-MM-DD `
    --output ./instagram_media
```

### Download only reels

```powershell
python instagram_downloader.py `
    --toon-file dataset.json `
    --type reel `
    --output ./reels_only
```

### Download own posts only (exclude mentions/tags)

```powershell
python instagram_downloader.py `
    --toon-file dataset.json `
    --profile username `
    --own-only `
    --output ./own_posts
```

### Download only mentions (tags by other accounts)

```powershell
python instagram_downloader.py `
    --toon-file dataset.json `
    --profile username `
    --mentions-only `
    --output ./mentions
```

### Flat output (no date/shortcode folders)

```powershell
python instagram_downloader.py `
    --toon-file dataset.json `
    --profile username `
    --flat `
    --output ./all_posts_flat
```

### Via Apify API directly (with token)

```powershell
python instagram_downloader.py `
    --dataset <DATASET_ID> `
    --api-token apify_api_xxxxxxxxx `
    --profile username `
    --output ./instagram_media
```

### Disable carousel enhancement (use Apify thumbnails only)

```powershell
python instagram_downloader.py `
    --toon-file dataset.json `
    --profile username `
    --no-instagrapi `
    --output ./simple_download
```

---

## Output Structure

By default, files are organized as:

```
<output-dir>/
├── YYYY-MM-DD/
│   ├── <SHORTCODE>/
│   │   ├── post_info.txt           # Metadata (author, date, type, URLs)
│   │   ├── <SHORTCODE>.mp4         # Reel video (if type=reel)
│   │   ├── <SHORTCODE>_thumb.jpg   # Thumbnail (if type=reel)
│   │   ├── <SHORTCODE>_01.jpg      # Carousel image 1 / single photo
│   │   ├── <SHORTCODE>_02.jpg      # Carousel image 2 (if exists)
│   │   ├── ...                     # More carousel images
│   │   └── <SHORTCODE>_NN.jpg      # Last carousel image
│   └── <SHORTCODE>/
│       └── ...
└── YYYY-MM-DD/
    └── ...
```

### `post_info.txt` example

```
shortcode: <SHORTCODE>
type: carousel
date: YYYY-MM-DDTHH:MM:SS.000Z
author: username
relation: own_post
url: https://www.instagram.com/p/<SHORTCODE>/
thumbnail_url: https://scontent.cdninstagram.com/v/...
```

---

## Troubleshooting

### "403 Forbidden" when downloading

**Cause**: Instagram CDN URLs expire after a few hours.

**Solution**: Re-run the Apify Actor to get fresh URLs, then re-run the download script. The script skips files that already exist, so only failed files will be re-downloaded.

### "GraphQL Query Error" for carousels

**Cause**: `instagrapi`'s GraphQL endpoint only works for recent posts (~last 3-4 weeks). Older posts require authentication.

**Solution**: The script falls back to the Apify thumbnail automatically (single image per carousel). To see which carousels used GQL vs fallback, check the download stats in the output.

### "No module named 'instagrapi'"

```powershell
pip install instagrapi
```

The script still works without instagrapi — it simply skips GQL enhancement and downloads Apify thumbnails for carousels.

### "No items found" or "0 posts match filters"

**Check**:
1. The dataset was exported correctly (check file size)
2. The `--date-start/--end` range includes posts
3. The `--type` filter matches existing posts
4. The `--own-only` has a matching `--profile`

### Apify Actor returning empty results

**Cause**: The Actor may not handle private accounts, or the account may have blocked scraping.

**Solution**: Try a different Apify Actor:
- [`apify/instagram-scraper`](https://apify.com/apify/instagram-scraper) — official, 317K+ users
- [`vendi/instagram-scraper`](https://apify.com/vendi/instagram-scraper) — alternative

### "requests.exceptions.SSLError"

```powershell
python instagram_downloader.py --toon-file data.json --no-verify
```

> **Warning**: Only use `--no-verify` temporarily. Fix your SSL certificates.

---

## FAQ

**Q: Do I need to log into Instagram?**
A: No. The Apify Actor handles login serverside. The download script itself requires no Instagram credentials.

**Q: Do I need an Apify account?**
A: Yes, to run the Actor and obtain the dataset. Free tier offers plenty of usage.

**Q: Can I download Instagram stories / highlights?**
A: Not with this tool. The `unseenuser/IG-posts` Actor only scrapes profile posts (reels, photos, carousels).

**Q: Why not use instaloader?**
A: Instaloader returns `403 Forbidden` on all GraphQL queries as of mid-2025. Instagram aggressively blocks automated scraping.

**Q: The carousel only has 1 image?**
A: If `instagrapi` GQL fails (older posts), only the Apify thumbnail is used. Re-run when the post is more recent, or accept the single-image fallback.

**Q: Can I use this for any Instagram profile?**
A: Public profiles only (unless the Apify Actor supports login, which is not covered here).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines.

Short version:
1. Open an [issue](https://github.com/USERNAME/ig-downloader-skill/issues) for bugs or feature requests
2. Fork the repo, create a branch, commit changes
3. Open a [Pull Request](https://github.com/USERNAME/ig-downloader-skill/pulls)
4. Wait for review and approval

---

## License

Copyright (C) 2026 Edgar Zorrilla

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the [GNU General Public License](LICENSE) for more details.
