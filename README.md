# Instagram Downloader Skill v2.2

> Download Instagram media — reels, carousels (all images), photos — via **sessionid (instagrapi, recommended)**, **Playwright setup wizard**, or **Apify dataset** fallback. No password sharing required.

> **⚠ 2026-07-07: `--login` mode is BROKEN.** Meta deprecated the instagrapi login endpoint server-side. Use `--setup` (Playwright) or a manual `--sessionid` cookie instead.

[![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](LICENSE)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![instagrapi](https://img.shields.io/badge/instagrapi-2.18%2B-purple)](https://github.com/subzeroid/instagrapi)

---

## Table of Contents

- [Why This Tool Exists](#why-this-tool-exists)
- [Quick Start](#quick-start)
- [Operation Modes](#operation-modes)
- [Getting the Sessionid Cookie](#getting-the-sessionid-cookie)
- [Installation](#installation)
- [Usage Guide](#usage-guide)
- [Examples](#examples)
- [Output Structure](#output-structure)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Contributing](#contributing)
- [License](#license)

---

## Why This Tool Exists

Traditional Instagram downloaders (`instaloader`, `gallery-dl`) fail with 403/NotFound errors because Instagram aggressively blocks scraping. The web page no longer embeds JSON data (`__INITIAL_STATE__` removed). Solutions exist but each has tradeoffs:

| Approach | Issue |
|----------|-------|
| `instaloader` | 403 on all GraphQL queries |
| `gallery-dl` | 403 on direct URLs |
| Apify Actors | ❌ Carousels: only 1st image. Old posts: GQL fails. Cost: ~$0.03/run. |
| `instagrapi` GQL (no login) | ✅ Free, but only recent posts (<4 weeks) |

**v2.2 solution**: Two working authentication paths + one fallback:
1. **Sessionid** (recommended) 🥇: Cookie-only access via `instagrapi` (no password, no 2FA). Full access to ALL posts, ALL carousel images, ANY date.
2. **Apify** (fallback): Dataset-based when no sessionid is available.
3. **`--setup`**: Playwright browser auto-extracts sessionid and saves to config.

> **`--login` mode removed**: Meta deprecated the underlying endpoint. Login via password no longer works.

---

## How It Works

```mermaid
flowchart LR
    subgraph Auth[Authentication Layer]
        direction TB
        C1[config.json] -->|auto-loads| SID[sessionid]
        CLI[--sessionid flag] --> SID
        ENV[SESSIONID env var] --> SID
        SETUP[--setup wizard] -->|Playwright| SID
        CHROME[Chrome cookies] -->|fallback| SID
    end

    subgraph Download[Download Engine]
        direction TB
        SID --> instagrapi{instagrapi}
        instagrapi -->|Sessionid| FULL[user_medias → ALL posts]
        FULL --> CARR{media_type}
        CARR -->|Photo| PHOTO[photo_download → .jpg]
        CARR -->|Reel| REEL[video_download → .mp4]
        CARR -->|Carousel| CAR[media_info → _01.jpg ... _0N.jpg]
    end

    subgraph Fallback[Apify Fallback]
        direction TB
        DATASET[Apify Dataset] --> TOON[toon-file / API]
        TOON --> GQL{GQL ≤4w?}
        GQL -->|Yes| GOK[All images]
        GQL -->|No| GFALL[Single thumbnail]
    end

    Download --> OUT[📁 YYYY-MM-DD/shortcode/]
    Fallback --> OUT
```

---

## Quick Start

### 1. Setup (one-time)

```bash
pip install instagrapi playwright
playwright install chromium
python instagram_downloader.py --setup
```

A browser opens. Log into Instagram. The sessionid is saved automatically.

### 2. Download everything

```bash
python instagram_downloader.py -u username -o ./my_downloads
```

No `--sessionid` flag needed after setup.

---

## Operation Modes

| Mode | How | Best For |
|------|-----|----------|
| **Sessionid** 🥇 | `instagrapi` login via browser cookie | Full access. All posts, all carousels, no date limit. No password sharing. |
| **Apify (legacy)** | `unseenuser/IG-posts` dataset | No login at all. Carousels limited to 1 image for posts >4 weeks. |
| **Setup** | Playwright browser → captures cookie → saves config | One-time. Enables sessionid mode. |

### Mode Comparison

| Feature | Sessionid | Apify |
|---------|-----------|-------|
| Authentication | Cookie `sessionid` | None |
| All posts (any date) | ✅ | ✅ (catalog) |
| Carousels: ALL images | ✅ (via `media_info()`) | ❌ 1st image only (old posts) |
| Carousels: recent posts | ✅ | ✅ (GQL enhancement) |
| Private profiles | ✅ (if you follow) | ❌ |
| Session persistence | ✅ `config.json` | N/A |
| Download method | `instagrapi` native | `requests` + `instagrapi` GQL |
| Cost | $0 | ~$0.03/run |
| Setup time | 1 min (first time via --setup) | 5 min (Apify account) |

---

## Authentication

### A. Interactive Setup (recommended)

```bash
pip install playwright && playwright install chromium
python instagram_downloader.py --setup
```

```mermaid
sequenceDiagram
    actor User
    participant Script as instagram_downloader.py
    participant PW as Playwright Chromium
    participant IG as instagram.com
    participant FS as ~/.ig-downloader/config.json

    Script->>PW: Launch headful browser
    PW->>IG: Navigate to instagram.com
    User->>IG: Log in (manual)
    Note over IG: User enters credentials,<br/>2FA, or challenge codes
    loop Every 3 seconds
        Script->>PW: Poll context.cookies()
        PW-->>Script: [cookies...]
    end
    Script->>FS: Save sessionid to config.json
    Script->>PW: Close browser
    Note over User,FS: ✅ Done — subsequent runs<br/>auto-load sessionid from config
```

1. Launches a clean Chromium browser (no Chrome profile needed)
2. You log into Instagram normally
3. Script detects the `sessionid` cookie automatically via Playwright's `context.cookies()`
4. Saves to `~/.ig-downloader/config.json`
5. Done. No `--sessionid` flag needed ever again.

**Fallback chain**: Playwright → Chrome extraction → manual paste prompt.

### B. Manual sessionid (for power users / no Playwright)

1. Chrome → **F12** → **Application** → **Cookies** → `www.instagram.com`
2. Copy the `sessionid` value
3. Run: `python instagram_downloader.py -u username --sessionid "YOUR_COOKIE"`

### C. Environment variable

```powershell
$env:SESSIONID = "YOUR_COOKIE"
python instagram_downloader.py -u username -o ./downloads
```

---

## Installation

```bash
# Clone
git clone https://github.com/cripterhack/ig-downloader-skill.git
cd ig-downloader-skill

# Dependencies
pip install instagrapi

# Run
python instagram_downloader.py --help
```

Or install as a package:

```bash
pip install git+https://github.com/cripterhack/ig-downloader-skill.git
ig-downloader --help
```

---

## Usage Guide

### Mode Selection

The script auto-detects which mode to use (priority order):

```
1. --sessionid flag / env var / config file / Chrome → Sessionid mode
2. --setup flag   → Interactive setup wizard (Playwright)
3. --dataset/--toon-file → Apify mode (legacy)
```

### Sessionid Flags

| Flag | Description |
|------|-------------|
| `-u / --username HANDLE` | Target Instagram profile (required). |
| `--sessionid STR` | sessionid cookie (direct, skips config/env). |
| `--setup` | Interactive setup wizard (Playwright → Chrome → manual paste). |
| `-o / --output DIR` | Output directory (default: `./instagram_downloads`). |

### Apify Flags (Legacy)

| Flag | Description |
|------|-------------|
| `--dataset ID` | Apify dataset ID. |
| `--api-token KEY` | Apify API token. |
| `--toon-file PATH` | Apify dataset as JSON/YAML file. |
| `--date-start YYYY-MM-DD` | Earliest post date. |
| `--date-end YYYY-MM-DD` | Latest post date. |
| `--type {reel,carousel,photo}` | Filter by post type. |
| `--own-only` | Only posts by `--username`. |
| `--mentions-only` | Only posts from other accounts. |
| `--no-instagrapi` | Disable GQL carousel enhancement. |

---

## Examples

### Sessionid mode (from config file)

```bash
# After running --setup once
python instagram_downloader.py -u username -o ./downloads
```

### Sessionid mode (direct cookie)

```bash
python instagram_downloader.py \
    -u username \
    --sessionid "1234567890%3Aabcdef" \
    -o ./downloads
```

### Setup wizard

```bash
python instagram_downloader.py --setup
```

### Apify mode (toon file with filters)

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

### Flat output (no date folders)

```bash
python instagram_downloader.py \
    -u username \
    --flat \
    -o ./flat_downloads
```

---

## Output Structure

### Sessionid mode

```
<output-dir>/
└── YYYY-MM-DD/
    ├── <SHORTCODE>/               # Reel
    │   ├── <SHORTCODE>.mp4        # Video
    │   ├── <SHORTCODE>.jpg        # Thumbnail
    │   └── post_info.txt
    ├── <SHORTCODE>/               # Photo
    │   ├── <SHORTCODE>.jpg        # Full resolution
    │   └── post_info.txt
    └── <SHORTCODE>/               # Carousel (all images)
        ├── <SHORTCODE>.jpg        # First image
        ├── <SHORTCODE>_02.jpg     # Image 2/N
        ├── <SHORTCODE>_03.jpg     # Image 3/N
        ├── ...
        └── post_info.txt
```

### Apify mode

Same structure, but carousels >4 weeks get `_01.jpg` only (single thumbnail).

### post_info.txt

```
shortcode: <SHORTCODE>
type: carousel
date: 2026-06-18T22:58:02.000Z
author: username
relation: own_post
url: https://www.instagram.com/p/<SHORTCODE>/
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `instagrapi` not found | `pip install instagrapi` |
| `playwright` not found | `pip install playwright && playwright install chromium` |
| "No sessionid found" | Run `--setup` or pass `--sessionid` flag. |
| "Login required" | sessionid expired. Re-run `--setup`. |
| Playwright browser doesn't open | Run `playwright install chromium` to download browser. |
| Chrome cookie extraction fails | Use `--sessionid` flag with cookie from DevTools manually. |
| 403 in Apify mode | CDN URL expired → re-run the Actor. |
| GQL timeout | Post >4 weeks → falls back to Apify thumbnail. |
| "No items" in sessionid mode | Check username; profile may be private and session may not follow it. |
| "No items parsed" in toon mode | Try `--dataset` API mode instead. |
| `python` not found | Use `py` or `python3`. |

---

## FAQ

**Q: Does this share my Instagram password?**
A: No. The script uses a `sessionid` cookie — no password is ever sent or stored.

**Q: How does --setup work?**
A: It launches a clean Chromium browser via Playwright. You log into Instagram normally. The script extracts the `sessionid` cookie via Playwright's `context.cookies()` API. No passwords are transmitted to the script.

**Q: How long does the sessionid last?**
A: Days to weeks. When it expires, re-run `--setup` (takes 30 seconds).

**Q: Can I download private profiles?**
A: Sessionid mode can download profiles your account follows. Apify mode only works for public profiles.

**Q: Can I download stories / highlights?**
A: No. This tool downloads profile posts and reels only.

**Q: Do I still need Apify?**
A: No. Sessionid mode replaces Apify entirely for most use cases. Apify mode is kept as a fallback.

**Q: Does it work on Linux / macOS?**
A: Yes. `--setup` uses Playwright (cross-platform). Linux/macOS: install `playwright` and you're set.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Open issues, fork, submit PRs.

---

## License

Copyright (C) 2026 Edgar Zorrilla

GNU General Public License v2.0. See [LICENSE](LICENSE).
