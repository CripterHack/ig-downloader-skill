---
name: instagram-downloader
description: Download Instagram profile media (reels MP4, photos JPG, full carousel multi-image JPG) via sessionid (instagrapi), Apify dataset fallback, or interactive setup wizard. No password sharing required.
version: 2.0.0
author: opencode
type: skill
category: data-extraction
tags:
  - instagram
  - instagrapi
  - sessionid
  - apify
  - download
  - media
  - carousel
  - scraping
---

# Instagram Downloader Skill v2.0

> **Purpose**: Download all media (reels MP4, carousels with ALL images, photos JPG) from an Instagram profile. Three operation modes: sessionid (full access), Apify (no login, limited), setup wizard (interactive browser login).

---

## Operation Modes

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          INSTAGRAM DOWNLOADER v2.0                          │
│                                                                              │
│  ┌─────────────────────┐   ┌─────────────────────┐   ┌──────────────────┐   │
│  │  Mode 1: Sessionid  │   │  Mode 2: Apify      │   │  Mode 3: Setup   │   │
│  │                     │   │  (Legacy)           │   │  (Wizard)        │   │
│  │  instagrapi         │   │  Apify Actor        │   │  Opens browser   │   │
│  │  login_by_sessionid │   │  dataset            │   │  Polls for login │   │
│  │  user_medias()      │   │  GQL enhancement    │   │  Saves config    │   │
│  │  media_info()       │   │  for carousels      │   │                  │   │
│  │                     │   │                     │   │  One-time setup  │   │
│  │  ✅ Full catalog    │   │  ✅ No login        │   │                  │   │
│  │  ✅ All carousels   │   │  ❌ Date cutoff     │   │  Output:         │   │
│  │  ✅ Any date        │   │  ❌ 1st img only    │   │  config.json     │   │
│  │  ✅ No watermark    │   │     (old posts)     │   │  with sessionid  │   │
│  │  ──────────────     │   │  ────────────────   │   │                  │   │
│  │  Requires:          │   │  Requires:           │   │  `--setup` flag │   │
│  │  sessionid cookie   │   │  Apify dataset ID   │   │                  │   │
│  └─────────────────────┘   └─────────────────────┘   └──────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Mode Comparison

| Aspect | Sessionid 🥇 | Apify (legacy) | Setup Wizard |
|--------|-------------|----------------|--------------|
| **Login** | Cookie `sessionid` | None | Interactive browser |
| **All posts** | ✅ Yes | ✅ Yes | N/A (setup only) |
| **Old posts** | ✅ Yes | ❌ GQL < 4 weeks | N/A |
| **Carousels** | ✅ All images | ❌ 1st image only (old) | N/A |
| **Cost** | $0 | ~$0.03/run | $0 |
| **Speed** | Fast (instagrapi) | Fast (direct URLs) | N/A |
| **Complexity** | Cookie extraction | Apify account | 1 click |

---

## Architecture

### Mode 1: Sessionid (Primary)

```
User provides ──→ sessionid cookie
                        │
                        ▼
              instagrapi.login_by_sessionid()
                        │
                        ▼
              cl.user_id_from_username(username)
                        │
                        ▼
              cl.user_medias(user_id, amount=0)
                  (fetches ALL posts)
                        │
              ┌─────────┴──────────┐
              ▼                    ▼
         cl.photo_download()   cl.video_download()
         (photos/carousels)    (reels)
              │                    │
              ▼                    ▼
         <output_dir>/YYYY-MM-DD/<shortcode>/
             ├── <shortcode>.mp4          (reel)
             ├── <shortcode>.jpg          (photo)
             ├── <shortcode>_01.jpg       (carousel img 1/N)
             ├── <shortcode>_02.jpg       (carousel img 2/N)
             ├── ...
             └── post_info.txt            (metadata)
```

### Sessionid Source Priority

The script resolves the sessionid in this order:

1. **`--sessionid` CLI flag** — highest priority, one-shot
2. **`SESSIONID` environment variable** — for CI/automation
3. **Config file** (`~/.ig-downloader/config.json`) — persistent, set by `--setup`
4. **Chrome cookies** (automatic extraction from browser) — if user is logged in

### Mode 2: Apify (Fallback)

Same as v1.x: Apify Actor → dataset → toon file → download (with GQL carousel enhancement).

---

## Prerequisites

### Sessionid Mode

- **Python 3.7+**
- **`instagrapi >= 2.0.0`**: `pip install instagrapi`
- **Instagram `sessionid` cookie** (from browser DevTools → Application → Cookies)
- **Chrome** (optional, for auto-extraction with `--setup`)

### Apify Mode (Legacy)

- **`requests`**: `pip install requests`
- **`instagrapi`** (optional, for carousel enhancement): `pip install instagrapi`
- **Apify account** (free tier)

---

## Getting the Sessionid Cookie

### Method A: Manual (1 minute)

1. Open Chrome, go to `https://www.instagram.com`
2. Log in to Instagram
3. Press **F12** → **Application** → **Cookies** → `www.instagram.com`
4. Find `sessionid` — copy its value
5. Run: `python instagram_downloader.py -u username --sessionid "YOUR_SESSIONID"`

### Method B: Interactive Setup (recommended)

```bash
python instagram_downloader.py --setup
```

This opens Instagram in your browser. Log in, and the script automatically detects the `sessionid` cookie, saves it to `~/.ig-downloader/config.json`, and exits. After that, no `--sessionid` flag needed.

### Method C: Environment Variable

```bash
set SESSIONID=YOUR_SESSIONID
python instagram_downloader.py -u username
```

---

## Workflow

### Sessionid Mode (Fastest, Most Complete)

```bash
# One-time setup
python instagram_downloader.py --setup

# Then just download
python instagram_downloader.py -u username -o ./instagram_downloads
```

### Apify Mode (No Login)

```python
# Via MCP
await mcp_call-actor({ actor: "unseenuser/IG-posts", input: { usernames: ["username"] } })
await mcp_get-dataset-items({ datasetId: "<ID>", limit: 999, clean: true })

# Then download
python instagram_downloader.py --toon-file ./data.txt \
    -u username \
    --date-start YYYY-MM-DD --date-end YYYY-MM-DD \
    -o ./instagram_downloads
```

---

## Script Reference

**Location**: `instagram_downloader.py` (same directory)

### Command-Line Options

#### Mode Selection (choose one or none)

| Option | Description |
|--------|-------------|
| `--sessionid STR` | Instagram sessionid cookie (one-shot, highest priority) |
| `--setup` | Interactive setup: opens browser, polls for login, saves config |
| `--dataset ID` | Apify dataset ID |
| `--api-token KEY` | Apify API token (required with `--dataset`) |
| `--toon-file PATH` | Apify dataset exported as JSON/YAML |

#### Files & Target

| Option | Description |
|--------|-------------|
| `-u / --username HANDLE` | Target Instagram handle (required for sessionid mode) |
| `-o / --output DIR` | Output directory (default: `./instagram_downloads`) |
| `--flat` | Flatten: single folder instead of `YYYY-MM-DD/shortcode/` |

#### Filters (Apify mode only)

| Option | Description |
|--------|-------------|
| `--date-start YYYY-MM-DD` | Earliest post date (inclusive) |
| `--date-end YYYY-MM-DD` | Latest post date (inclusive) |
| `--type {reel,carousel,photo,all}` | Filter by post type (default: all) |
| `--own-only` | Only posts authored by `--username` |
| `--mentions-only` | Only posts from other accounts mentioning `--username` |

#### Misc

| Option | Description |
|--------|-------------|
| `--no-verify` | Skip SSL verification (not recommended) |
| `--version` | Show version and exit |
| `--help` | Show help message |

### Default Output Structure

```
instagram_downloads/
└── YYYY-MM-DD/
    ├── <SHORTCODE>/               # Reel
    │   ├── <SHORTCODE>.mp4
    │   ├── <SHORTCODE>.jpg        # Thumbnail
    │   └── post_info.txt
    ├── <SHORTCODE>/               # Photo
    │   ├── <SHORTCODE>.jpg
    │   └── post_info.txt
    └── <SHORTCODE>/               # Carousel
        ├── <SHORTCODE>.jpg        # First image (cl.photo_download)
        ├── <SHORTCODE>_02.jpg     # Image 2/N (from media_info)
        ├── <SHORTCODE>_03.jpg     # Image 3/N
        ├── ...
        └── post_info.txt
```

---

## Sessionid Under the Hood

### Cookie Extraction

The `--setup` flow:
1. Opens `https://www.instagram.com` in the default browser via `webbrowser.open()`
2. Polls the Chrome cookie SQLite database every 3 seconds
3. Reads cookies using `sqlite3` + DPAPI key decryption (AES-GCM with no-authentication-tag)
4. Once `sessionid` is detected, saves to `~/.ig-downloader/config.json`
5. Closes automatically

### Media Fetching

- `user_id_from_username()` → numeric user ID
- `user_medias(user_id, amount=0)` → ALL media items (amount=0 means unlimited)
- Each `Media` object has: `pk`, `code` (shortcode), `media_type` (1=photo, 2=video, 8=carousel), `taken_at` (datetime)
- Carousels: `media_info(pk)` returns `carousel_media[]` with all resources
- Downloads via `photo_download()` / `video_download()` with proper auth

### Config Storage

```json
{
  "sessionid": "YOUR_SESSIONID_COOKIE",
  "created_at": "2026-07-07T22:00:00"
}
```

Location: `~/.ig-downloader/config.json`

---

## Examples

### Sessionid mode (from config, simplest)

```bash
python instagram_downloader.py -u username -o ./downloads
```

### Sessionid mode (direct flag)

```bash
python instagram_downloader.py \
    -u username \
    --sessionid "1234567890%3Aabcdef" \
    -o ./downloads
```

### Sessionid mode (environment variable)

```bash
set SESSIONID=1234567890%3Aabcdef
python instagram_downloader.py -u username -o ./downloads
```

### Setup wizard (first time only)

```bash
python instagram_downloader.py --setup
```

### Apify mode (toon file, with filters)

```bash
python instagram_downloader.py \
    --toon-file ./data.txt \
    -u username \
    --type reel \
    --date-start YYYY-MM-DD \
    --date-end YYYY-MM-DD \
    -o ./reels_only
```

### Apify mode (API token)

```bash
python instagram_downloader.py \
    --dataset <DATASET_ID> \
    --api-token apify_api_xxx \
    -u username \
    -o ./downloads
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No sessionid found" | Run `--setup` or pass `--sessionid` directly |
| "Login required" in sessionid mode | sessionid expired. Re-run `--setup` to get a fresh one |
| `instagrapi` not found | `pip install instagrapi` |
| Chrome cookie extraction fails | Use `--sessionid` flag with manual cookie from DevTools |
| 403 on fbcdn.net | Use sessionid mode (instagrapi handles auth) |
| Apify returns 403 | CDN URL expired → re-run the Actor |
| GQL timeout | Old post > 4 weeks → falls back to Apify thumbnail |
| No items in sessionid mode | Check username; profile may be private and sessionid may not follow it |
| ModuleNotFoundError: No module named 'win32crypt' | Auto-detected; falls back to manual `--sessionid` flag |
| "No items parsed" in toon mode | Toon format may differ → try `--dataset` API mode |

---

## Known Issues

### 1. Sessionid Expiration
Instagram session cookies expire after some time (days-weeks). When this happens, re-run `--setup` or pass a fresh `--sessionid`.

### 2. Chrome DPAPI Decryption
Cookie extraction uses Windows DPAPI + AES-GCM. Works with Chrome's latest cookie encryption (no-authentication-tag variant). If Chrome updates its format, extraction may break.

### 3. Private Profiles
Sessionid mode can only download profiles that the logged-in user follows. For private profiles you don't follow, Apify mode with `unseenuser/IG-posts` may work (the actor runs its own session).

### 4. Carousel GQL Limit (Apify mode)
GQL enhancement works only for recent posts (< 4 weeks). Older posts get single thumbnail.

### 5. CDN URL Expiry (Apify mode)
Apify URLs expire after hours. Download soon after fetching.

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2026-07 | Sessionid mode with instagrapi full access; interactive setup wizard; Chrome cookie extraction; config management; 3-mode architecture |
| 1.1.0 | 2026-07 | instagrapi GQL hybrid for carousel enhancement; `--no-instagrapi` flag |
| 1.0.0 | 2026-07 | Initial Apify-based release |

---

**Instagram Downloader Skill v2.0.0** — Three modes, zero compromises.
