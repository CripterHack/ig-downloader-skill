---
name: instagram-downloader
description: Download Instagram profile media (reels MP4, photos JPG, full carousel multi-image JPG) via Apify + instagrapi hybrid. No login required. Supports filters: date range, post type, own vs mentions.
version: 1.1.0
author: opencode
type: skill
category: data-extraction
tags:
  - instagram
  - apify
  - instagrapi
  - download
  - media
  - carousel
  - scraping
  - gql
---

# Instagram Downloader Skill

> **Purpose**: Download all media (reels, carousels with all images, photos) from an Instagram profile using a hybrid Apify + instagrapi approach. Supports filtering by date range, post type, authorship (own posts vs mentions), and flat or date-organized output.

---

## Why This Approach?

**The Problem**: Popular Instagram download tools (`instaloader`, `gallery-dl`) consistently fail with 403/NotFound errors because Instagram aggressively blocks scraping and requires session cookies that expire. Additionally, the standard Instagram web page no longer embeds JSON data (`__INITIAL_STATE__`, `__sharedData__`) — it's fully client-side rendered.

**The Hybrid Solution**:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        HYBRID ARCHITECTURE                               │
│                                                                          │
│  1. Apify Actor (unseenuser/IG-posts)                                    │
│     └─→ Scrapes profile catalog (shortcodes, types, dates)               │
│        └─→ Provides fallback CDN URLs for ALL items                      │
│                                                                          │
│  2. instagrapi GQL (per item, for carousels)                             │
│     └─→ Fetches ALL images in each carousel                             │
│        └─→ Handles fbcdn.net CDN that blocks requests.get()              │
│                                                                          │
│  3. Falls back to Apify URLs if GQL unavailable (old posts)              │
│     └─→ Reels/photos: always use Apify URLs (works fine)                 │
│        └─→ Carousels: GQL → multi-image; Apify → single thumbnail       │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key advantages**:
- ✅ **No Instagram login required** — neither Apify nor GQL needs auth
- ✅ **Full carousel extraction** — up to 20 images per carousel (vs only first image from Apify)
- ✅ **Fresh CDN URLs** — GQL returns live fbcdn.net links
- ✅ **No watermark on reels** (`video_url_no_watermark` from Apify)
- ✅ **Graceful fallback** — if GQL fails (old posts, network), Apify data is used
- ✅ **Works from OpenCoder via MCP or standalone**

---

## Architecture

### Data Flow

```
Apify Actor ──→ dataset ──→ Python script ──→ Downloads
(unseenuser/     (items:        │
 IG-posts)       shortcodes,    ├── Reels → Apify MP4 URL → requests.get() ✅
                 types,         ├── Photos → Apify JPG URL → requests.get() ✅
                 dates)         └── Carousels:
                                    ├── Try instagrapi GQL (no login)
                                    │   └── Success → ALL images (_01.jpg.._0N.jpg)
                                    │              → Download via instagrapi public.get()
                                    └── Fail → Apify thumbnail_url (first image only)
                                               → Download via requests.get()
```

### Data Fields (from Actor `unseenuser/IG-posts`)

| Field | Type | Description |
|-------|------|-------------|
| `shortcode` | string | Instagram post ID |
| `type` | string | `reel` \| `carousel` \| `photo` |
| `created_at` | string | ISO 8601 datetime |
| `author_handle` | string | Post author's handle (flat key) |
| `video_url_no_watermark` | string | MP4 URL for reels (flat key) |
| `thumbnail_url` | string | JPG thumbnail for carousels/photos |

> **⚠ Note**: Apify API returns nested JSON (`author.handle`). MCP `get-dataset-items` flattens keys. The script handles both.

---

## Prerequisites

- **Python 3.7+**
- **`requests`**: `pip install requests`
- **`instagrapi`** (optional, for full carousel extraction): `pip install instagrapi`
- **Apify account** (free tier) — only for running the Actor
- **OpenCoder** with Apify MCP tools (simplest path)

> **Without instagrapi**: The script works, but carousels only get the first image (Apify `thumbnail_url`). Install it for multi-image extraction.

---

## Workflow

### Step 1: Run the Apify Actor

```javascript
// Via MCP — search then run
const actorInfo = await mcp_search-actors({ keywords: "instagram posts" });

const result = await mcp_call-actor({
  actor: "unseenuser/IG-posts",
  input: {
    usernames: ["<username>"],
  },
  waitSecs: 60,
});
```

Result contains a `datasetId` (e.g. `<DATASET_ID>`).

### Step 2: Get Dataset Items

```javascript
const datasetResult = await mcp_get-dataset-items({
  datasetId: "<DATASET_ID>",
  limit: 999,
  clean: true,
});
```

Output is saved to a temp file (toon/YAML format).

### Step 3: Run the Download Script

```bash
# With instagrapi (carousels get all images)
python instagram_downloader.py --toon-file <temp-file> \
    --profile <username> \
    --date-start YYYY-MM-DD \
    --date-end YYYY-MM-DD \
    --output ./instagram_downloads
```

Or with Apify API token:

```bash
python instagram_downloader.py --dataset <DATASET_ID> \
    --api-token apify_api_xxx \
    --profile <username> \
    --output ./instagram_downloads
```

---

## Script Reference

**Location**: `instagram_downloader.py` (in same directory as this SKILL.md)

### Command-Line Options

#### Input Sources (choose one)

| Option | Description |
|--------|-------------|
| `--dataset ID` | Apify dataset ID to fetch from API |
| `--api-token KEY` | Apify API token (required with `--dataset`) |
| `--toon-file PATH` | Path to toon/YAML file from MCP output |

#### Filters

| Option | Description |
|--------|-------------|
| `--profile HANDLE` | Target Instagram handle. Used to classify OWN vs MENTION. |
| `--date-start YYYY-MM-DD` | Earliest post date (inclusive) |
| `--date-end YYYY-MM-DD` | Latest post date (inclusive) |
| `--type {reel,carousel,photo,all}` | Filter by post type (default: all) |
| `--own-only` | Only posts authored by `--profile` |
| `--mentions-only` | Only posts from other accounts mentioning `--profile` |

#### Output

| Option | Description |
|--------|-------------|
| `--output DIR, -o DIR` | Output directory (default: `./instagram_downloads`) |
| `--flat` | Flatten: single folder instead of `YYYY-MM-DD/shortcode/` |

#### Instagrapi Control

| Option | Description |
|--------|-------------|
| `--no-instagrapi` | Skip GQL carousel enhancement. Use Apify thumbnails only. |

#### Misc

| Option | Description |
|--------|-------------|
| `--no-verify` | Skip SSL verification (not recommended) |

### Default Output Structure

```
instagram_downloads/
├── YYYY-MM-DD/
│   ├── <SHORTCODE>/                    # Reel
│   │   ├── post_info.txt              # Metadata
│   │   ├── <SHORTCODE>.mp4            # Reel video
│   │   └── <SHORTCODE>_thumb.jpg      # Thumbnail
│   ├── <SHORTCODE>/                   # Photo
│   │   ├── post_info.txt
│   │   └── <SHORTCODE>_01.jpg
│   └── <SHORTCODE>/                   # Carousel (with GQL)
│       ├── post_info.txt
│       ├── <SHORTCODE>_01.jpg         # Image 1/N
│       ├── <SHORTCODE>_02.jpg         # Image 2/N
│       ├── ...
│       └── <SHORTCODE>_0N.jpg         # Image N/N
├── YYYY-MM-DD/
│   └── ...
└── YYYY-MM-DD/
    └── ...
```

With `--flat`:
```
instagram_downloads/
├── <SHORTCODE>.mp4
├── <SHORTCODE>_thumb.jpg
├── <SHORTCODE>_post_info.txt
├── <SHORTCODE>_01.jpg
├── <SHORTCODE>_02.jpg
└── ...
```

---

## GQL Carousel Extraction Details

### How It Works

1. For each carousel item, the script calls `instagrapi.media_info_gql(pk)` — this uses Instagram's GraphQL endpoint **without login**
2. The response contains `resources[]` with one entry per carousel slide
3. Each resource's `thumbnail_url` (fbcdn.net CDN) is extracted
4. Images are downloaded using instagrapi's `public.get()` which has browser-grade headers

### Success Rate

| Factor | Details |
|--------|---------|
| **Posts < 3 weeks old** | ~100% GQL success, all images extracted |
| **Posts 3-5 weeks old** | ~90% GQL success |
| **Posts > 5 weeks old** | GQL likely fails → falls back to Apify thumbnail (first image only) |
| **Timeout** | 20 seconds per GQL call; skipped if exceeded |
| **Unavailable** | If `instagrapi` not installed, falls back silently |

### Download Method

| CDN Provider | Method | Status |
|-------------|--------|--------|
| `instagram.fX.fna.fbcdn.net` | instagrapi `public.get()` | ✅ 200 OK |
| `instagram.fX.fna.fbcdn.net` | `requests.get()` with headers | ❌ 403 Forbidden |
| `scontent.cdninstagram.com` | `requests.get()` with headers | ✅ 200 OK (Apify URLs) |
| `video.cdninstagram.com` | `requests.get()` with headers | ✅ 200 OK (Apify URLs) |

---

## Filter Examples

### Last month's reels only

```bash
python instagram_downloader.py --toon-file ./data.txt \
    --profile username \
    --type reel \
    --date-start YYYY-MM-DD \
    --output ./reels_june
```

### Own posts only (exclude mentions)

```bash
python instagram_downloader.py --toon-file ./data.txt \
    --profile username \
    --own-only \
    --output ./own_posts
```

### Mentions only (posts by other accounts)

```bash
python instagram_downloader.py --toon-file ./data.txt \
    --profile username \
    --mentions-only \
    --output ./mentions
```

### Carousels with instagrapi disabled

```bash
python instagram_downloader.py --toon-file ./data.txt \
    --profile username \
    --type carousel \
    --no-instagrapi \
    --output ./carousels_thumbnails
```

---

## Using without Apify API Token (MCP-only)

1. **Search for the Actor** in the Apify Store: `Search → "unseenuser/IG-posts"`
2. **Run it** via `mcp_call-actor` with the target username
3. **Fetch items** via `mcp_get-dataset-items`. Output saves to a temp file
4. **Run the script** with `--toon-file` pointing to that temp file

The temp file path is shown in the MCP output (e.g. `C:\Users\<user>\.local\share\opencode\tool-output\tool_f39b...`).

---

## Known Issues & Gotchas

### 1. CDN URLs Expire
Apify media URLs expire after some time. Download soon after fetching. Apify URLs handle `requests.get()` fine.

### 2. Carousel GQL Cutoff
instagrapi GQL works **without login only for recent posts** (~last 4-5 weeks). Older posts will fall back to the Apify single-thumbnail. This is a limitation of the public GraphQL endpoint — Instagram's A1 API (used by `media_info()`) requires login. If you need full carousel extraction for older posts, consider providing Instagram login credentials for the `instagrapi.Client`.

### 3. fbcdn.net CDN Blocks Direct Requests
The fbcdn.net URLs from GQL return 403 with plain `requests.get()`, even with full browser headers. The script uses instagrapi's `public.get()` (a pre-configured `requests.Session` with Instagram headers) which works.

### 4. Actor May Not Return Everything
Free-tier Apify Actors have limits. For large profiles, paginate or use a paid plan.

### 5. No Login Required — But Rate Limits Apply
`unseenuser/IG-posts` doesn't need Instagram login, but Instagram rate limits still apply via the proxy.

### 6. Toon Parsing is Fragile
The toon/YAML parser works with OpenCoder's specific MCP output format. Prefer `--dataset` mode when possible.

### 7. File Size Verification
Script skips existing files above minimum thresholds (10KB for videos, 1KB for images). Delete folders to force re-downloads.

### 8. Reel Watermark
Apify returns `video_url_no_watermark` for reels when available. If the field is null, the reel may not have a watermark-free version.

---

## Performance Notes

- **GQL calls**: ~2-5s per carousel (sequential). 16 carousels → ~60s total
- **Downloads**: ~0.5-3s per image depending on CDN speed
- **Total for 16 carousels**: ~2-4 minutes (GQL + 137 images)
- **Reels + photos**: download instantly from Apify URLs
- **Use `--no-instagrapi`** for faster runs if you only need thumbnails

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `requests` not found | `pip install requests` |
| `instagrapi` not found | `pip install instagrapi` (optional, for carousel multi-image) |
| No items returned from Actor | Check username; profile may be private |
| 403 on Apify media URL | CDN URL expired → re-run the Actor |
| 403 on carousel image (fbcdn.net) | instagrapi handles this — ensure `instagrapi` is installed |
| Toon file not found | Check the temp file path from MCP output |
| "No items parsed" | Toon format may differ → try `--dataset` mode |
| GQL timeout | Old post beyond GQL window → falls back to Apify thumbnail |
| "No downloadable media" | Check `post_info.txt` for the item's available URLs |

---

## Output Verification

```bash
# Count files by type
Get-ChildItem -Recurse -File ./output | Group-Object Extension

# Expected distribution:
#   .mp4  → reels
#   .jpg  → carousels, photos, thumbnails
#   .txt  → post_info metadata

# Check for empty files
Get-ChildItem -Recurse -File ./output | Where-Object { $_.Length -eq 0 }

# Count posts per date
Get-ChildItem -Directory ./output | ForEach-Object {
    $count = (Get-ChildItem -Path $_.FullName -Directory).Count
    "$($_.Name): $count posts"
}

# List carousels with their image counts
Get-ChildItem -Recurse -File ./output/*.txt | ForEach-Object {
    $dir = $_.Directory
    $images = Get-ChildItem -Path $dir.FullName -Filter "*.jpg" `
        | Where-Object { $_.Name -match '_\d{2}\.jpg$' }
    if ($images.Count -gt 1) {
        "$($dir.Parent.Name)/$($dir.Name): $($images.Count) images"
    }
}
```

---

## File Locations

- **Skill**: `./SKILL.md` (this file)
- **Download script**: `./instagram_downloader.py`

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-07 | Initial Apify-based release |
| 1.1.0 | 2026-07 | Added instagrapi GQL hybrid for full carousel extraction; `--no-instagrapi` flag; documented fbcdn.net CDN handling |

---

**Instagram Downloader Skill v1.1.0** — Hybrid Apify + instagrapi approach.
