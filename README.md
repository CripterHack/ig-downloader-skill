# Instagram Downloader Skill v2.1

> Download Instagram media — reels, carousels (all images), photos — via **login (instagrapi, recommended)**, **sessionid (instagrapi)** or **Apify dataset** fallback. Full login with 2FA support, challenge handling, and saved sessions.

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

**v2.1 solution**: Three authentication paths:
1. **Login** (recommended): Full username/password via `instagrapi` with 2FA and challenge support. Saved sessions auto-reload.
2. **Sessionid**: Cookie-only access (no password, no 2FA). Full access to ALL posts, ALL carousel images, ANY date.
3. **Apify** (fallback): Dataset-based when no login/sessionid is available.

As a **fallback**, the Apify dataset mode is preserved for when instagrapi authentication is unavailable.

---

## Quick Start

### Option A: Login (recommended)

```bash
pip install instagrapi
python instagram_downloader.py --login -u username -o ./downloads
```

Password is prompted securely. Subsequent runs auto-reload the saved session.

### Option B: Setup wizard (sessionid)

```bash
pip install instagrapi
python instagram_downloader.py --setup
```

A browser opens. Log into Instagram. Then:

```bash
python instagram_downloader.py -u username -o ./downloads
```

No `--sessionid` flag needed after setup.

---

## Operation Modes

| Mode | How | Best For |
|------|-----|----------|
| **Login** 🥇 | `instagrapi` full login (password + 2FA) | Full access. All posts, all carousels, private profiles. Saved sessions persist. |
| **Sessionid** 🥈 | `instagrapi` login via browser cookie | Full access. All posts, all carousels, no date limit. No password sharing. |
| **Apify (legacy)** | `unseenuser/IG-posts` dataset | No login at all. Carousels limited to 1 image for posts >4 weeks. |
| **Setup** | Interactive browser → captures cookie → saves config | One-time. Enables sessionid mode. |

### Mode Comparison

| Feature | Login | Sessionid | Apify |
|---------|-------|-----------|-------|
| Login | Username/password (+2FA) | Cookie `sessionid` | None |
| All posts (any date) | ✅ | ✅ | ✅ (catalog) |
| Carousels: ALL images | ✅ (via `media_info()`) | ✅ (via `media_info()`) | ❌ 1st image only (old posts) |
| Private profiles | ✅ (if you follow) | ✅ (if you follow) | ❌ |
| Session persistence | ✅ Saved `settings.json` | ✅ `config.json` | N/A |
| Download method | `instagrapi` native | `instagrapi` native | `requests` + `instagrapi` GQL |
| Cost | $0 | $0 | ~$0.03/run |
| Setup time | 10s (password prompt) | 1 min (cookie) | 5 min (Apify account) |

---

## Authentication

### A. Login (recommended)

```bash
python instagram_downloader.py --login -u username -o ./downloads
```

- Password prompted securely via `getpass` (invisible)
- With 2FA: add `--totp CODE`
- Challenge detection: SMS/email codes prompted interactively
- Session saved to `~/.ig-downloader/settings.json` — subsequent runs auto-reload

### B. Interactive Setup (sessionid)

```bash
python instagram_downloader.py --setup
```

1. Opens `https://www.instagram.com` in your browser
2. You log in normally (or are already logged in)
3. Script detects the `sessionid` cookie automatically
4. Saves to `~/.ig-downloader/config.json`
5. Done. No `--sessionid` flag needed ever again.

### C. Manual sessionid (for power users)

1. Chrome → **F12** → **Application** → **Cookies** → `www.instagram.com`
2. Copy the `sessionid` value
3. Run: `python instagram_downloader.py -u username --sessionid "YOUR_COOKIE"`

### D. Environment variable

```powershell
$env:SESSIONID = "YOUR_COOKIE"
python instagram_downloader.py -u username -o ./downloads
```

---

## Installation

```bash
# Clone
git clone https://github.com/USERNAME/ig-downloader-skill.git
cd ig-downloader-skill

# Dependencies
pip install instagrapi

# Run
python instagram_downloader.py --help
```

Or install as a package:

```bash
pip install git+https://github.com/USERNAME/ig-downloader-skill.git
ig-downloader --help
```

---

## Usage Guide

### Mode Selection

The script auto-detects which mode to use (priority order):

```
1. Saved settings (~/.ig-downloader/settings.json) → Login mode (auto)
2. --sessionid flag / env / config / Chrome → Sessionid mode
3. --login flag   → Login mode (password prompted)
4. --setup flag   → Interactive setup wizard
5. --dataset/--toon-file → Apify mode (legacy)
```

### Login Flags

| Flag | Description |
|------|-------------|
| `--login` | Full username/password login (recommended). Password prompted via `getpass`. |
| `--password STR` | Inline password (omit for secure prompt). |
| `--totp CODE` | 2FA verification code. |
| `-u / --username HANDLE` | Target Instagram profile (required). |
| `-o / --output DIR` | Output directory (default: `./instagram_downloads`). |

### Sessionid Flags

| Flag | Description |
|------|-------------|
| `--sessionid STR` | sessionid cookie (direct, skips config/env). |
| `--setup` | Interactive setup wizard (opens browser, captures cookie). |

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

### Login mode (recommended, full access)

```bash
# Password prompted securely (no --password flag needed)
python instagram_downloader.py --login -u username -o ./downloads

# With 2FA verification code
python instagram_downloader.py --login -u username --totp 123456 -o ./downloads

# After first login: saved session auto-reloads
python instagram_downloader.py -u username -o ./downloads
```

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
| Login fails | Check username/password. For 2FA, add `--totp CODE`. For challenge, check terminal for code prompt. |
| Login succeeds but no downloads | Saved session may be expired — re-run with `--login` to refresh. |
| "No sessionid found" | Run `--setup` or pass `--sessionid` flag. |
| "Login required" in sessionid mode | sessionid expired. Re-run `--setup`. |
| Chrome cookie extraction fails | Use `--sessionid` flag with cookie from DevTools manually. |
| 403 in Apify mode | CDN URL expired → re-run the Actor. |
| GQL timeout | Post >4 weeks → falls back to Apify thumbnail. |
| "No items" in sessionid mode | Check username; profile may be private and session may not follow it. |
| ModuleNotFoundError: win32crypt | Auto-detected. Falls back to manual `--sessionid` flag. |
| "No items parsed" in toon mode | Try `--dataset` API mode instead. |
| `python` not found | Use `py` or `python3`. |

---

## FAQ

**Q: Does this share my Instagram password?**
A: Login mode prompts for password via `getpass` (invisible, not stored). Sessionid mode uses a cookie — no password at all.

**Q: How does login mode handle 2FA?**
A: Pass `--totp CODE` for time-based codes. Challenge SMS/email codes are handled interactively via terminal prompt.

**Q: Does login mode save my password?**
A: No. The password is used once to log in, then `instagrapi` saves a session file (`settings.json`) — password is not stored.

**Q: How long do sessions last?**
A: Login sessions persist until Instagram invalidates them (weeks-months). Sessionid cookies expire in days-weeks.

**Q: Can I download private profiles?**
A: Login/sessionid modes can download profiles your account follows. Apify mode only works for public profiles.

**Q: Can I download stories / highlights?**
A: No. This tool downloads profile posts and reels only.

**Q: Do I still need Apify?**
A: No. Login and sessionid modes replace Apify entirely. Apify mode is kept as a fallback.

**Q: Does it work on Linux / macOS?**
A: Yes. Login mode works everywhere (password prompt). `--setup` Chrome extraction is Windows-only (DPAPI). On Linux/macOS, use login or `--sessionid` flag.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Open issues, fork, submit PRs.

---

## License

Copyright (C) 2026 Edgar Zorrilla

GNU General Public License v2.0. See [LICENSE](LICENSE).
