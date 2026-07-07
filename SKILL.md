---
name: instagram-downloader
description: Download Instagram profile media (reels MP4, photos JPG, full carousel multi-image JPG) via sessionid (instagrapi), Apify dataset fallback, or interactive setup wizard. No password sharing required.
version: 2.1.0
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

# Instagram Downloader Skill v2.1

> **Purpose**: Download all media (reels MP4, carousels with ALL images, photos JPG) from an Instagram profile. Four operation modes: login (full username/password + 2FA), sessionid (cookie), Apify (no login, limited), setup wizard (interactive browser login).

---

## Operation Modes

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                          INSTAGRAM DOWNLOADER v2.1                                   │
│                                                                                      │
│  ┌─────────────────────┐   ┌───────────────────┐   ┌──────────────────┐   ┌───────┐ │
│  │  Mode 1: Login      │   │  Mode 2: Sessionid│   │  Mode 3: Apify   │   │Mode 4 │ │
│  │  (Recommended)      │   │                   │   │  (Legacy)        │   │Setup  │ │
│  │                     │   │                   │   │                  │   │(Wiz.) │ │
│  │  instagrapi         │   │  instagrapi        │   │  Apify Actor     │   │Opens  │ │
│  │  Client.login()     │   │  login_by_sid()    │   │  dataset         │   │browser│ │
│  │  Password + 2FA     │   │  user_medias()     │   │  GQL enh.        │   │Polls  │ │
│  │  Saved sessions     │   │  media_info()      │   │  for carousels   │   │Saves  │ │
│  │                     │   │                    │   │                  │   │config │ │
│  │  ✅ Full catalog    │   │  ✅ Full catalog   │   │  ✅ No login     │   │       │ │
│  │  ✅ All carousels   │   │  ✅ All carousels  │   │  ❌ GQL cutoff   │   │       │ │
│  │  ✅ Any date        │   │  ✅ Any date       │   │  ❌ 1st img old  │   │       │ │
│  │  ✅ Private profiles│   │  ✅ No watermark   │   │                  │   │       │ │
│  │  ──────────────     │   │  ────────────────   │   │  ─────────────   │   │       │ │
│  │  Requires:          │   │  Requires:           │   │  Requires:       │   │One-   │ │
│  │  --login + password │   │  sessionid cookie   │   │  Apify dataset   │   │time   │ │
│  └─────────────────────┘   └─────────────────────┘   └──────────────────┘   └───────┘ │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### Mode Comparison

| Aspect | Login 🥇 | Sessionid 🥈 | Apify (legacy) | Setup Wizard |
|--------|---------|-------------|----------------|--------------|
| **Login** | Username/password (+2FA) | Cookie `sessionid` | None | Interactive browser |
| **All posts** | ✅ Yes | ✅ Yes | ✅ Yes | N/A (setup only) |
| **Old posts** | ✅ Yes | ✅ Yes | ❌ GQL < 4 weeks | N/A |
| **Carousels** | ✅ All images | ✅ All images | ❌ 1st image only (old) | N/A |
| **Private profiles** | ✅ (if you follow) | ✅ (if you follow) | ❌ | N/A |
| **Session persistence** | ✅ Saved settings.json | ✅ config.json | N/A | ✅ config.json |
| **Cost** | $0 | $0 | ~$0.03/run | $0 |
| **Speed** | Fast (instagrapi) | Fast (instagrapi) | Fast (direct URLs) | N/A |
| **Complexity** | Password (1 prompt) | Cookie extraction | Apify account | 1 click |

---

## Architecture

### Credential Resolution Priority

The script auto-detects the best available authentication method:

1. **Saved settings** (`~/.ig-downloader/settings.json`) — persistent session from `--login`, auto-reloaded
2. **`--sessionid` CLI flag** — one-shot session cookie
3. **`SESSIONID` environment variable** — for CI/automation
4. **Config file** (`~/.ig-downloader/config.json`) — persistent, set by `--setup`
5. **Chrome cookies** — automatic extraction from browser SQLite
6. **`--login` fallback** — prompts for password if no other credential found

When no instagrapi auth is available, falls through to **Apify mode**.

### Mode 1: Login (Recommended)

```
python instagram_downloader.py --login -u username
                              ▼
               ┌─ Password (secure prompt) ──┐
               │  getpass.getpass()           │
               └──────────────────────────────┘
               │
               ▼
    instagrapi.Client.login(password, verification_code)
         ┌─────┴─────┐
         ▼            ▼
    2FA prompt   Challenge SMS/email
   (--totp)     (code_handler)
         │            │
         └─────┬──────┘
               ▼
      cl.dump_settings(session_path)
      Save to ~/.ig-downloader/settings.json
               │
               ▼
      cl.user_id_from_username(username)
               │
               ▼
      cl.user_medias(user_id, amount=0)
          (fetches ALL posts)
               │
      ┌────────┴──────────┐
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

### Mode 2: Sessionid

```
User provides ──→ sessionid cookie
                        │
                        ▼
              instagrapi.login_by_sessionid()
         (same pipeline as Mode 1 from user_id onward)
```

### Mode 3: Apify (Fallback)

Same as v1.x: Apify Actor → dataset → toon file → download (with GQL carousel enhancement for recent posts).

---

## Prerequisites

- **Python 3.7+**
- **`instagrapi >= 2.0.0`**: `pip install instagrapi`
- **`requests`**: `pip install requests`
- **Chrome** (optional, for interactive setup and cookie extraction)
- **Apify account** (free tier, only needed for Apify legacy mode)

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

### Login Mode (Recommended, Full Access)

```bash
# Download all media (password prompted securely)
python instagram_downloader.py --login -u username -o ./downloads

# With 2FA
python instagram_downloader.py --login -u username --totp 123456 -o ./downloads

# Subsequent runs: saved session auto-reloads, just:
python instagram_downloader.py -u username -o ./downloads
```

### Sessionid Mode (Cookie)

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

#### Mode Selection (auto-detected in order: login → sessionid → Apify → setup)

| Option | Description |
|--------|-------------|
| `--login` | Full username/password login (recommended). Prompts for password securely. |
| `--password STR` | Password for `--login` mode (omit to prompt securely via `getpass`). |
| `--totp CODE` | 2FA verification code for `--login` mode. |
| `--sessionid STR` | Instagram sessionid cookie (one-shot, overrides config/env). |
| `--setup` | Interactive setup: opens browser, polls for login, saves sessionid to config. |
| `--dataset ID` | Apify dataset ID (legacy, no login). |
| `--api-token KEY` | Apify API token (required with `--dataset`). |
| `--toon-file PATH` | Apify dataset exported as JSON/YAML. |

#### Files & Target

| Option | Description |
|--------|-------------|
| `-u / --username HANDLE` | Target Instagram handle (required for login/sessionid/setup). |
| `-o / --output DIR` | Output directory (default: `./instagram_downloads`). |
| `--flat` | Flatten: single folder instead of `YYYY-MM-DD/shortcode/`. |

#### Filters (Apify mode only; login/sessionid modes download ALL posts)

| Option | Description |
|--------|-------------|
| `--date-start YYYY-MM-DD` | Earliest post date (inclusive). |
| `--date-end YYYY-MM-DD` | Latest post date (inclusive). |
| `--type {reel,carousel,photo,all}` | Filter by post type (default: all). |
| `--own-only` | Only posts authored by `--username`. |
| `--mentions-only` | Only posts from other accounts mentioning `--username`. |

#### Misc

| Option | Description |
|--------|-------------|
| `--no-verify` | Skip SSL verification (not recommended). |
| `--version` | Show version and exit. |
| `--help` | Show help message. |

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

### Login mode (recommended, full access)

```bash
# Password prompted securely (no --password flag needed)
python instagram_downloader.py --login -u username -o ./downloads

# With 2FA verification code
python instagram_downloader.py --login -u username --totp 123456 -o ./downloads

# After first login: saved session auto-reloads
python instagram_downloader.py -u username -o ./downloads
```

### Sessionid mode (from config, simplest)

```bash
# After running --setup once
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
| "No instagrapi" | `pip install instagrapi` |
| Login fails | Check username/password. For 2FA, provide `--totp CODE`. For challenge, check terminal for SMS/email prompt. |
| "Login required" in sessionid mode | sessionid expired. Re-run `--setup` to get a fresh one. |
| "No sessionid found" | Run `--setup` or pass `--sessionid` directly. |
| Chrome cookie extraction fails | Use `--sessionid` flag with manual cookie from DevTools. |
| 403 on fbcdn.net | Use login/sessionid mode (instagrapi handles auth). |
| Apify returns 403 | CDN URL expired → re-run the Actor. |
| GQL timeout | Old post > 4 weeks → falls back to Apify thumbnail. |
| No items in sessionid mode | Check username; profile may be private and sessionid may not follow it. |
| ModuleNotFoundError: No module named 'win32crypt' | Auto-detected; falls back to manual `--sessionid` flag. |
| "No items parsed" in toon mode | Toon format may differ → try `--dataset` API mode. |

---

## Known Issues

### 1. Sessionid Expiration
Instagram session cookies expire after some time (days-weeks). When this happens, re-run `--setup` or pass a fresh `--sessionid`. Login mode avoids this via saved sessions + auto-reload.

### 2. Login Challenge Detection
Instagram may trigger a challenge (SMS/email code) on first login from a new IP. The script detects this and prompts you interactively. After the first successful login, the saved session prevents future challenges.

### 3. Chrome DPAPI Decryption
Cookie extraction uses Windows DPAPI + AES-GCM. Works with Chrome's latest cookie encryption (no-authentication-tag variant). If Chrome updates its format, extraction may break.

### 4. Private Profiles
Login/sessionid modes can only download profiles that the logged-in user follows. For private profiles you don't follow, Apify mode with `unseenuser/IG-posts` may work (the actor runs its own session).

### 5. Carousel GQL Limit (Apify mode)
GQL enhancement works only for recent posts (< 4 weeks). Older posts get single thumbnail. Login/sessionid modes avoid this entirely.

### 6. CDN URL Expiry (Apify mode)
Apify URLs expire after hours. Download soon after fetching. Login/sessionid modes avoid this entirely.

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 2.1.0 | 2026-07 | Login mode: `--login` with password prompt, 2FA (`--totp`), challenge handler, saved session persistence via `dump_settings()` |
| 2.0.0 | 2026-07 | Sessionid mode with instagrapi full access; interactive setup wizard; Chrome cookie extraction; config management; 3-mode architecture |
| 1.1.0 | 2026-07 | instagrapi GQL hybrid for carousel enhancement; `--no-instagrapi` flag |
| 1.0.0 | 2026-07 | Initial Apify-based release |

---

**Instagram Downloader Skill v2.1.0** — Four modes, zero compromises, full login.
